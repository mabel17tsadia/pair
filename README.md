# Pair

Pair is a Flask demonstration application for the North American AI Challenge, created with First Place AZ in mind. It explores how neurodivergent young adults can learn life skills, follow through on healthcare, and stay in control of what information they choose to share.

Pair uses fictional demonstration data. It does not diagnose, is not a medical device, is not an EHR, and is not ready for real health information. It is a prototype, not a production healthcare system.

## Current prototype

The landing page opens five sample workspaces. Choosing a role previews that workspace; it does not sign in or grant real access.

| Workspace | Demonstration experience |
|---|---|
| Pair member | Home, private Check In, My Plan, Health, Patterns, Connected Data Sources, My Circle, appointment preparation, and member settings. |
| Coach or educator | Learners, learner details, a reusable Activity Library, assignment from a learner profile, and coach settings. The sample view contains learning information, not private check-ins or health records. |
| Healthcare professional | Member-shared appointment packets, packet detail, proposed next steps, and professional settings. The view is limited to the submitted sample packet. |
| Trusted person | Member-shared summaries and encouragement options. |
| Organization administrator | Sample people and roles, invitations, consent and audit records, activity-template governance, and organization settings; no member health content. |

In the member workspace, activities can be filtered by date and source and shown one step at a time. Check In supports optional answers and keeps the saved response private in the member's demo session. Health brings together appointment preparation, shared-packet review, care instructions and accepted actions. Patterns and connected sources use progressive disclosure. Circle permissions and packet sharing are demonstrations: nothing is delivered to a real person or service.

The coach must open a learner profile before assigning an activity. Healthcare professionals can propose next steps; only member-accepted actions enter the sample plan. These workflows illustrate boundaries but do not provide production authorization.

## Demonstration identities and data

All people, health values, appointments, activities, and records are fictional. Jordan Reyes is the primary member demonstration identity. Maya Chen and Theo Okafor appear as sample learners in staff workspaces. CSV files and `data/demo_records.json` are local fixtures; changes made during a demo are stored in Flask's session, not written back to those fixtures.

See [Demonstration data](docs/demo-data.md) for the data model and fictional-record notes.

## Technology

- Python, Flask, and Jinja templates.
- HTML, plain CSS, and small plain JavaScript files served from `public/`.
- Fictional CSV and JSON data.
- Anthropic API for optional in-app AI suggestions when `ANTHROPIC_API_KEY` is configured.
- Optional Google Health OAuth integration. It is not required for the demo and is not reliable across serverless instances because its token is kept in process memory.
- Python's built-in `unittest` framework for automated tests. `pytest` is not a project dependency.

## AI use

### In the application

The app calls the Anthropic API only when an optional API key is configured. Current user-facing calls are:

- Appointment-question suggestions use the first name, visit type, pattern-change sentences, body-signal summaries, and check-in mood counts.
- “Not sure who to see?” uses the first name, up to 500 characters the member enters, and pattern and body-signal summaries. A rule-based urgent-language check runs before this call.
- The legacy routine editor can request steps using only the routine name.

The appointment flow labels suggestions as “Adapted with AI” or “Using built-in guidance”; the professional suggestion flow labels its source. When no key is configured or a request fails, the question flow uses fixed questions for that visit type, the professional flow suggests primary care, and routine step suggestions return an empty list for the member to fill in. Pair remains usable without an Anthropic key.

These features do not diagnose or make clinical decisions. Because the appointment suggestions may send member-entered or health-related context to an external API, do not enter real personal or health information in this prototype.

### During development

Pair was initially developed with Claude Opus 5.5 through Claude Code. Codex was later used to support UI refinement, testing, documentation, deployment preparation, and repository review. The team reviewed the generated work, tested the application, and made the final product decisions.

`notes/prompts-log.md` contains available early development prompts; it is not a complete prompt history. A separate curated AI Prompts PDF is being prepared for the challenge submission.

## Privacy and security limits

- Use fictional data only; do not enter real health information.
- `SECRET_KEY` and optional API credentials are supplied through environment variables or a local ignored `.env`; they must not be committed.
- Demo changes are held in Flask's signed client-side session cookie. The signature helps detect tampering, but the cookie is not encrypted and its contents are readable by the browser owner.
- The prototype has no production identity, authentication, or authorization system. Switching roles is a workspace preview only.
- Connected integrations are optional. Google OAuth tokens are kept in process memory and do not reliably survive restarts or move between serverless instances.
- Appointment packets, invitations, messages, and sharing confirmations are not delivered externally.

Pair is not represented as HIPAA compliant or production secure. Production use would require, among other things, verified identity and authorization, protected server-side storage, and reviewed external integrations.

## Local setup (Windows PowerShell)

From the folder where you want the project:

```powershell
git clone https://github.com/mabel17tsadia/pair.git
cd pair
git switch pair-ui-redesign
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(32))")
python app.py
```

Open <http://127.0.0.1:5000>. The `SECRET_KEY` command creates a temporary key for the current PowerShell session. A local ignored `.env` can be used instead if the key should persist between sessions. Do not share or commit either value.

AI is optional. To try it locally, add `ANTHROPIC_API_KEY=<your-private-key>` to the ignored `.env` before starting the app. Keep the actual key private. Without it, built-in guidance is used.

Google Health OAuth is also optional and requires separately configured Google credentials and a matching callback URL. Leave it unconfigured for the fictional demo.

## Tests

Run the repository's test suite with:

```powershell
python -m unittest discover -s tests -q
```

**60 tests passed on 4 November 2026.** Rerun the command for the current result. The tests cover the member and staff workflows, role boundaries, activity and health flows, and responsive/accessibility contracts.

## Deployment versions

- **Current challenge submission:** `pair-ui-redesign`, deployed as [Pair on Vercel](https://pair-mvp.vercel.app).
- **Submission source:** [mabel17tsadia/pair on `pair-ui-redesign`](https://github.com/mabel17tsadia/pair/tree/pair-ui-redesign).
- **Earlier prototype:** `main` remains separate and is the branch associated with the earlier Render deployment. The separation preserves that version; this submission does not change it.

See [Deployment notes](docs/deployment.md) for environment variables and hosting details. No Render URL is included because the repository does not document a specific service URL.

## Documentation

| Document | What it covers |
|---|---|
| [Product requirements](docs/product-requirements.md) | Current product purpose, principles, and the intended member experience. |
| [Roles and permissions](docs/roles-and-permissions.md) | Intended workspace boundaries and member-controlled sharing. |
| [Demonstration data](docs/demo-data.md) | Fictional fixture contents and data-provider structure. |
| [UI/UX design system](docs/ui-ux-design-system.md) | Shared visual and accessibility guidance. |
| [Master design prompt](docs/master-design-prompt.md) | Detailed product and design direction; not every requirement is implemented in the prototype. |
| [Deployment notes](docs/deployment.md) | Local, Vercel, and Render configuration and prototype limitations. |
| [Early prompt log](notes/prompts-log.md) | Historical Pace-era prompts available in the repository; not the full Pair prompt record. |
| [Early testing log](notes/testing-log.md) | Historical note about an early AI fallback test, not the current automated suite. |

## Team and partner context

The challenge team is G-Unit. Pair was created with First Place AZ in mind. First Place AZ research findings and individual team contributions are not documented in the repository; add only findings and attributions confirmed by the team.
