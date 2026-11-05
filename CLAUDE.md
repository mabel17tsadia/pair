> Historical development note: This file contains the original instructions used when the prototype was called Pace and focused primarily on pattern detection. Pair later expanded into role-specific workspaces, healthcare follow-through, member-controlled sharing, and My Plan. Current product scope is defined in `docs/product-requirements.md`.

## Historical project description

Name: Pair. A web app for the North American AI Challenge, built with our challenge partner First Place AZ in mind.
Pair connects, with consent, to devices a person already uses (phone first; optional smart washer, mattress sensor or smart ring), learns the person's own usual patterns, notices when several patterns change together, tells the person first in plain language, and lets them choose what each trust circle member can see.
All device data is simulated from CSV files. Pair does not diagnose and is not a task planner.
Out of scope: task lists, adding tasks, inbox, wearables being required, medical devices like pacemakers.

For current product purpose and scope, see [docs/product-requirements.md](docs/product-requirements.md). The statements above record the original Pace-era project description and are not current Pair product requirements.

# Rules for this project

The team must be able to read and explain every line in a code review.

1. Keep code short and simple. Prefer fewer lines over clever code.
2. No new libraries or packages without asking first and explaining why.
3. Build ONE screen or feature at a time. Stop and summarize when done.
4. Add a short plain-English comment above each function and each
   section of a template explaining what it does.
5. Use Python with Flask, HTML templates, plain CSS with theme variables,
   and only small plain JavaScript for buttons. No frontend frameworks.
6. Never put API keys or real personal data in code or commits.
   Keys live in .env only.
7. After each step, list the files you changed and how to test them.
8. If something is unclear, ask before guessing.
