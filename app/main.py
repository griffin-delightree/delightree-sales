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
from .registry import Rep, get_rep, active_reps
from . import auth, storage
from .pipeline.assemble import build_slate

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
    """First deploy: if no passwords exist yet and BOOTSTRAP_PASSWORD is set, seed
    every rep with it so the team can log in immediately. Rotate per-user after."""
    from .registry import load_reps
    if not settings.bootstrap_password:
        return
    existing = auth._load_creds()
    if existing:
        return
    for email in load_reps():
        auth.set_password(email, settings.bootstrap_password)

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
    has_page = storage.load_page(rep.hubspot_owner_id) is not None
    body = (
        '<iframe src="/page" title="Daily slate"></iframe>'
        if has_page else
        '<div class="box"><h1>No slate yet</h1>'
        '<p class="muted">Generate your first daily re-engagement slate.</p></div>'
    )
    bar = f"""
      <div class="bar">
        <div><b>Daily Re-Engagement</b> &middot; {_html.escape(rep.rep_name)}
             <span class="muted">(owner {_html.escape(rep.hubspot_owner_id)})</span></div>
        <div class="actions">
          <form method="post" action="/run" onsubmit="this.querySelector('button').disabled=true;this.querySelector('button').textContent='Running (this can take a minute)...'">
            <button class="btn" type="submit">Run my slate now</button>
          </form>
          <a class="btn ghost" href="/logout">Log out</a>
        </div>
      </div>"""
    return _shell_doc(f"{rep.rep_name} - Daily Slate", bar + body, full=True)


@app.get("/page", response_class=HTMLResponse)
def page(rep: Rep = Depends(current_rep)):
    html = storage.load_page(rep.hubspot_owner_id)
    if html is None:
        return HTMLResponse("<p style='font-family:sans-serif;padding:24px'>No slate generated yet. "
                            "Click <b>Run my slate now</b>.</p>")
    return HTMLResponse(html)


@app.post("/run")
async def run(rep: Rep = Depends(current_rep)):
    await build_slate(rep)
    return RedirectResponse("/", status_code=303)


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


# ---------------------------- html helpers ----------------------------

def _forbidden(msg: str) -> HTMLResponse:
    return HTMLResponse(_shell_doc("Access denied",
        f'<div class="box"><h1>Access denied</h1><p class="muted">{_html.escape(msg)}</p>'
        f'<a class="btn ghost" href="/login">Back to sign in</a></div>'), status_code=403)


def _shell_doc(title: str, inner: str, full: bool = False, picker: bool = False) -> str:
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
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_html.escape(title)}</title>
<style>
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
