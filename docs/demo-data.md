# Pair Demonstration Data

Use fictional people and fictional records only. The target demo set below is a design requirement; it is not a description of the CSV files currently in `data/`. Do not copy real participant information into demo data.

## Target demo set

- Pair member: Jordan Reyes.
- Life coach: Dana Brooks.
- Healthcare professional: Dr. Priya Patel.
- Four Circle members with distinct relationships and explicit member-selected permissions.
- Three coach-assigned activities.
- Two member-created activities.
- Three healthcare follow-up actions, including a mix of proposed and member-reviewed states.
- Four private check-ins.
- Optional phone activity and sleep-pattern data.
- One upcoming appointment packet and one previous appointment.
- Activity steps, dates, sources, estimated time, statuses, and next actions.

All names, contact details, dates, health values, and activity histories must be invented for the demo. The four Circle members can include the named coach and professional; do not create additional real identities.

## Suggested record groups

| Record group | Useful fields |
|---|---|
| Member and role | Stable demo ID, fictional name, role, organization where relevant. |
| Circle permission | Member ID, invited-person ID, relationship, specific permission, start and expiration, active or revoked state. |
| Activity | ID, title, source, source person or organization, due date or scheduled time, estimated minutes, status, next action, optional accepted health follow-up link. |
| Activity step | Activity ID, order, short instruction, optional fictional image reference, original instruction reference. |
| Check-in | Member ID, fictional date, selected feeling, selected help choice, private visibility by default. |
| Connected source | Member ID, fictional source type, signals provided, consent state, connection state. |
| Appointment packet | Member ID, fictional appointment type/date, selected items with source labels, recipient, review state, access expiration, previous or upcoming state. |
| Healthcare next step | Packet ID, submitting professional, plain-language instruction, optional due date, supporting detail reference, proposed / question asked / accepted / declined status. |

These are logical fields to guide a later data model, not a mandate to add a database now. Keep the interface separate from the CSV-loading details so the demo source can later be replaced by an API or database without rebuilding the presentation layer.

## Current sample data

The repository has CSVs for people, signals, devices, vitals, check-ins, circle members, goals, and routines. The Jordan sample Circle includes four contacts, including Dana Brooks, Dr. Priya Patel, and Marisol Reyes. Maya and Theo appear only in staff learning views with sample learning-sharing permission. The JSON fixture contains Jordan's activities, Health follow-ups, four private check-ins, optional phone and sleep sources, an upcoming and a previous appointment packet, learning-only records for Maya and Theo, and fictional role-workspace summaries. Changes made in the browser remain session-only and do not persist to CSV or JSON files.

The Prompt 6 target records are in [`data/demo_records.json`](../data/demo_records.json). [`demo_data.py`](../demo_data.py) exposes them through a typed record contract and `DemoDataProvider`; the current JSON provider can be replaced by an API or database provider implementing the same `load()` interface. My Plan, Health, and activity detail read these records through that provider. Activity steps preserve their original instruction and learning objective alongside optional picture labels, shorter wording, alternate explanations, and examples. Other existing screens continue to use the original CSV-backed `data.py` functions. The JSON fixture is fictional, simulated demo content and is not connected to a real person or service.

### Session-only workflow state

The browser's Flask session, not the CSV or JSON fixture, temporarily holds member decisions and progress. This includes whether a proposed healthcare instruction was accepted or declined, selected recurrence and reminder time, daily occurrence completion, paused or in-progress activity state, and coach help requests. The fixture may define a baseline recurrence or acceptance status, but member changes do not rewrite it. These session values are not permanently stored and may disappear when the demo session is cleared.

## Privacy and demo behavior

Keep check-in notes private. Do not place real personal data or credentials in the repository. Clearly label simulated readings and prototype-only sharing. Never imply that a demo packet, activity, or sharing confirmation was delivered to a real person.
