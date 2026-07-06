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

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .registry import Rep, get_rep, active_reps, load_reps
from . import auth, storage, overrides
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
    """Weekday 7AM auto-generation (only if SCHEDULE_ENABLED)."""
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
    html = storage.load_page(rep.hubspot_owner_id)
    if html is None:
        return HTMLResponse("<p style='font-family:sans-serif;padding:24px'>No slate generated yet. "
                            "Click <b>Run my slate now</b>.</p>")
    return HTMLResponse(html)


@app.post("/run")
def run(rep: Rep = Depends(current_rep)):
    jobs.start(rep)                       # kicks off a background thread, returns instantly
    return RedirectResponse("/", status_code=303)


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
            active_ctrl = ('<label class="c"><input type="checkbox" checked disabled> active '
                           '<span style="font-size:10px;color:#4f46e5">(admin)</span></label>'
                           '<input type="hidden" name="active" value="on">')
        else:
            active_ctrl = f'<label class="c"><input type="checkbox" name="active" {"checked" if r.active else ""}> active</label>'
        rows += f"""
        <form method="post" action="/admin/rep" class="r{' off' if not r.active else ''}">
          <input type="hidden" name="email" value="{_html.escape(r.email)}">
          <div class="who"><b>{_html.escape(r.rep_name)}</b><span>{_html.escape(r.email)} · owner {_html.escape(r.hubspot_owner_id)}</span></div>
          {active_ctrl}
          <label class="c">slate <input type="number" name="slate_size" value="{r.slate_size}" min="1" max="10"></label>
          <label class="c"><input type="checkbox" name="auto_slate" {'checked' if r.auto_slate else ''}> 7AM</label>
          <input class="tm" name="team" value="{_html.escape(r.team)}" placeholder="team">
          <button class="btn sm" type="submit">Save</button>
        </form>"""

    n_active = sum(1 for r in reps if r.active)
    n_auto = sum(1 for r in reps if r.auto_slate)
    sched_on = settings.schedule_enabled
    sched = (f'<div class="sched"><b>Morning auto-run:</b> '
             f'{"🟢 ON" if sched_on else "⚪ OFF"} · weekday {settings.schedule_hour:02d}:00 {settings.schedule_tz} · '
             f'{n_auto} rep(s) tagged 7AM. '
             f'{"" if sched_on else "Set SCHEDULE_ENABLED=true in Render to arm it. "}'
             f'<form method="post" action="/admin/run-scheduled" style="display:inline">'
             f'<button class="btn sm" type="submit">Run the 7AM batch now (test)</button></form></div>')
    inner = f"""
    <div class="bar"><div><b>Admin</b> · rep settings <span class="muted">({n_active} active of {len(reps)})</span></div>
      <a class="btn ghost" href="/">← back to my slate</a></div>
    <div class="wrap">
      {sched}
      <form method="post" action="/admin/bulk" class="bulk">
        <b>Bulk:</b>
        <select name="scope"><option value="__all__">All reps</option>{team_opts}</select>
        <select name="active"><option value="">active: leave</option><option value="on">activate</option><option value="off">deactivate</option></select>
        <select name="auto_slate"><option value="">7AM: leave</option><option value="on">on</option><option value="off">off</option></select>
        <label>slate <input type="number" name="slate_size" min="1" max="10" placeholder="—" style="width:56px"></label>
        <button class="btn" type="submit">Apply to group</button>
      </form>
      <p class="muted" style="font-size:12px">Deactivate the HubSpot users who will never use this so they drop off the login. Set slate size per rep (e.g. 5). Tag <b>7AM</b> to include a rep in the scheduled morning run.</p>
      <div class="rows">{rows}</div>
    </div>"""
    css = ("body{background:#f6f7f9}.wrap{max-width:1000px;margin:0 auto;padding:16px}"
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


@app.post("/admin/rep")
async def admin_rep(request: Request, rep: Rep = Depends(require_admin)):
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    if get_rep(email):
        try:
            size = max(1, min(10, int(form.get("slate_size") or 3)))
        except ValueError:
            size = 3
        overrides.set_fields(email, active=("active" in form), auto_slate=("auto_slate" in form),
                             slate_size=size, team=(form.get("team") or "").strip())
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
    if fields and targets:
        overrides.set_bulk(targets, **fields)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/run-scheduled")
def admin_run_scheduled(rep: Rep = Depends(require_admin)):
    """Run the same batch the 7AM job runs (all auto_slate reps) — lets you test
    the morning flow on demand instead of waiting for 7AM."""
    targets = [r for r in active_reps() if r.auto_slate]
    jobs.start_batch(targets)
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
