# IONOS Web Hosting Plus — Setup Guide

This covers one-time IONOS setup, GitHub secrets, and how to run the first sync.

## Architecture

```
GitHub Actions (every 6h)
  → garmin_dash.sync  (pulls last 7 days from Garmin API)
  → garmin_dash.export (writes JSON to backend/export/)
  → SFTP upload JSON → IONOS public data folder
  → SFTP upload garmin.db → IONOS private folder

GitHub Pages (static site)
  → fetches JSON from IONOS data folder via HTTPS
```

---

## 1. IONOS folder structure (gleearl.com — as configured)

The SFTP user (`a1002472`) lands in the **webspace home root**. The domain
`gleearl.com` is connected (Domains → Connect to webspace) with **Target =
`/garmin-data`**, so the domain serves *from inside* that folder.

| Path (relative to SFTP home) | Purpose | Served at |
|------|---------|-----------|
| `garmin-data/` | JSON files | `https://gleearl.com/` (no `/garmin-data/` in the URL!) |
| `garmin.db` (home root) | SQLite cache (private) | Not web-served |

> **Key consequence:** `garmin-data/daily.json` is reachable at
> `https://gleearl.com/daily.json` — NOT `https://gleearl.com/garmin-data/daily.json`.
> Files in the SFTP home root (the parent of `garmin-data`) are not web-served, so
> `garmin.db` is safe there.

---

## 2. CORS header on the data folder

Create `garmin-data/.htaccess` (already done):

```apache
Header set Access-Control-Allow-Origin "https://gleearl.github.io"
Header set Cache-Control "public, max-age=300"
<Files "*.db">
  Require all denied
</Files>
```

This allows your GitHub Pages site to fetch the JSON cross-origin.
Adjust the origin if your Pages URL changes.

---

## 3. Generate your Garmin token secret

Run locally (requires a valid `~/.garminconnect` token store from a prior login):

```bash
cd backend
uv run python -m garmin_dash.token_dump
```

Copy the printed base64 string — it's the value for `GARMIN_TOKEN_BASE64`.

---

## 4. GitHub secrets & variables

Go to **Settings → Secrets and variables → Actions** in your repo.

### Secrets (encrypted)

| Secret | Value |
|--------|-------|
| `GARMIN_TOKEN_BASE64` | Output from `token_dump` above |
| `IONOS_SFTP_HOST` | `access-5020736834.webspace-host.com` |
| `IONOS_SFTP_USER` | `a1002472` |
| `IONOS_SFTP_PASSWORD` | Your IONOS SFTP password |
| `IONOS_DATA_PATH` | `garmin-data` |

> The DB is stored at the SFTP home root (`garmin.db`), which is not web-served,
> so no separate `IONOS_DB_PATH` secret is needed.

### Variables (non-sensitive, used in the deploy workflow)

| Variable | Value |
|----------|-------|
| `IONOS_DATA_URL` | `https://gleearl.com` |

---

## 5. First sync (bootstrap)

If you have an existing `garmin.db` from local dev, upload it to the SFTP home
root first so you don't lose history:

```bash
sftp a1002472@access-5020736834.webspace-host.com
> put backend/garmin.db garmin.db
> quit
```

Then trigger the workflow manually:
**GitHub → Actions → "Sync Garmin data to IONOS" → Run workflow**

After it completes, visit `https://gleearl.com/meta.json` to confirm the JSON landed.

---

## 6. Update GitHub Pages deploy

After adding the `IONOS_DATA_URL` variable, re-run the **"Deploy to GitHub Pages"**
workflow (or push any frontend change) to bake the IONOS URL into the build.

---

## 7. Refreshing the token

Garmin OAuth tokens expire (typically every 30–90 days). When the sync workflow
starts failing with auth errors, re-run `token_dump` locally and update the
`GARMIN_TOKEN_BASE64` secret.

---

## Finding your IONOS SFTP hostname

IONOS → Hosting → FTP Access → the hostname shown there (e.g. `access123456.webspace-data.io`).
Port is 22 for SFTP.
