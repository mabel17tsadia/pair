# Pair Master UI/UX Design Requirements

**Intended product direction:** This document records detailed design goals. The current application code and tests establish which parts are implemented; this document does not establish current behavior by itself.

In the sections below, **Implemented now** describes behavior verified in the Flask prototype. **Future / production direction** describes goals that are not available as production services. Demo-session state and sample integrations are not durable or production behavior.

## Product purpose

Pair is an accessible independence companion for neurodivergent young adults. It helps members:

- Complete educational and independent-living activities.
- Understand one manageable next step at a time.
- Check in with themselves.
- Prepare for healthcare appointments.
- Understand and complete follow-up actions.
- Choose what information is shared and with whom.

Pair is not an electronic health-record system, does not diagnose conditions and does not replace educators, life coaches or healthcare professionals.

## Design principles

Use progressive disclosure. Show one clear primary action first and allow the member to open additional information when needed.

Use:

- Plain language.
- Short sections.
- Clear headings.
- Generous spacing.
- Large interaction targets.
- Rounded cards.
- Visible keyboard focus.
- Sufficient color contrast.
- Responsive desktop and mobile layouts.
- Pictures with text labels where useful.
- Reduced-motion support.

Avoid:

- Crowded dashboards.
- Long blocks of text.
- Unnecessary animation.
- Medical or technical jargon.
- Unexplained AI recommendations.
- Assuming one visual style works for every neurodivergent person.
- Automatic sharing.
- Making wearables mandatory.

## Visual themes

Provide three member-selectable themes:

1. Ocean: blue-green with warm gold accents.
2. Garden: soft green with clay or warm brown accents.
3. Twilight: accessible dark blue with soft blue and violet accents.

Theme selection changes appearance, not access or functionality.

## Roles

Support these roles:

- Pair member.
- Coach or educator.
- Healthcare professional.
- Trusted person.
- Organization administrator.

A role determines available navigation and actions. A role alone must not automatically grant access to a member’s information.

## Pair-member navigation

Use this intended primary navigation:

- Home.
- Check In.
- My Plan.
- Health.
- Patterns.
- Appointments.
- My Circle.
- Settings.

## Home

**Implemented now:** The member's Home page has a short greeting and one Check In button. It shows fictional health observations, a basic Now / Up Next schedule that is independent of My Pace, and a compact Check-in complete card after saving. When the member visits after a scheduled activity's time, Home may show an in-app demonstration reminder. It does not send push, text, or email notifications.

The primary action opens Check In. Continue to My Plan is a secondary link after a check-in. Do not add a second prompt asking the member to choose a pace on Home.

## My Plan

**Implemented now:** My Plan is the member's place to follow through on activities added by the member, assigned by a coach or educator, accepted healthcare instructions, and appointment-preparation activities. Proposed healthcare instructions stay in Health until accepted; declined or unanswered proposals do not enter My Plan. Appointments themselves remain in Health and Appointments.

The two side-by-side dropdowns are **When** (Today, Tomorrow, This Week, Later) and **From** (All, Added by Me, From My Coach, From Health). Defaults are Today and All. A message links back to Check In to change My Pace; the choice is not repeated in My Plan.

Use the latest check-in for the member's display:

- **One small step:** show the first incomplete activity.
- **A few things feel manageable:** show up to three activities.
- **I need a pause:** initially show no activity; Return when ready reveals one activity.
- **Not sure:** show one incomplete activity.
- **No check-in today:** show all activities matching Today and All.

After a one-at-a-time activity is completed, return to My Plan and show the next incomplete activity. If none remain in the view, say “You completed everything in this view.” Keep Home's basic Now / Up Next schedule visible regardless of My Pace.

Every activity should retain its title, source, scheduled date/time, estimate, status, and next action. Use Start, Pause, and Done for applicable recurring health activities; Done may be used without Start. Store daily completion by occurrence so a repeated submission does not count twice. Generate the next occurrence only on its scheduled date. The walk's displayed duration is approximately 15 minutes. Accepted instructions with a defined period, such as seven days of sleep recording, stop when that period ends.

**Future / production direction:** Durable schedules, background delivery, and external notification integrations are not part of this Flask demo. The prototype checks for due in-app reminders when Home or My Plan is rendered.

## Activity experience

**Implemented now:** Coach-assigned learning activities display one step at a time. The activity screen supports picture prompts, step choices, Previous / Next, Show fewer words, Show an example, Explain differently, View the original, and Easy / Okay / Difficult feedback on the final step. I need a break pauses learning and returns to My Plan. I need help is available only for a coach-assigned activity with an identified coach; its confirmation makes clear that no real message is delivered. Read Aloud is shown only when enabled in Settings and meaningful text is present.

