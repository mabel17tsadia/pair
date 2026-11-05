# Pair

## What Pair does

Pair is a Flask prototype for the North American AI Challenge, created with First Place AZ in mind. It explores how neurodivergent young adults can build life skills, follow through on healthcare, and control what information they share.

Pair helps members notice how they are doing, understand relevant health and wellbeing information, and use that context to choose which activities to prioritize—one manageable step at a time.

Pair uses fictional data. It is not a medical device, an EHR, a diagnostic tool, or a production healthcare system.

## Demonstration workspaces

| Workspace | What reviewers can explore |
|---|---|
| Pair member | Jordan’s sample Home, private Check In, Health, My Plan, Patterns, Appointments, My Circle, and Settings. |
| Coach or educator | Learning progress, activity library, learner profiles, and sample assignments. |
| Healthcare professional | Member-shared appointment packets and proposed follow-up steps. |
| Trusted person | Member-shared summaries and encouragement choices. |
| Organization administrator | Sample account, invitation, consent, and organization-management views. |

Selecting a role opens a sample workspace; it does not sign in or grant real access.

## Key prototype features

- **Home:** brings together the member’s current context and a manageable next step.
- **Private Check In:** supports picture-based reflection; responses stay private by default.
- **Health:** helps the member review relevant information, prepare for appointments, and review care-team instructions.
- **My Plan:** uses the member’s choices and available context to help organize activities, which can be followed one step at a time.
- **Patterns and connected data sources:** shows one selected pattern at a time and manages optional sample sources.
- **Appointments:** supports appointment preparation, packet review, and member acceptance of proposed next steps.
- **My Circle:** lets the member choose what specific information to share and with whom; sharing is not automatic.
- **Staff demonstrations:** shows the boundaries of coach, healthcare professional, trusted-person, and administrator workspaces.

## Fictional data, privacy, and limitations

All identities and records are fictional. Demo role switching is not authentication. Packets, invitations, and messages are not delivered to real people or services. Do not enter real personal or health information. Pair is not HIPAA-compliant or production-ready.

See [Demonstration data](docs/demo-data.md) and [Roles and permissions](docs/roles-and-permissions.md) for more detail.

## AI use

**Development:** Pair was initially developed with Claude Opus 5.5 through Claude Code. Codex was later used to support UI refinement, testing, documentation, deployment preparation, and repository review. The team reviewed the generated work, tested the application, and made the final product decisions.

**In the app:** Selected optional features can use the Anthropic API. Built-in guidance is used when the API key is absent or a request fails, and the prototype remains usable without the key. Do not enter real personal or health information.

## Run locally

In Windows PowerShell:

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

Open <http://127.0.0.1:5000>. `ANTHROPIC_API_KEY` is optional; keep any key private and out of Git.

## Tests

```powershell
python -m unittest discover -s tests -q
```

**60 tests passed on 4 November 2026.** Rerun the command for the latest result.

## Deployment and project links

- **Current challenge prototype:** [Pair on Vercel](https://pair-mvp.vercel.app), using `pair-ui-redesign`.
- **Submission source:** [GitHub: mabel17tsadia/pair, branch `pair-ui-redesign`](https://github.com/mabel17tsadia/pair/tree/pair-ui-redesign).
- **Earlier prototype:** `main` and its Render deployment are intentionally preserved separately; the branches are not merged.

See [deployment notes](docs/deployment.md). The repository does not document a specific Render URL.

## Documentation

| Document | Description |
|---|---|
| [Product requirements](docs/product-requirements.md) | Product purpose and intended member experience. |
| [Roles and permissions](docs/roles-and-permissions.md) | Workspace boundaries and member-controlled sharing. |
| [Demonstration data](docs/demo-data.md) | Fictional sample records and data-provider notes. |
| [Design system](docs/ui-ux-design-system.md) | Visual and accessibility guidance. |
| [Master design prompt](docs/master-design-prompt.md) | Product and design direction; some requirements remain aspirational. |
| [Deployment notes](docs/deployment.md) | Local and hosting configuration. |
| [Early prompts](notes/prompts-log.md) | Available Pace-era development prompts, not a complete history. |
| [Early testing log](notes/testing-log.md) | Historical early API-key fallback test; not the current suite record. |

## Team and partner context

**Team:** G-Unit. **Challenge partner context:** First Place AZ.
