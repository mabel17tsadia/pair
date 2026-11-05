# Pair Master UI/UX Design Requirements

**Intended product direction:** This document records detailed design goals. The current application code and tests establish which parts are implemented; this document does not establish current behavior by itself.

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
- Health.
- My Plan.
- Patterns.
- Appointments.
- My Circle.
- Settings.

## Home

The member’s Home page should show:

- A short greeting.
- One recommended next action.
- A simple Now, Up Next and Later schedule.
- An optional private pattern notice.
- An upcoming appointment reminder when relevant.
- Clear links to continue an activity or check in.

Do not overload the Home page with every available feature.

## My Plan

My Plan supports the member after reflection and relevant health context. It helps the member choose and follow manageable activities; it does not lead the product experience or make medical decisions.

My Plan contains:

- Educational activities.
- Independent-living activities.
- Personal activities added by the member.
- Activities assigned by a coach or educator.
- Accepted healthcare follow-up actions.

Provide time filters:

- Today.
- Tomorrow.
- This Week.
- Later.
- Completed.

Provide source filters:

- All.
- Added by Me.
- From My Coach.
- From Health.

Every activity card should display:

- Activity title.
- Source.
- Due date or scheduled time.
- Estimated time.
- Completion status.
- The next action.

Appointment preparation, packets, and follow-through belong in Appointments. Health provides the broader health overview and relevant records. Accepted follow-up actions may appear in both Health and My Plan.

## Activity experience

Display one activity step at a time by default.

Support:

- Pictures and words.
- Words only.
- Pictures first.
- Read aloud.
- Show fewer words.
- Show an example.
- Explain differently.
- View the original instruction.
- I Need a Break.
- I Need Help.
- Easy, Okay or Difficult feedback.

AI may change how an activity is presented, but it must not silently change the educator’s learning objective or required outcome.

## Check In

Use pictures or clear icons together with text labels.

Feelings may include:

- Calm.
- Okay.
- Tired.
- Worried.
- Overwhelmed.
- Another feeling.

“What would help?” choices should include:

- Take a quiet break.
- Show me a smaller step.
- Message someone I trust.
- Read this aloud.
- Reduce what is on the screen.
- Nothing right now.

Check-ins remain private unless the member deliberately shares specific information.

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

## Appointment preparation

Use a guided process:

1. Appointment type and date.
2. Reason for the visit.
3. Member-selected changes or symptoms.
4. Questions the member wants to ask.
5. Communication preferences.
6. Final packet review.
7. Recipient and access-expiration selection.

Nothing is shared before the member reviews and submits the packet.

Every included item should identify its source, such as:

- Entered by the member.
- From a private check-in.
- From phone activity.
- From a connected health source.

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

The member must be able to:

- Accept.
- Ask a Question.
- Decline.

Only accepted actions enter the member’s plan.

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

## My Circle

Allow the member to invite:

- Coach or educator.
- Healthcare professional.
- Family member.
- Friend or trusted person.

The member chooses exact permissions for every person.

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

Member settings should include:

- Theme.
- Text size.
- Information density.
- Pictures-and-words preference.
- Read-aloud controls.
- Reduced motion.
- Celebration style.
- Connected Data Sources.
- My Circle permissions.
- AI personalization profile.
- Face ID or device biometrics.
- Data download.
- Account deletion.

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
