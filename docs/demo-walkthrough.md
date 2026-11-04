# Pair Demo Walkthrough

This walkthrough distinguishes what can be shown in the current local prototype from the intended product flows in [master-design-prompt.md](master-design-prompt.md). The prototype uses fictional CSV data and stores changes in the browser's Flask session. Its send actions do not deliver information.

## Current local demo

Start the app with `python app.py` and open <http://127.0.0.1:5000>.

1. **Choose a demo person.** The current sample people are Jordan, Maya, and Theo. Choose Jordan to see the existing sample profile and circle.
2. **Open Today.** Review the simulated week summary, paired-signal changes, any body signals or routine note, the gentle step, and climb card. Text generation may use AI when configured or the rule-based backup otherwise.
3. **Open Climb.** Review weekly goals, mark a manual goal done, or add a personal goal. Changes are session-only.
4. **Open Check In.** Select a mood and optionally enter a note. The response compares the choice with simulated patterns; the note remains private in the demo. The emergency-word flow is a prototype aid and not a replacement for emergency services.
5. **Open Circle.** Review sample circle levels, add or edit a member, and open Share to inspect the member-specific preview. The preview starts with no selections. Submitting it only displays a prototype confirmation; nothing is sent.
6. **Open Me.** Visit routines, patterns, body signals, paired-device controls, appointment preparation, and settings. Device readings are sample data. Google Health is an optional test integration and its returned readings are not used in pattern calculations.
7. **Open appointment preparation.** Review the generated or rule-based summary, add questions or manually entered items, and use browser print if desired. The send form only displays a prototype confirmation.

## Intended design walkthrough (future implementation)

The target member flow begins at Home with one recommended action and a Now / Up Next / Later schedule. The member opens My Plan, filters by time or source, and completes an activity one step at a time. They can request help or a break and give difficulty feedback. Check In remains private unless the member chooses to share specific details.

For healthcare, the member opens Health, prepares a packet through the guided steps, reviews every item and source, selects a recipient and expiration, then submits. A professional may propose a next step; the member accepts, asks a question, or declines. Only accepted actions appear in My Plan. Connected sources remain optional and expose clear consent, access, and disconnect details.

## Current prototype versus target

The target role workspaces, full My Plan, coach activity assignments, professional packet inbox, real packet delivery, accepted healthcare follow-up actions, and persistent accounts are not implemented in the current demo. Use this future flow to explain the design direction, not to claim working behavior.
