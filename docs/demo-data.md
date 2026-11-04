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

The repository currently has CSVs for people, signals, devices, vitals, check-ins, circle members, goals, and routines. They currently include Jordan, Maya, and Theo; the target four-circle-member and activity / appointment counts above are not all represented. Do not replace or rewrite the current CSVs as part of documentation work. Current session changes do not persist back to the CSVs.

The Prompt 6 target records are in [`data/demo_records.json`](../data/demo_records.json). [`demo_data.py`](../demo_data.py) exposes them through a typed record contract and `DemoDataProvider`; the current JSON provider can be replaced by an API or database provider implementing the same `load()` interface. My Plan, Health, and activity detail read these records through that provider. Activity steps preserve their original instruction and learning objective alongside optional picture labels, shorter wording, alternate explanations, and examples. Other existing screens continue to use the original CSV-backed `data.py` functions. The JSON fixture is fictional, simulated demo content and is not connected to a real person or service.

## Privacy and demo behavior

Keep check-in notes private. Do not place real personal data or credentials in the repository. Clearly label simulated readings and prototype-only sharing. Never imply that a demo packet, activity, or sharing confirmation was delivered to a real person.
