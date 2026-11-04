# Pair Roles and Permissions

Roles define which workspace and actions are available. A role alone never grants access to a member's content. Access must be specifically authorized, limited to the relevant information, and revocable by the member. Health packet access also follows its authorized time period.

## Roles

| Role | Intended workspace and actions | Information boundary |
|---|---|---|
| Pair member | Home, My Plan, Check In, Health, My Circle, and Me; controls activities, check-ins, packets, source connections, and sharing choices. | Own information. The member chooses what specific information to share and with whom. |
| Coach or educator | Overview, learners, an individual learner profile, Activity Library, and Coach Settings; may assign an activity only after opening a specific learner profile. | May see assigned activity status, help requests, learning preferences, helpful presentation formats, and difficulty feedback when authorized. Must not see private check-ins, medical records, raw health readings, appointment packets, or unrelated health details. |
| Healthcare professional | Shared Appointment Packets, Packet Detail, Communication Preferences, Proposed Next Steps, and Professional Settings. | Only packet content deliberately submitted by the member and only during the authorized period. May propose follow-up actions; does not automatically write to My Plan. |
| Trusted person | Member-authorized summaries, shared accomplishments, encouragement opportunities, and support requests selected by the member. | Only specific content authorized by the member. No continuous-monitoring or surveillance dashboard. |
| Organization administrator | Accounts, role verification, invitations, organization settings, consent records, access logs, and activity-template governance. | Administrative role does not grant access to private member content. Access logs and consent records must not become a route to unrelated health information. |

## Member-controlled permissions

For each invited person, the member can review, change, revoke, and time-limit permissions. Sharing is never automatic. A trusted person's relationship or an organization's role does not imply permission. Appointment packets require a final member review and explicit recipient selection before submission.

## Current prototype boundary

The existing app is a single-browser demo with demo-person selection, not account authentication. Its circle levels control sample previews and the coach demo; they do not establish real identities or secure external access. The `/share` and appointment send actions show confirmation text but do not transmit information. The coach view is built from sample data. These behaviors must not be described as production authorization or delivery.

## Access review questions for implementation

Before adding a role workflow, identify the authenticated person, the member whose information is involved, the exact permission granted, the content allowed, the expiration, and the revocation path. Deny access by default when any required authorization is missing.
