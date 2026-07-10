"""STEP 6 - FastAPI serving + Google OAuth + rep scoping.

Routes (all data routes derive the rep from the SESSION, never from the URL):
  GET  /                      dashboard shell (top bar + iframe of the rep's page)
  GET  /page                  the rep's rendered artifact (scoped to their owner_id)
  POST /run                   regenerate this rep's slate now, then redirect to /
  GET  /login                 sign-in page (Google button and/or magic-link note)
  GET  /auth/google/login     start Google OAuth
  GET  /auth/google/callback  finish Google OAuth -> map email -> rep
  GET  /auth/magic?token=...   magic-link login
  GET  /logout
  GET  /healthz
"""
from __future__ import annotations

import html as _html
from urllib.parse import quote as _urlquote

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .registry import Rep, get_rep, active_reps, load_reps
from . import auth, storage, overrides, schedule_state
from .pipeline import jobs
from .scheduler import start_scheduler

settings = get_settings()
app = FastAPI(title="Delightree Prospecting Portal")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.session_https_only,   # True in prod (HTTPS), False for local http
)


@app.on_event("startup")
def _bootstrap_credentials() -> None:
    """Password bootstrap on boot.
    - Reps: seeded with BOOTSTRAP_PASSWORD only on first boot (empty credentials), so
      per-user passwords set later aren't clobbered.
    - Admins: (re)set to BOOTSTRAP_PASSWORD_ADMIN on EVERY boot, so admin-board access
      is controlled by that one secret and applies to any admin you add later.
    """
    reps = load_reps()
    # 1) first-boot rep seeding
    if settings.bootstrap_password and not auth._load_creds():
        for email in reps:
            auth.set_password(email, settings.bootstrap_password)
    # 2) admins always use the dedicated admin password (if configured)
    if settings.bootstrap_password_admin:
        for email, r in reps.items():
            if r.is_admin:
                auth.set_password(email, settings.bootstrap_password_admin)


@app.on_event("startup")
def _start_scheduler() -> None:
    """Register the weekday 7AM job; the admin toggle decides if it runs."""
    start_scheduler()

# --- optional Google OAuth ---
_oauth = None
if auth.google_configured():
    from authlib.integrations.starlette_client import OAuth
    _oauth = OAuth()
    _oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ---------------------------- dependencies ----------------------------

def current_rep(request: Request) -> Rep:
    rep = auth.rep_from_session(request.session)
    if rep is None:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return rep


# ---------------------------- auth routes ----------------------------

@app.get("/login", response_class=HTMLResponse)
def login(request: Request, error: str = ""):
    """Single team link: pick your HubSpot user, enter your per-user password."""
    if auth.rep_from_session(request.session):
        return RedirectResponse("/", status_code=302)
    options = "".join(
        f'<option value="{_html.escape(r.email)}">{_html.escape(r.rep_name)} ({_html.escape(r.email)})</option>'
        for r in sorted(active_reps(), key=lambda r: r.rep_name.lower())
    )
    google_btn = ('<a class="btn ghost" href="/auth/google/login">or sign in with Google</a>'
                  if _oauth else "")
    err = f'<p style="color:#b91c1c;font-size:13px;margin:0 0 6px">{_html.escape(error)}</p>' if error else ""
    field = ("padding:11px;border:1px solid #e6e8ec;border-radius:10px;font-size:14px;"
             "width:100%;margin:6px 0")
    return _shell_doc("Sign in", f"""
      <div class="box" style="max-width:480px">
        <h1>Delightree Prospecting</h1>
        <p class="muted">Select your HubSpot user and enter your portal password.</p>
        {err}
        <form method="post" action="/login">
          <select name="email" style="{field}" autofocus>{options}</select>
          <input name="password" type="password" placeholder="Portal password" style="{field}">
          <button class="btn" type="submit" style="width:100%;margin-top:8px">Sign in</button>
        </form>
        {google_btn}
        <p class="muted" style="margin-top:14px;font-size:12px">You will only see your own HubSpot book. Not listed, or need a password? Ask RevOps.</p>
      </div>""")


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    rep = get_rep(email)
    if rep is None or not rep.active:
        return RedirectResponse("/login?error=Unknown+user", status_code=303)
    if not auth.check_password(email, password):
        return RedirectResponse("/login?error=Incorrect+password", status_code=303)
    request.session[auth.SESSION_EMAIL_KEY] = email
    return RedirectResponse("/", status_code=303)


