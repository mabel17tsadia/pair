# Pair Roles and Permissions

Roles define which workspace and actions are available. A role alone never grants access to a member's content. Access must be specifically authorized, limited to the relevant information, and revocable by the member. Health packet access also follows its authorized time period.

## Roles

| Role | Intended workspace and actions | Information boundary |
|---|---|---|
| Pair member | Home, Check In, My Plan, Health, Patterns, Appointments, My Circle, and Settings; controls activities, check-ins, packets, source connections, and sharing choices. | Own information. The member chooses what specific information to share and with whom. |
| Coach or educator | Overview, learners, an individual learner profile, Activity Library, and Coach Settings; may create or assign learning activities only within the coach workspace and after opening a specific learner profile. | May see assigned activity status, help requests, learning preferences, helpful presentation formats, and difficulty feedback when authorized. Must not see private check-ins, medical records, raw health readings, appointment packets, or unrelated health details. |
| Healthcare professional | Shared Appointment Packets, Packet Detail, Communication Preferences, Proposed Next Steps, and Professional Settings. | Only packet content deliberately submitted by the member and only during the authorized period. May propose care-team instructions. Each proposal stays in Health until the member reviews and accepts or declines it. Proposed instructions do not enter My Plan automatically; only accepted instructions become My Plan activities. |
| Trusted person | Member-authorized summaries, shared accomplishments, encouragement opportunities, and support requests selected by the member. | Only specific content authorized by the member. No continuous-monitoring or surveillance dashboard. |
| Organization administrator | Accounts, role verification, invitations, organization settings, consent records, access logs, and activity-template governance. | Administrative role does not grant access to private member content. Access logs and consent records must not become a route to unrelated health information. |

## Member-controlled permissions

For each invited person, the member can review, change, revoke, and time-limit permissions. Sharing is never automatic. A trusted person's relationship or an organization's role does not imply permission. Appointment packets require a final member review and explicit recipient selection before submission. Message Someone opens a member-selected existing Circle relationship and drafts a prototype message; no external message is delivered.

## Current prototype boundary

The app offers five fictional, role-specific demonstration workspaces. The role selector changes the sample workspace and server routes redirect requests to other roles' demo pages. This is presentation behavior only: it does not authenticate a person, verify employment, establish consent, or provide production authorization. Session changes and invitations are temporary. Share, encouragement, packet, and administration actions do not send messages or manage a real organization. Due activities can display an in-app reminder when the member loads Home or My Plan; the prototype does not send push notifications, texts, or emails.

The coach workspace is limited to fictional learners whose sample Circle data enables learning sharing. It displays learning activities, progress, preferences, and learning requests; private Check Ins, health patterns, raw device readings, appointment packets, and Circle information are excluded. The healthcare workspace displays only the currently authorized sample packet fields, its authorization window, and associated proposed actions. The trusted-person workspace shows a fixed fictional summary explicitly marked as shared by Jordan; encouragement is stored only in the demo session. The administrator workspace contains fictional account, role, invitation, consent, audit, and template metadata, not member content.

Member Health screens are scoped to the active member's own sample profile. Professional packet detail checks recipient, member-reviewed state, and current authorization dates before showing selected fields. These checks protect the demo's record boundaries; they are not production authentication or recipient authorization.

## Access review questions for implementation

Before adding a role workflow, identify the authenticated person, the member whose information is involved, the exact permission granted, the content allowed, the expiration, and the revocation path. Deny access by default when any required authorization is missing.
