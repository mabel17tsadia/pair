# Pair deployment notes

This guide records deployment details for the fictional Pair demonstration. The current
`pair-ui-redesign` challenge submission is on Vercel; the earlier prototype remains on Render.
Role switching is a workspace preview only; it is not authentication or authorization.

## Current application shape

- Flask exports the WSGI application as `app` from the root `app.py` file. The local development
  server starts only when `app.py` is run directly.
- Templates use Flask/Jinja. Stylesheets and scripts live in `public/`, which Vercel serves from
  its CDN and Flask serves locally or on Render through `url_for('static', ...)`.
- Python dependencies are declared in `requirements.txt`. The application uses no Vercel-specific
  routing wrapper or `vercel.json` because Vercel detects the root Flask application automatically.
- CSV files and `data/demo_records.json` are read-only fictional fixtures. The app does not write
  member changes into the repository or local filesystem.

Vercel's [Flask deployment guide](https://vercel.com/docs/frameworks/backend/flask) recognizes a
root `app.py` exporting `app`, installs dependencies from `requirements.txt`, and serves static
assets from `public/`. The project follows those conventions and does not need an explicit
`vercel.json`.

## Local development

From the repository root in PowerShell:

1. Create the virtual environment once: `python -m venv venv`
2. Install dependencies once: `venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Supply a local `SECRET_KEY` through the ignored `.env` file or the shell environment.
4. Start Pair: `venv\Scripts\python.exe app.py`
5. Open `http://127.0.0.1:5000`.

The `.env` file is ignored by Git. Never paste its values into source, documentation, logs, or a
commit.

## Existing Render deployment

Keep the existing Render service and configuration in place:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Render environment-variable names: `SECRET_KEY` is required. `ANTHROPIC_API_KEY` is optional.
  Google Health OAuth uses `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and
  `GOOGLE_REDIRECT_URI` when explicitly enabled.

This audit does not change, replace, disconnect, or deploy the Render service.

## Current Vercel project `pair-mvp`

The current challenge submission is available at <https://pair-mvp.vercel.app> and uses the
`pair-ui-redesign` branch. These settings document the existing project and can also be used if it
needs to be recreated:

1. Import the `mabel17tsadia/pair` repository into Vercel.
2. Set the Vercel project name to `pair-mvp` and the project root to the repository root.
3. Set the Production Branch to `pair-ui-redesign`.
4. Leave the Build Command and Output Directory unset so Vercel can use its Flask/Python detection.
   Dependencies are installed from `requirements.txt`; there is no separate frontend build step.
5. Add `SECRET_KEY` under the Vercel project's Environment Variables. Use a strong random value,
   keep it private, and keep it stable across all function instances that must read the same session.
6. Leave Google OAuth variables unset for this demo deployment. See the Google limitation below.
7. Deploy the branch from the Vercel dashboard. Verify the deployment before sharing its URL.

The application reads these environment-variable names:

| Name | Requirement | Purpose |
|---|---|---|
| `SECRET_KEY` | Required | Signs Flask's session cookie; use a private, high-entropy value. |
| `ANTHROPIC_API_KEY` | Optional | Enables supported AI-assisted suggestions. The app uses its built-in guidance when absent. |
| `GOOGLE_CLIENT_ID` | Optional; OAuth only | Identifies the Google OAuth application. |
| `GOOGLE_CLIENT_SECRET` | Optional; OAuth only | Authenticates the Google OAuth application. |
| `GOOGLE_REDIRECT_URI` | Optional; OAuth only | Must exactly match the callback URL registered with Google. |

`SECRET_KEY` is the session-security variable. The Google variables are not required for the
fictional demo; with client ID or secret absent, the Google sign-in link returns to Pair and keeps
using sample data.

If Google OAuth is enabled in a future deployment, set `GOOGLE_REDIRECT_URI` to the exact HTTPS
callback for that deployment (ending in `/google/callback`) and add the same URL to the Google
OAuth client's authorized redirect URLs. The current Google access token is held in process memory.
Vercel may route later requests to a different or restarted function instance, so Google Health
connections are not reliable across instances. Do not enable Google OAuth on `pair-mvp` until Pair
uses a secure shared token store. The demo remains usable without Google credentials.

## State, privacy, and reset limits

- Pair changes are held in Flask's signed client-side session cookie. The same `SECRET_KEY` lets
  different Vercel instances read a session, so demo state does not depend on a writable function
  filesystem. CSV and JSON fixtures remain unchanged. Session updates travel with each request; they
  are portable between instances, though simultaneous edits from multiple tabs can overwrite one
  another.
- A signed cookie is tamper-evident, not encrypted. A browser owner can inspect its contents, and
  browser cookie size is limited. This session design is for fictional demonstrations only; do not
  enter real personal or health information. Production use requires encrypted server-side
  persistence, authentication, and authorization.
- Demo role switching only changes the sample workspace. It does not prove identity or grant real
  access. Sign-in screens, member invites, and password recovery are demonstration flows.
- To reset a member demonstration, open **Settings → Export or delete my data**, select the
  confirmation checkbox, and choose **Delete my demo data**. This removes saved changes in that
  browser session; the fictional sample records remain available. Open the welcome page and choose
  Jordan Reyes to start again.

## Post-deployment review

Manually review the welcome page, Jordan's Home, Check In, My Plan, Health (including Connected Data Sources),
Patterns, Appointments (including packet preparation and review), My Circle, Settings, and the coach,
healthcare, trusted-person, and administrator workspaces. Confirm that static assets load, a new
session starts with fictional data, and the configured production branch is `pair-ui-redesign`.