@app.get("/auth/google/login")
async def google_login(request: Request):
    if not _oauth:
        raise HTTPException(404, "Google OAuth not configured")
    return await _oauth.google.authorize_redirect(request, settings.oauth_redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    if not _oauth:
        raise HTTPException(404, "Google OAuth not configured")
    token = await _oauth.google.authorize_access_token(request)
    info = token.get("userinfo") or {}
    email = (info.get("email") or "").lower()
    hd = info.get("hd") or email.split("@")[-1]
    if settings.google_hosted_domain and hd != settings.google_hosted_domain:
        return _forbidden(f"This portal is restricted to {settings.google_hosted_domain} accounts.")
    if not get_rep(email):
        return _forbidden(f"{email} is not a registered rep. Ask RevOps to add you to reps.json.")
    request.session[auth.SESSION_EMAIL_KEY] = email
    return RedirectResponse("/", status_code=302)


@app.get("/auth/magic")
def magic(request: Request, token: str):
    email = auth.verify_magic_token(token)
    if not email or not get_rep(email):
        return _forbidden("This magic link is invalid or expired.")
    request.session[auth.SESSION_EMAIL_KEY] = email
    return RedirectResponse("/", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# ---------------------------- data routes ----------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(rep: Rep = Depends(current_rep)):
    running = jobs.is_running(rep.hubspot_owner_id)
    st = jobs.status(rep.hubspot_owner_id)
    has_page = storage.load_page(rep.hubspot_owner_id) is not None

    if running:
        body = (
            '<div class="box"><h1>Building your slate…</h1>'
            '<p class="muted">Researching your accounts and writing every A/B email. '
            'This takes ~2-3 minutes. This page refreshes itself — no need to wait here.</p>'
            '<div class="spinner"></div></div>'
        )
    elif has_page:
        body = '<iframe src="/page" title="Daily slate"></iframe>'
    else:
        err = st.get("error")
        note = (f'<p style="color:#b91c1c;font-size:13px">Last run errored: {_html.escape(err)}</p>'
                if err else '<p class="muted">Generate your first daily re-engagement slate.</p>')
        body = f'<div class="box"><h1>No slate yet</h1>{note}</div>'

    run_btn = ('<span class="btn" style="opacity:.6">Building…</span>' if running else
               '<form method="post" action="/run"><button class="btn" type="submit">'
               f'{"Re-run my slate" if has_page else "Run my slate now"}</button></form>')
    bar = f"""
      <div class="bar">
        <div><b>Daily Re-Engagement</b> &middot; {_html.escape(rep.rep_name)}
             <span class="muted">(owner {_html.escape(rep.hubspot_owner_id)})</span></div>
        <div class="actions">
          <a class="btn ghost" href="/add">+ Add company</a>
          <a class="btn ghost" href="/next-week">Next week</a>
          {run_btn}
          {'<a class="btn ghost" href="/admin">Admin</a>' if rep.is_admin else ''}
          <a class="btn ghost" href="/logout">Log out</a>
        </div>
      </div>"""
    # while a job runs, auto-refresh so the page flips to the slate when ready
    return _shell_doc(f"{rep.rep_name} - Daily Slate", bar + body, full=True,
                      refresh=12 if running else 0)


@app.get("/page", response_class=HTMLResponse)
def page(rep: Rep = Depends(current_rep)):
    # Render live from the stored payload so presentation/template changes show on a
    # plain refresh (no costly re-draft). Fall back to the cached HTML if no payload.
    data = storage.load_data_json(rep.hubspot_owner_id)
    if data is not None:
        from .render import render_data
        tracker = storage.load_tracker(rep.hubspot_owner_id)
        streak = int(tracker.get("streak_days", 0)) or 1
        return HTMLResponse(render_data(data, streak=streak, rep_name=rep.rep_name))
    html = storage.load_page(rep.hubspot_owner_id)
    if html is None:
        return HTMLResponse("<p style='font-family:sans-serif;padding:24px'>No slate generated yet. "
                            "Click <b>Run my slate now</b>.</p>")
    return HTMLResponse(html)


@app.post("/run")
def run(rep: Rep = Depends(current_rep)):
    jobs.start(rep)                       # kicks off a background thread, returns instantly
    return RedirectResponse("/", status_code=303)


# ---------------------------- weekly "next week" preview ----------------------------

def _fmt_day(iso: str) -> str:
    from datetime import date
    try:
        return date.fromisoformat(iso).strftime("%A · %b %-d")
    except ValueError:
        return iso


def _week_plan_html(plan: dict, portal_id: str) -> str:
    from .pipeline.enrich import company_record_url
    if not plan or not plan.get("days"):
        return ('<p class="muted">No plan yet. Next week\'s slate is planned automatically '
                'each Friday.</p>')
    cols = ""
    for day in plan["days"]:
        accts = day.get("accounts", [])
        if accts:
            cards = "".join(
                f'<div class="wa">'
                f'<div class="wn">{_html.escape(a.get("name",""))}</div>'
                f'<div class="wm">{_html.escape(" · ".join(x for x in [a.get("vertical",""), a.get("status","")] if x))}</div>'
                f'<div class="wl">{("Dormant since "+_html.escape(a.get("last_touch",""))) if a.get("last_touch") else "Never contacted"}'
                f' · <a href="{_html.escape(company_record_url(portal_id, a.get("id","")))}" target="_blank" rel="noopener">HubSpot ↗</a></div>'
                f'</div>'
                for a in accts
            )
        else:
            cards = '<div class="we">—</div>'
        cols += f'<div class="wcol"><div class="wh">{_fmt_day(day["date"])}<span>{len(accts)}</span></div>{cards}</div>'
    return f'<div class="wgrid">{cols}</div>'


@app.get("/next-week", response_class=HTMLResponse)
def next_week(rep: Rep = Depends(current_rep)):
    plan = storage.load_week_plan(rep.hubspot_owner_id)
    body = _week_plan_html(plan, settings.hubspot_portal_id)
    wk = f' — week of {_fmt_day(plan["week_of"])}' if plan else ""
    css = _WEEK_CSS
    inner = f"""
    <div class="bar"><div><b>Next week</b>{wk} · {_html.escape(rep.rep_name)}</div>
      <a class="btn ghost" href="/">← back to my slate</a></div>
    <div class="wrap">
      <p class="hint">Your planned accounts for next week, spread across each day. These fill your daily
      slate automatically (re-checked each morning; if one gets worked or opened elsewhere it's swapped out).
      Drafts are written the morning each account surfaces.</p>
      {body}
    </div>"""
    return _shell_doc("Next week", f"<style>{css}</style>{inner}")


_WEEK_CSS = ("body{background:#f6f7f9}.wrap{max-width:1200px;margin:0 auto;padding:16px}"
             ".bar{height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;background:#fff;border-bottom:1px solid #e6e8ec}"
             ".hint{color:#646b76;font-size:13px}"
             ".wgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:12px}"
             "@media(max-width:900px){.wgrid{grid-template-columns:1fr}}"
             ".wcol{background:#f0f1f4;border-radius:12px;padding:8px;min-height:80px}"
             ".wh{font-size:12px;font-weight:800;color:#312e81;padding:4px 6px 8px;display:flex;justify-content:space-between;align-items:center}"
             ".wh span{background:#e0e7ff;color:#4338ca;border-radius:999px;padding:1px 8px;font-size:11px}"
             ".wa{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:8px 10px;margin:6px 0}"
             ".wn{font-size:13px;font-weight:700}.wm{font-size:11px;color:#646b76;margin-top:2px}"
             ".wl{font-size:11px;color:#8a909a;margin-top:4px}.wl a{color:#4f46e5;font-weight:700;text-decoration:none}"
             ".we{color:#a0a6b0;text-align:center;padding:12px;font-size:13px}"
             ".btn.sm{padding:7px 12px;font-size:13px}")


# ---------------------------- manual "add company" ----------------------------

@app.get("/add", response_class=HTMLResponse)
def add_page(rep: Rep = Depends(current_rep)):
    """Search your own HubSpot companies and add one to today's slate."""
    tracker = storage.load_tracker(rep.hubspot_owner_id)
    pinned = tracker.get("pinned", [])
    if pinned:
        items = "".join(
            f'<div class="pin"><span>{_html.escape(pn.get("name","")) or pn.get("id")}</span>'
            f'<form method="post" action="/slate/remove">'
            f'<input type="hidden" name="company_id" value="{_html.escape(pn.get("id",""))}">'
            f'<button class="btn sm ghost" type="submit">Remove</button></form></div>'
            for pn in pinned
        )
        pinned_block = f'<h3>Added by you</h3><div class="pins">{items}</div>'
    else:
        pinned_block = ""
    building = ('<p style="color:#b45309;font-size:13px">A slate build is currently running — '
                'wait for it to finish before adding.</p>' if jobs.is_running(rep.hubspot_owner_id) else "")
    css = ("body{background:#f6f7f9}.wrap{max-width:760px;margin:0 auto;padding:16px}"
           "input.q{width:100%;padding:11px;border:1px solid #e6e8ec;border-radius:10px;font-size:15px}"
           ".res{margin:10px 0;display:flex;flex-direction:column;gap:8px}"
           ".card{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:10px 12px;display:flex;align-items:center;gap:12px}"
           ".card .m{flex:1;min-width:0}.card b{font-size:14px}.card .sub{font-size:12px;color:#646b76}"
           ".warn{font-size:11px;color:#b45309}.pins{display:flex;flex-direction:column;gap:6px;margin:8px 0}"
           ".pin{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;font-size:14px}"
           ".btn.sm{padding:7px 12px;font-size:13px}.hint{color:#646b76;font-size:13px}")
    inner = f"""
    <div class="bar"><div><b>Add a company</b> · {_html.escape(rep.rep_name)}</div>
      <a class="btn ghost" href="/">← back to my slate</a></div>
    <div class="wrap">
      {building}
      <p class="hint">Search your own HubSpot companies by name and add one to today's slate.
      It gets fully researched (contacts, verification flags, A/B emails) and pinned so it stays until you remove it.
      You can add accounts that wouldn't auto-surface (recently contacted, open deal, under your location floor) — we'll flag why.</p>
      <input id="q" class="q" placeholder="Type a company name…" autofocus autocomplete="off">
      <div id="res" class="res"></div>
      {pinned_block}
    </div>
    <script>
    const box=document.getElementById('q'), res=document.getElementById('res');
    let t=null;
    box.addEventListener('input',()=>{{clearTimeout(t);t=setTimeout(go,300);}});
    async function go(){{
      const q=box.value.trim();
      if(q.length<2){{res.innerHTML='';return;}}
      res.innerHTML='<p class="hint">Searching…</p>';
      let data;
      try{{ data=await (await fetch('/companies/search?q='+encodeURIComponent(q))).json(); }}
      catch(e){{ res.innerHTML='<p class="warn">Search failed. Try again.</p>'; return; }}
      if(!data.results||!data.results.length){{res.innerHTML='<p class="hint">No matches in your book.</p>';return;}}
      res.innerHTML=data.results.map(c=>{{
        const loc=(c.locations==null)?'locations unknown':c.locations+' locations';
        const sub=[c.domain,loc,c.status,c.last_touch?('last touch '+c.last_touch):''].filter(Boolean).join(' · ');
        const warn=c.notes&&c.notes.length?('<div class="warn">⚠ '+c.notes.join(', ')+'</div>'):'';
        return '<div class="card"><div class="m"><b>'+esc(c.name)+'</b><div class="sub">'+esc(sub)+'</div>'+warn+'</div>'+
          '<form method="post" action="/slate/add"><input type="hidden" name="company_id" value="'+esc(c.id)+'">'+
          '<button class="btn sm" type="submit">Add</button></form></div>';
      }}).join('');
    }}
    function esc(s){{return String(s==null?'':s).replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]));}}
    </script>"""
    return _shell_doc("Add a company", f"<style>{css}</style>{inner}")


@app.get("/companies/search")
async def companies_search(q: str = "", rep: Rep = Depends(current_rep)):
    """Owner-scoped company search for the add picker (JSON). Never returns another
    rep's companies — the search is filtered to this rep's book server-side."""
    from .pipeline.assemble import search_owned
    try:
        results = await search_owned(rep, q)
    except Exception as e:  # surface a clean message to the picker
        return JSONResponse({"results": [], "error": str(e)[:200]}, status_code=200)
    return JSONResponse({"results": results})


@app.post("/slate/add")
async def slate_add(request: Request, rep: Rep = Depends(current_rep)):
    """Add one owned company to today's slate (researched in the background)."""
    form = await request.form()
    company_id = (form.get("company_id") or "").strip()
    if company_id:
        jobs.start_add(rep, company_id)   # background; ownership re-checked in add_company
    return RedirectResponse("/", status_code=303)


@app.post("/slate/remove")
async def slate_remove(request: Request, rep: Rep = Depends(current_rep)):
    """Un-pin a manually added company from this rep's slate."""
    from .pipeline.assemble import remove_company
    form = await request.form()
    company_id = (form.get("company_id") or "").strip()
    if company_id:
        remove_company(rep, company_id)
    return RedirectResponse("/add", status_code=303)


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


# ---------------------------- admin portal ----------------------------

def require_admin(rep: Rep = Depends(current_rep)) -> Rep:
    if not rep.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return rep


@app.get("/admin", response_class=HTMLResponse)
def admin(rep: Rep = Depends(require_admin)):
    reps = sorted(load_reps().values(),
                  key=lambda r: (not r.active, (r.team or "~"), r.rep_name.lower()))
    teams = sorted({r.team for r in reps if r.team})
    team_opts = "".join(f'<option value="{_html.escape(t)}">{_html.escape(t)}</option>' for t in teams)

    rows = ""
    for r in reps:
        # admins are always active and cannot be switched off (prevents self-lockout)
        if r.is_admin:
            active_ctrl = ('<label class="c"><input type="checkbox" checked disabled> active</label>'
                           '<input type="hidden" name="active" value="on">')
        else:
            active_ctrl = f'<label class="c"><input type="checkbox" name="active" {"checked" if r.active else ""}> active</label>'
        # admin role: you cannot demote yourself (no self-lockout); others are toggleable
        if r.email == rep.email:
            admin_ctrl = ('<label class="c" title="You can\'t remove your own admin access">'
                          '<input type="checkbox" checked disabled> admin (you)</label>'
                          '<input type="hidden" name="make_admin" value="on">')
        else:
            admin_ctrl = (f'<label class="c" title="Admin-board access"><input type="checkbox" '
                          f'name="make_admin" {"checked" if r.is_admin else ""}> admin</label>')
        rows += f"""
        <form method="post" action="/admin/rep" class="r{' off' if not r.active else ''}">
          <input type="hidden" name="email" value="{_html.escape(r.email)}">
          <div class="who"><b>{_html.escape(r.rep_name)}</b><span>{_html.escape(r.email)} · owner {_html.escape(r.hubspot_owner_id)}</span></div>
          {active_ctrl}
          {admin_ctrl}
          <label class="c">slate <input type="number" name="slate_size" value="{r.slate_size}" min="1" max="10"></label>
          <label class="c" title="Min locations to qualify. Blank = global default ({settings.location_floor}).">min-loc <input type="number" name="location_floor" value="{r.location_floor if r.location_floor is not None else ''}" min="1" max="5000" placeholder="{settings.location_floor}"></label>
          <label class="c" title="Max locations to qualify. Blank = no ceiling.">max-loc <input type="number" name="max_locations" value="{r.max_locations if r.max_locations is not None else ''}" min="1" max="5000" placeholder="∞"></label>
          <label class="c"><input type="checkbox" name="auto_slate" {'checked' if r.auto_slate else ''}> 7AM</label>
          <input class="tm" name="team" value="{_html.escape(r.team)}" placeholder="team">
          <button class="btn sm" type="submit">Save</button>
        </form>"""

    n_active = sum(1 for r in reps if r.active)
    n_auto = sum(1 for r in reps if r.auto_slate)
    sched_on = schedule_state.is_enabled()
    toggle_label = "Turn OFF" if sched_on else "Turn ON"
    toggle_to = "0" if sched_on else "1"
    warn = "" if n_auto else '<span style="color:#b45309">— tag reps 7AM first</span> '
    sched = (f'<div class="sched"><b>Morning auto-run:</b> '
             f'{"🟢 ON" if sched_on else "⚪ OFF"} · weekday {settings.schedule_hour:02d}:00 {settings.schedule_tz} · '
             f'{n_auto} rep(s) tagged 7AM. {warn}'
             f'<form method="post" action="/admin/schedule-toggle" style="display:inline">'
             f'<input type="hidden" name="enabled" value="{toggle_to}">'
             f'<button class="btn sm" type="submit">{toggle_label}</button></form>'
             f'<form method="post" action="/admin/run-scheduled" style="display:inline">'
             f'<button class="btn sm ghost" type="submit">Run the 7AM batch now (test)</button></form>'
             f'<form method="post" action="/admin/plan-week" style="display:inline">'
             f'<button class="btn sm ghost" type="submit">Plan next week now (test)</button></form>'
             f'<a class="btn sm ghost" href="/admin/next-week">View next-week plans →</a></div>')
    # password hygiene: admins must use a distinct, non-empty admin password
    ap, rp = settings.bootstrap_password_admin, settings.bootstrap_password
    n_admin = sum(1 for r in reps if r.is_admin)
    if not ap:
        pw_banner = ('<div class="pwwarn">&#9888; <b>Admin password not set.</b> '
                     'Admins are falling back to the standard rep password. Set '
                     '<code>BOOTSTRAP_PASSWORD_ADMIN</code> in Render to a strong, distinct value.</div>')
    elif ap == rp:
        pw_banner = ('<div class="pwwarn">&#9888; <b>Admin password equals the rep password.</b> '
                     'Change <code>BOOTSTRAP_PASSWORD_ADMIN</code> in Render so it differs from '
                     '<code>BOOTSTRAP_PASSWORD</code>.</div>')
    else:
        pw_banner = (f'<div class="pwok">&#10003; Admin access is protected by a distinct admin '
                     f'password ({n_admin} admin(s)). It differs from the rep password.</div>')

    inner = f"""
    <div class="bar"><div><b>Admin</b> · rep settings <span class="muted">({n_active} active of {len(reps)})</span></div>
      <div class="actions"><a class="btn ghost" href="/admin/unassigned">Unassigned ICP accounts →</a>
      <a class="btn ghost" href="/">← back to my slate</a></div></div>
    <div class="wrap">
      {pw_banner}
      {sched}
      <form method="post" action="/admin/bulk" class="bulk">
        <b>Bulk:</b>
        <select name="scope"><option value="__all__">All reps</option>{team_opts}</select>
        <select name="active"><option value="">active: leave</option><option value="on">activate</option><option value="off">deactivate</option></select>
        <select name="auto_slate"><option value="">7AM: leave</option><option value="on">on</option><option value="off">off</option></select>
        <label>slate <input type="number" name="slate_size" min="1" max="10" placeholder="—" style="width:56px"></label>
        <label>min-loc <input type="number" name="location_floor" min="1" max="5000" placeholder="—" style="width:64px"></label>
        <label>max-loc <input type="number" name="max_locations" min="1" max="5000" placeholder="—" style="width:64px"></label>
        <button class="btn" type="submit">Apply to group</button>
      </form>
      <p class="muted" style="font-size:12px">Deactivate the HubSpot users who will never use this so they drop off the login. Set slate size per rep (e.g. 5). <b>min-loc</b>/<b>max-loc</b> set the company-size band by location count for that rep's search: min-loc blank inherits the global default ({settings.location_floor}), max-loc blank means no upper limit. E.g. 15–50 targets mid-size multi-unit only. Tag <b>7AM</b> to include a rep in the scheduled morning run. Tick <b>admin</b> to grant a teammate admin-board access — their login password is set to the admin password automatically.</p>
      <div class="rows">{rows}</div>
    </div>"""
    css = ("body{background:#f6f7f9}.wrap{max-width:1000px;margin:0 auto;padding:16px}"
           ".pwwarn{background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;border-radius:10px;padding:10px 13px;margin:14px 0;font-size:13px}"
           ".pwok{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;border-radius:10px;padding:9px 13px;margin:14px 0;font-size:13px}"
           ".pwwarn code,.pwok code{background:rgba(0,0,0,.06);padding:1px 5px;border-radius:4px;font-size:12px}"
           ".sched{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:12px;margin:14px 0;font-size:13px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}"
           ".bar{height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;background:#fff;border-bottom:1px solid #e6e8ec}"
           ".bulk{display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:12px;margin:14px 0}"
           ".bulk select,.bulk input{padding:7px;border:1px solid #e6e8ec;border-radius:8px;font-size:13px}"
           ".r{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:8px 12px;margin:6px 0;flex-wrap:wrap}"
           ".r.off{opacity:.55}.who{flex:1;min-width:200px;display:flex;flex-direction:column}.who span{font-size:11px;color:#646b76}"
           ".c{font-size:13px;display:flex;align-items:center;gap:4px;white-space:nowrap}.c input[type=number]{width:48px;padding:4px;border:1px solid #e6e8ec;border-radius:6px}"
           ".tm{width:110px;padding:6px;border:1px solid #e6e8ec;border-radius:8px;font-size:13px}"
           ".btn.sm{padding:7px 12px;font-size:13px}")
    return _shell_doc("Admin", f"<style>{css}</style>{inner}")


def _opt_loc(raw) -> int | None:
    """Parse an optional location bound; blank/invalid -> None (clear / no bound)."""
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return max(1, min(5000, int(s)))
    except ValueError:
        return None


@app.post("/admin/rep")
async def admin_rep(request: Request, rep: Rep = Depends(require_admin)):
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    target = get_rep(email)
    if target:
        try:
            size = max(1, min(10, int(form.get("slate_size") or 3)))
        except ValueError:
            size = 3
        # blank min/max-loc -> None -> cleared (floor inherits global; ceiling = none)
        floor = _opt_loc(form.get("location_floor"))
        ceil = _opt_loc(form.get("max_locations"))

        # admin role change (you can never demote yourself). On a real change, sync
        # the login password so admin-board access stays gated by the admin secret.
        want_admin = ("make_admin" in form) or (email == rep.email)
        extra: dict = {}
        if want_admin != target.is_admin:
            extra["role"] = "admin" if want_admin else "rep"
            if want_admin and settings.bootstrap_password_admin:
                auth.set_password(email, settings.bootstrap_password_admin)
            elif not want_admin and settings.bootstrap_password:
                auth.set_password(email, settings.bootstrap_password)

        overrides.set_fields(email, active=("active" in form) or want_admin,
                             auto_slate=("auto_slate" in form),
                             slate_size=size, location_floor=floor, max_locations=ceil,
                             team=(form.get("team") or "").strip(), **extra)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/bulk")
async def admin_bulk(request: Request, rep: Rep = Depends(require_admin)):
    form = await request.form()
    scope = form.get("scope") or "__all__"
    targets = [e for e, r in load_reps().items() if scope == "__all__" or r.team == scope]
    fields: dict = {}
    if form.get("active") in ("on", "off"):
        fields["active"] = form.get("active") == "on"
    if form.get("auto_slate") in ("on", "off"):
        fields["auto_slate"] = form.get("auto_slate") == "on"
    if (form.get("slate_size") or "").strip():
        try:
            fields["slate_size"] = max(1, min(10, int(form["slate_size"])))
        except ValueError:
            pass
    if (v := _opt_loc(form.get("location_floor"))) is not None:
        fields["location_floor"] = v
    if (v := _opt_loc(form.get("max_locations"))) is not None:
        fields["max_locations"] = v
    if fields and targets:
        overrides.set_bulk(targets, **fields)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/assign")
async def admin_assign(request: Request, rep: Rep = Depends(require_admin)):
    """Assign an unowned ICP account to a rep by pinning it to that rep's slate
    (no HubSpot write). Researched in the background under the target rep's owner."""
    form = await request.form()
    company_id = (form.get("company_id") or "").strip()
    email = (form.get("email") or "").strip().lower()
    name = (form.get("company_name") or "").strip()
    target = get_rep(email)
    if company_id and target and target.active:
        jobs.start_assign(target, company_id)
        msg = f"Assigned {name or company_id} to {target.rep_name} — building their slate now."
    else:
        msg = "Could not assign: pick an active rep."
    return RedirectResponse(f"/admin/unassigned?msg={_urlquote(msg)}", status_code=303)


@app.get("/admin/unassigned", response_class=HTMLResponse)
async def admin_unassigned(rep: Rep = Depends(require_admin),
                           min: int = 0, max: int = 0, unknown: int = 0, msg: str = ""):
    """ICP accounts with NO owner — nobody is working them. Same ICP gates as the
    daily search. Admin can assign one to a rep."""
    from .hubspot.eligibility import unowned_icp_pool
    floor = min if min > 0 else settings.location_floor
    ceiling = max if max > 0 else None
    incl = bool(unknown)
    try:
        pool = await unowned_icp_pool(floor=floor, ceiling=ceiling, include_unknown=incl)
        err = ""
    except Exception as e:
        pool, err = [], str(e)

    reps_opts = "".join(
        f'<option value="{_html.escape(r.email)}">{_html.escape(r.rep_name)}</option>'
        for r in sorted(active_reps(), key=lambda r: r.rep_name.lower())
    )
    from .pipeline.enrich import company_record_url
    portal_id = settings.hubspot_portal_id
    rows = ""
    for c in pool:
        loc = "—" if c["locations"] is None else str(c["locations"])
        sub = " · ".join(x for x in [c["domain"], c["vertical"], c["status"]] if x)
        hs = company_record_url(portal_id, c["id"])
        rows += f"""
        <div class="r">
          <div class="who"><b>{_html.escape(c['name'])}</b><span>{_html.escape(sub)}</span></div>
          <div class="loc">{loc} loc</div>
          <a class="hs" href="{_html.escape(hs)}" target="_blank" rel="noopener">HubSpot ↗</a>
          <form method="post" action="/admin/assign" class="asg">
            <input type="hidden" name="company_id" value="{_html.escape(c['id'])}">
            <input type="hidden" name="company_name" value="{_html.escape(c['name'])}">
            <select name="email">{reps_opts}</select>
            <button class="btn sm" type="submit">Assign</button>
          </form>
        </div>"""
    if err:
        rows = f'<p style="color:#b91c1c">Could not load: {_html.escape(err[:200])}</p>'
    elif not pool:
        rows = '<p class="muted">No unowned accounts match this filter.</p>'

    ck = "checked" if incl else ""
    filt = (f'<form method="get" action="/admin/unassigned" class="bulk">'
            f'<b>Filter:</b> <label>min-loc <input type="number" name="min" value="{floor}" min="1" max="5000" style="width:64px"></label>'
            f'<label>max-loc <input type="number" name="max" value="{max or ""}" min="1" max="5000" placeholder="—" style="width:64px"></label>'
            f'<label><input type="checkbox" name="unknown" value="1" {ck}> include unknown location count</label>'
            f'<button class="btn sm" type="submit">Apply</button></form>')
    css = ("body{background:#f6f7f9}.wrap{max-width:1000px;margin:0 auto;padding:16px}"
           ".bar{height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;background:#fff;border-bottom:1px solid #e6e8ec}"
           ".bulk{display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:12px;margin:14px 0}"
           ".bulk input,.bulk select{padding:7px;border:1px solid #e6e8ec;border-radius:8px;font-size:13px}"
           ".r{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:8px 12px;margin:6px 0}"
           ".who{flex:1;min-width:200px;display:flex;flex-direction:column}.who span{font-size:11px;color:#646b76}"
           ".loc{font-size:13px;font-weight:700;color:#5b21b6;white-space:nowrap}"
           ".hs{font-size:12px;font-weight:700;color:#4f46e5;text-decoration:none;white-space:nowrap}"
           ".asg{display:flex;gap:6px;align-items:center}.asg select{padding:6px;border:1px solid #e6e8ec;border-radius:8px;font-size:13px;max-width:160px}"
           ".flash{background:#d1fae5;border:1px solid #a7f3d0;color:#065f46;border-radius:10px;padding:10px 12px;margin:12px 0;font-size:14px}"
           ".btn.sm{padding:7px 12px;font-size:13px}.hint{color:#646b76;font-size:13px}")
    inner = f"""
    <div class="bar"><div><b>Unassigned ICP accounts</b> <span class="muted">({len(pool)} shown)</span></div>
      <a class="btn ghost" href="/admin">← back to admin</a></div>
    <div class="wrap">
      {f'<div class="flash">{_html.escape(msg)}</div>' if msg else ''}
      <p class="hint">Companies in HubSpot with <b>no owner</b> that still fit ICP (no open deal, not a customer,
      not blacklisted, within the location band) — nobody is working these. Assign one to a rep to put it in play.
      This pins the researched account to that rep's slate; it does not change ownership in HubSpot.</p>
      {filt}
      <div class="rows">{rows}</div>
    </div>"""
    return _shell_doc("Unassigned ICP accounts", f"<style>{css}</style>{inner}")


@app.post("/admin/run-scheduled")
def admin_run_scheduled(rep: Rep = Depends(require_admin)):
    """Run the same batch the 7AM job runs (all auto_slate reps) — lets you test
    the morning flow on demand instead of waiting for 7AM."""
    targets = [r for r in active_reps() if r.auto_slate]
    jobs.start_batch(targets)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/plan-week")
def admin_plan_week(rep: Rep = Depends(require_admin)):
    """Run the Friday planning now (all auto_slate reps) + post the Slack summary."""
    targets = [r for r in active_reps() if r.auto_slate]
    jobs.start_week_planning(targets)
    return RedirectResponse("/admin/next-week?msg=" + _urlquote(
        f"Planning next week for {len(targets)} rep(s) — refresh in a moment."), status_code=303)


@app.get("/admin/next-week", response_class=HTMLResponse)
def admin_next_week(rep: Rep = Depends(require_admin), msg: str = ""):
    """Overview of every rep's next-week plan."""
    reps = [r for r in active_reps() if r.auto_slate] or active_reps()
    portal_id = settings.hubspot_portal_id
    blocks = ""
    for r in sorted(reps, key=lambda r: r.rep_name.lower()):
        plan = storage.load_week_plan(r.hubspot_owner_id)
        n = sum(len(d.get("accounts", [])) for d in plan.get("days", [])) if plan else 0
        wk = f' · week of {_fmt_day(plan["week_of"])}' if plan else ""
        blocks += (f'<div class="repblk"><div class="rh"><b>{_html.escape(r.rep_name)}</b> '
                   f'<span class="muted">{n} planned{wk}</span></div>'
                   f'{_week_plan_html(plan, portal_id)}</div>')
    flash = f'<div class="flash">{_html.escape(msg)}</div>' if msg else ""
    css = _WEEK_CSS + ".repblk{margin:18px 0}.rh{margin:6px 2px}.flash{background:#d1fae5;border:1px solid #a7f3d0;color:#065f46;border-radius:10px;padding:10px 12px;margin:12px 0;font-size:14px}"
    inner = f"""
    <div class="bar"><div><b>Next-week plans</b> <span class="muted">({len(reps)} reps)</span></div>
      <a class="btn ghost" href="/admin">← back to admin</a></div>
    <div class="wrap">{flash}
      <p class="hint">Planned Friday for the coming week (eligibility only — drafts are written each
      morning). Use "Plan next week now" on the admin board to (re)generate.</p>
      {blocks}
    </div>"""
    return _shell_doc("Next-week plans", f"<style>{css}</style>{inner}")


@app.post("/admin/schedule-toggle")
async def admin_schedule_toggle(request: Request, rep: Rep = Depends(require_admin)):
    """Flip the weekday-morning auto-run on/off. Persisted on disk; no redeploy."""
    form = await request.form()
    schedule_state.set_enabled((form.get("enabled") or "").strip() == "1")
    return RedirectResponse("/admin", status_code=303)


# ---------------------------- html helpers ----------------------------

def _forbidden(msg: str) -> HTMLResponse:
    return HTMLResponse(_shell_doc("Access denied",
        f'<div class="box"><h1>Access denied</h1><p class="muted">{_html.escape(msg)}</p>'
        f'<a class="btn ghost" href="/login">Back to sign in</a></div>'), status_code=403)


def _shell_doc(title: str, inner: str, full: bool = False, picker: bool = False,
               refresh: int = 0) -> str:
    frame_css = (
        "iframe{width:100%;border:0;height:calc(100vh - 56px)}"
        ".bar{height:56px;display:flex;align-items:center;justify-content:space-between;"
        "padding:0 18px;background:#fff;border-bottom:1px solid #e6e8ec;position:sticky;top:0;z-index:5}"
        ".actions{display:flex;gap:10px;align-items:center}"
    )
    picker_css = (
        ".picker{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}"
        "@media(max-width:520px){.picker{grid-template-columns:1fr}}"
        ".pick{width:100%;text-align:left;background:#fff;border:1px solid #e6e8ec;border-radius:12px;"
        "padding:14px 16px;cursor:pointer;display:flex;flex-direction:column;gap:2px;transition:border-color .1s,box-shadow .1s}"
        ".pick:hover{border-color:#4f46e5;box-shadow:0 4px 14px rgba(79,70,229,.12)}"
        ".pn{font-weight:800;font-size:15px;color:#16181d}"
        ".pe{font-size:12px;color:#646b76}"
    )
    refresh_tag = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{refresh_tag}
<title>{_html.escape(title)}</title>
<style>
.spinner{{width:28px;height:28px;margin:18px auto 0;border:3px solid #e6e8ec;border-top-color:#4f46e5;border-radius:50%;animation:spin 1s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f6f7f9;color:#16181d}}
.muted{{color:#646b76;font-size:14px}}
.box{{max-width:460px;margin:12vh auto;background:#fff;border:1px solid #e6e8ec;border-radius:16px;padding:32px;text-align:center}}
h1{{font-size:22px;margin:0 0 8px}}
.btn{{display:inline-block;background:#4f46e5;color:#fff;border:none;border-radius:10px;padding:11px 18px;font-weight:800;font-size:14px;cursor:pointer;text-decoration:none}}
.btn:hover{{background:#4338ca}}
.btn.ghost{{background:#fff;color:#16181d;border:1px solid #e6e8ec;margin-top:10px}}
form{{margin:0}}
{frame_css if full else ""}
{picker_css if picker else ""}
</style></head><body>{inner}</body></html>"""
