# Pair Demo Walkthrough

This walkthrough distinguishes what can be shown in the current local prototype from the intended product flows in [master-design-prompt.md](master-design-prompt.md). The prototype uses fictional CSV data and stores changes in the browser's Flask session. Its send actions do not deliver information.

## Current local demo

Start the app with `python app.py` and open <http://127.0.0.1:5000>.

1. **Explore the five workspaces.** Jordan is the member demo; Dana is the coach; Dr. Priya Patel is the healthcare professional; Marisol is the trusted person; Alex is the organization administrator. Demo switching does not authenticate anyone or grant access to real information.
2. **Review Jordan's Home.** Find one next action, Today / Up next / Later summaries, personal My Climb progress, a short private pattern notice, appointment reminder, last Check In, and Circle link. Detailed patterns remain in Health.
3. **Explore Coach Overview.** Jordan, Maya, and Theo appear only with sample learning sharing enabled. Review activities, completion, learning preferences, and help or adaptation requests. Open a learner profile before assigning an activity. Health details and private Check Ins are not shown.
4. **Explore the professional workspace.** Review the new appointment packet inbox, open the active packet to see the selected information and authorization window, and review proposed next steps. Professional access does not include other account information.
5. **Explore the trusted-person workspace.** Marisol sees only Jordan's fictional weekly summary for its displayed period. Encouragement is saved only in this browser session and is not delivered.
6. **Explore organization administration.** Alex can review sample account and role status, invitation metadata, consent and audit metadata, approved activity-template governance, and session-only settings. The admin workspace does not show member content.
7. **Continue to inspect member features.** Check In remains picture-supported and private by default. My Plan, My Climb, Circle, Health, patterns, connected sources, appointment preparation, and settings remain available. Google Health is an optional test integration.

## Intended design walkthrough (future implementation)

The target member flow begins at Home with one recommended action and a Now / Up Next / Later schedule. The member opens My Plan, filters by time or source, and completes an activity one step at a time. They can request help or a break and give difficulty feedback. Check In remains private unless the member chooses to share specific details.

For healthcare, the member opens Health, prepares a packet through the guided steps, reviews every item and source, selects a recipient and expiration, then submits. A professional may propose a next step; the member accepts, asks a question, or declines. Only accepted actions appear in My Plan. Connected sources remain optional and expose clear consent, access, and disconnect details.

## Current prototype versus target

The role pages, coach assignments, packet review, member acceptance of follow-up steps, and organization metadata pages are available as demonstration workflows. Account identity, production authorization, external invitation or message delivery, real packet sharing, durable organization management, and production integrations remain unimplemented. Session-only changes and fictional fixture records must not be presented as production behavior.
