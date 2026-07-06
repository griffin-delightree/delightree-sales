# Deploy the portal as a live URL (Render)

Goal: a real HTTPS link (e.g. `https://delightree-portal.onrender.com`) your team just
opens and logs into. **No setup for reps** — they only need the URL + their password.
You (the admin) do this one-time setup through web dashboards; no coding.

Everything is already prepared: `Dockerfile`, `render.yaml`, HTTPS session cookie,
first-boot password bootstrap, and `reps.json` with all 43 HubSpot users.

---

## Step 1 — Put the code in a private GitHub repo (one time)
Render deploys from a git repo. Make it **private** (it contains rep names/emails).

From the project folder:
```bash
git init
git add .
git commit -m "Delightree prospecting portal"
```
Then on github.com: create a new **private** repo, and follow its "push existing repo" lines:
```bash
git remote add origin https://github.com/<you>/delightree-portal.git
git branch -M main
git push -u origin main
```
`.env`, `data/`, and `credentials.json` are gitignored — **no secrets are pushed.**

## Step 2 — Create the service on Render
1. Sign up at [render.com](https://render.com) (free).
2. **New + → Blueprint** → connect your GitHub → pick the repo.
3. Render reads `render.yaml` and proposes a web service **+ a 1 GB persistent disk**. Click **Apply**.

## Step 3 — Paste the secrets (Environment tab)
Render will prompt for the three `sync:false` values (or add them under the service's **Environment**):
| Key | Value |
|---|---|
| `HUBSPOT_TOKEN` | your HubSpot private-app token |
| `ANTHROPIC_API_KEY` | your `sk-ant-…` key |
| `BOOTSTRAP_PASSWORD` | a temporary team password (e.g. `Delightree!launch`) |

`SESSION_SECRET` is auto-generated; `DATA_DIR`, `SESSION_HTTPS_ONLY`, `HUBSPOT_PORTAL_ID`,
`ANTHROPIC_MODEL` are already set by the blueprint. Save → Render builds and deploys (~3-5 min).

## Step 4 — Share the URL
You get `https://<name>.onrender.com`. On first boot the app seeds **every rep** with your
`BOOTSTRAP_PASSWORD`. Send the team: **the URL + that password.** They open it → pick their
name → enter the password → their own scoped slate.

(Optional custom domain: service **Settings → Custom Domains → Add** `prospecting.delightree.com`,
then add the CNAME Render shows you at your DNS provider.)

---

## After launch

**Set real per-user passwords** (replaces the shared bootstrap). Open the service's
**Shell** tab in Render and run:
```bash
python cli.py set-password someone@delightree.com 'their-password'
```
Passwords live on the persistent disk, so they survive redeploys.

**Rotate the secrets** you pasted into chat during development (HubSpot token + Anthropic key)
from their respective consoles, and update them in Render's Environment tab.

**Add new HubSpot users later:** in the Render Shell, `python cli.py import-owners` refreshes the
roster from HubSpot (also commit the updated `reps.json` so it survives a rebuild).

**Slates today are on-demand:** a rep's first login shows "Run my slate now" (~3 min with Opus).
The **7AM scheduler** (not built yet) is the next step so slates are pre-generated and just *there*
on login — see the note in README before enabling it (drafting cost scales with how many reps
you auto-run daily).

---

## Other hosts
The `Dockerfile` is standard, so this also runs on Fly.io, Railway, Google Cloud Run, or any
container host. You'd replicate the same four env secrets + a persistent volume mounted at
`/var/data`. Render is the least-effort for a non-DevOps admin.
