# Pair Demo Walkthrough

This walkthrough follows the current member experience in the local Flask prototype. It uses fictional CSV and JSON records and stores interactive changes in the browser's Flask session. Demo actions do not send information to real people or services.

Start the app with `python app.py` and open <http://127.0.0.1:5000>.

## Member walkthrough

Follow the member navigation in this order: **Home → Check In → My Plan → Health → Patterns → Appointments → My Circle**.

1. **Home.** Jordan's page shows “Good afternoon, Jordan,” one Check In button, three fictional health observations, and Your Day with Now and Up Next. The schedule stays visible regardless of My Pace. After a saved check-in, Home shows a compact Check-in complete card and Continue to My Plan.
2. **Check In.** Open Check In. The optional questions show picture-supported feelings, My Pace, “What would help?” and an optional note. The three support choices are Quiet Break, Message Someone, and Nothing Right Now. Choose a feeling and help option if useful; every question is optional.
3. **My Pace.** Choose one of the four My Pace values: One small step, A few things feel manageable, I need a pause, or Not sure. For this walkthrough, choose One small step. Choose Nothing Right Now if you want the standard saved confirmation without leaving the Check In page. Save check-in answers remain private in collapsed history.
4. **Continue to My Plan.** The confirmation says “Thank you for checking in.” Select Continue to My Plan. My Plan shows one incomplete activity at a time. The status message links back to Check In if the member wants to change My Pace.
5. **Complete an activity.** Open the activity. For a learning activity, follow one instruction at a time and select Finish activity on its last step. A recurring Health activity can be marked Done without first selecting Start. The activity flow returns to My Plan.
6. **See the next activity.** In one-at-a-time mode, My Plan selects the next incomplete activity automatically. When no matching activities remain, it says “You completed everything in this view.” The When and From dropdowns can change the date range and source without changing the saved My Pace choice.
7. **Review accepted health activities.** Open Health and review the compact care-team instruction list or select Review instructions. Proposed instructions remain in Health until Jordan accepts them. Acceptance requires choosing a date, recurrence where applicable, and an optional reminder time; an accepted action then appears in My Plan with its source and schedule. Declined or unanswered proposals stay out of My Plan. Home and My Plan show an in-app demonstration reminder after the chosen time when the page is loaded; no push, text, or email is sent.
8. **Health Patterns.** Select Patterns. Choose one labeled pictogram tile on desktop or the pattern dropdown on mobile. Only the selected pattern's summary, source, comparison, chart, and explanation are expanded.
9. **Appointment preparation.** Select Appointments and begin preparation. Enter the visit reason, optionally open “Not sure? See common reasons for this type of visit,” and select or ignore sourced discussion topics. Continue through member-selected information, accommodations and communication preferences, and editable appointment questions. Review the packet, choose the recipient and expiration, and submit only if Jordan approves. The prototype does not deliver a real packet.
10. **My Circle.** Review each relationship's member-selected permissions. The Message Someone path opens “Who would you like to message?”, lets Jordan choose an existing Circle member, and provides a draft field. Send only records a demo action; it does not launch an external messaging service or deliver a real message.

## Other role demonstrations

Demo switching opens sample coach, healthcare-professional, trusted-person, and organization-administrator workspaces. It does not authenticate anyone or grant production access. Coaches see learning information and assignments, professionals see currently authorized packet contents and proposals, trusted people see only the sample shared summary, and administrators see organization metadata without member content.

## Current prototype versus future behavior

Account identity, production authorization, real message or packet delivery, durable organization management, push/text/email notifications, and production device integrations are not implemented. Session-only changes and fictional fixture records must not be presented as production behavior.