Pictures and Words is the default presentation. Settings also offers Words Only and Pictures First. A presentation change must preserve the educator's objective and required outcome. A Quiet Break is an exception: it is an immediate, timer-free support screen with one instruction, optional Read Aloud, Done, and a return link. It is not a multi-step lesson and Check In does not create a plan activity for it.

**Future direction:** Any additional adaptation control should appear only when it has a working outcome and a visible way to return to the original instruction.

## Check In

**Implemented now:** The page begins with optional picture-supported feeling choices, followed by **My Pace — How manageable does today feel right now?** and an optional note. The only “What would help?” choices are Quiet Break, Message Someone, and Nothing Right Now. Smaller Step is not offered because My Pace controls the number of activities in My Plan; Read Aloud and screen display options are available in their relevant activity or Settings contexts.

Each question is optional. When the member chooses Nothing Right Now or no support option, Save shows only “Thank you for checking in,” Continue to My Plan, and Change my choice. Quiet Break and Message Someone instead open their selected destination directly. Complete answers remain in collapsed private history. Home's Check-in complete card does not repeat answers. Display preferences do not appear on this page.

The My Pace mapping is documented in My Plan above. “Nothing Right Now” saves without creating an activity. Quiet Break opens the simplified screen and Done returns to My Plan. Message Someone opens My Circle, asks the member to select an existing Circle relationship, and offers a message field. The prototype sends no external message.

Check-ins remain private unless the member deliberately shares specific information. A generic reminder preview is not a real system notification.

## Health

Health contains:

- Health overview.
- Prepare for an Appointment.
- My Shared Packets.
- Next Steps.
- Member-selected health patterns.
- Connected Health Sources.
- Previous appointments.

Health information must use additional permission checks and progressive disclosure.

### Health Patterns

**Implemented now:** Show one selected pattern at a time with a pictogram and text label, plain-language summary, source, comparison with the member's usual range, chart, explanation, and available actions. Desktop uses selectable tiles; mobile uses a native select. Keep the complete responsive chart visible without a nested scrolling container; retain labels, point markers, the usual-range band, and the recent-days highlight.

## Appointment preparation

**Implemented now:** The guided flow asks about appointment type/date and reason, presents member-selected pattern or check-in items one at a time, asks about communication and accommodations, collects questions, and provides a final packet review before recipient and expiration are selected. Nothing is shared before member review and submission.

The reason field is “What would you like to talk about at this visit?” The optional “Not sure?” link reveals common topics for the selected professional type. Suggestions are sourced from profession-scope guidance, labeled AI-assisted or built-in, and may be selected, edited in the member's note, or ignored. They are general discussion examples, not diagnoses, treatment advice, or a direction to see a particular professional. Question suggestions are separately labeled Adapted with AI or Using built-in guidance and remain editable.

**Future / production direction:** Real packet delivery and live clinician communication are not implemented by these demonstration flows.

## Healthcare follow-up

A healthcare professional may propose:

- Prescription pickup.
- Laboratory test.
- Referral.
- Follow-up appointment.
- Discharge instruction.
- Other healthcare action.

Every proposed next step must include:

- Who submitted it.
- Plain-language instructions.
- Optional due date.
- Supporting details or original document.

The member can review a proposal in Health and choose Accept, Ask a Question, or Decline. Acceptance asks for the date, recurrence where applicable, and optional reminder time. Sleep recording runs daily for seven days with an editable suggested evening reminder. For blood-pressure recording, the member selects the reminder frequency because the sample care-team instruction specifies none; Pair does not invent a medically required frequency. A separate “Bring blood-pressure readings to your next visit” preparation activity is scheduled before the confirmed visit. The daily walking activity keeps its approximately 15-minute source record, supports Start / Pause / Done, and counts at most once per day.

Only accepted instructions create My Plan activities. Source instruction, professional, acceptance state, schedule, occurrence completion, and paused state are shown or stored in the Flask session for this demo. An in-app demonstration reminder appears when Home or My Plan is rendered at or after the scheduled time. No push, text, or email notification is sent.

## Connected Data Sources

Preserve existing paired-device and Google Health functionality.

Rename or organize Paired Devices as Connected Data Sources because not every source uses Bluetooth.

Potential sources include:

- Phone activity.
- Screen activity.
- Apple Health.
- Android Health Connect or existing Google Health integration.
- Optional watch or ring.
- Sleep sensor.
- Glucose or blood-pressure device.
- Supported smart-home device.
- Information entered manually by the member.

Pair must remain usable when no device or external source is connected.

For every connected source, show:

- What Pair reads.
- Why Pair requests it.
- Where the information appears.
- Who may see it.
- Whether it is connected.
- How to disconnect it.

Do not describe an API or account integration as a Bluetooth connection unless Bluetooth is actually used.

## Coach or educator experience

**Implemented now:** Coach Overview, Learners, learner profiles, Activity Library, and Coach Settings use the coach workspace. Reusable activities are created in the library; open a learner profile before assigning. A coach may review learning activity progress and member-submitted help requests but not private check-ins or Health information.

Provide:

- Overview.
- Learners.
- Individual learner profile.
- Activity Library.
- Coach Settings.

The Activity Library contains reusable activity templates.

A coach must open a specific learner’s profile before assigning an activity to that learner.

The learner profile may show:

- Assigned activities.
- Activity completion.
- Help requests.
- Learning preferences.
- Presentation formats that helped.
- Feedback about activity difficulty.

The coach must not see:

- Private check-ins.
- Medical records.
- Raw health readings.
- Appointment packets.
- Unrelated health information.

## Healthcare-professional experience

**Implemented now:** The professional workspace lists member-shared appointment packets within their demo authorization period and lets the professional propose next steps associated with an authorized packet. The inbox uses “New appointment packets” and explains that they are shared by members and awaiting review. Only submitted packet content is shown.

Provide:

- Shared Appointment Packets.
- Packet Detail.
- Communication Preferences.
- Proposed Next Steps.
- Professional Settings.

Replace “New packets” with:

“New appointment packets”

Supporting text:

“Shared by members and awaiting your review.”

The professional sees only the content deliberately included in the submitted packet and only for the authorized period.

**Future / production direction:** Professional identity verification, durable authorization, and real clinical record exchange are not implemented.

## My Circle

Allow the member to invite:

- Coach or educator.
- Healthcare professional.
- Family member.
- Friend or trusted person.

The member chooses exact permissions for every person. **Implemented now:** Message Someone asks the member to select an existing Circle relationship and compose a session-only demo message; it does not open WhatsApp or send an external message.

Allow permissions to be:

- Reviewed.
- Changed.
- Revoked.
- Time limited.

Do not share information automatically.

## Trusted-person experience

The trusted-person view may show:

- Member-authorized summaries.
- Shared accomplishments.
- Encouragement opportunities.
- Support requests selected by the member.

It must not become a continuous-monitoring or surveillance dashboard.

## Administrator experience

Administrators may manage:

- Accounts.
- Role verification.
- Invitations.
- Organization settings.
- Consent records.
- Access logs.
- Activity-template governance.

Administrator status must not automatically provide access to private member content.

## Settings

**Implemented now:** Member settings include theme, comfortable or compact density, Pictures and Words / Words Only / Pictures First, Read Aloud enablement, speech rate, notification-preview privacy, celebration motion, source and Circle links, personalization review, data export, and deletion of demo-session changes. Pictures and Words is the default activity presentation. The system reduced-motion preference is respected. Biometric sign-in is not available in this prototype.

**Future direction:** Adjustable text-size controls and biometric sign-in may be considered for a future product. Settings shown in the prototype do not make its demo data durable or create external notification delivery.

Coach, healthcare, trusted-person and administrator settings should contain only controls relevant to those roles.

## AI requirements

AI should:

- Adapt presentation.
- Break large activities into steps.
- Suggest questions for appointments.
- Summarize member-selected information.
- Explain why a presentation was changed.
- Allow the member to correct the personalization profile.

AI must not:

- Diagnose.
- Make final medical decisions.
- Change an educator’s learning objective without approval.
- Share information automatically.
- Hide the original instruction or document.
- Treat a behavioral pattern as proof of a condition.

## Demonstration data

Use fictional demonstration data only.

Include:

- Jordan Reyes as the Pair member.
- Dana Brooks as life coach.
- Dr. Priya Patel as healthcare professional.
- Four Circle members.
- Three coach-assigned activities.
- Two member-created activities.
- Three healthcare follow-up actions.
- Activity steps, dates, sources and statuses.
- Four private check-ins.
- Optional phone and sleep-pattern data.
- One upcoming appointment packet.
- One previous appointment.

Structure demonstration data so it can later be replaced by a database or API without rewriting the interface.

## Implementation rule

For every remaining coding prompt:

1. Read this document first.
2. Preserve existing working functionality.
3. Modify only the files needed for that stage.
4. Do not expose credentials or real personal information.
5. Run relevant tests.
6. Show the changed files and explain the result.
7. Report incomplete behavior or conflicts.
8. Do not push directly to `main`.
9. Do not begin the next implementation stage until the current stage has been reviewed.
