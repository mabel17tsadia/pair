# Pair Product Requirements

## Purpose

Pair is an accessible independence companion for neurodivergent young adults. It supports life-skills learning and healthcare follow-through while helping each member choose what information is shared and with whom.

Pair is not an electronic health-record (EHR) system. It does not diagnose, make final medical decisions, or replace educators, life coaches, or healthcare professionals.

## Product principles

- Keep the member in control of their information, choices, and next steps.
- Make one manageable next action easy to find.
- Use plain language, progressive disclosure, and accessible interaction patterns.
- Keep check-ins private unless the member deliberately shares selected information.
- Make wearables and connected devices optional. Pair remains usable without them.
- Never share automatically or infer that a behavioral pattern proves a condition.
- Keep demo data fictional and clearly distinguish prototype behavior from production behavior.

## Member experience

The primary member navigation is Home, My Plan, Check In, Health, My Circle, and Me.

Members can choose the Ocean, Garden, or Twilight visual theme. Theme choice changes appearance only.

- **Home** offers a greeting, a recommended next action, a simple Now / Up Next / Later schedule, optional private pattern notice, appointment reminder when relevant, and links to continue an activity or check in.
- **My Plan** organizes educational, independent-living, personal, coach-assigned, and accepted healthcare follow-up activities. It supports time and source filters and shows each activity's source, due date or time, estimated time, status, and next action. Appointments themselves belong in Health.
- **Activity experience** presents one step at a time and supports picture and text preferences, read aloud, simpler explanations, examples, original instructions, breaks, help requests, and difficulty feedback. Presentation changes must preserve the educator's objective and required outcome.
- **Check In** offers labeled feelings and “What would help?” choices. A check-in is private unless the member chooses to share specific information.
- **Health** organizes appointment preparation, shared packets, accepted next steps, member-selected patterns, connected sources, and previous appointments. It uses additional permission checks and progressive disclosure.
- **My Circle** lets the member review, change, revoke, or time-limit each person's permissions.
- **Me** provides member-specific accessibility and privacy settings.

## Appointment and follow-up experience

Appointment preparation is a guided flow: appointment type and date; reason; member-selected changes or symptoms; questions; communication preferences; packet review; recipient and access-expiration selection. Nothing is shared before the member reviews and submits the packet. Each item identifies its source.

Healthcare professionals may propose a prescription pickup, laboratory test, referral, follow-up appointment, discharge instruction, or other healthcare action. Proposals identify who submitted them, provide plain-language instructions, may include a due date and supporting details, and let the member accept, ask a question, or decline. Only accepted actions enter My Plan.

## Connected information

Phone activity, screen activity, Apple Health, Android Health Connect or the existing Google Health integration, optional watches or rings, sleep sensors, glucose or blood-pressure devices, supported smart-home devices, and information entered by the member are possible sources. These are possibilities, not claims that every integration currently exists.

For each connected source, explain what Pair reads, why it is requested, where it appears, who may see it, whether it is connected, and how to disconnect it. Do not call an API or account connection Bluetooth unless it uses Bluetooth. Device connections are optional.

## Roles and access

The intended roles are Pair member, coach or educator, healthcare professional, trusted person, and organization administrator. Role-specific navigation does not itself grant access to member information. The member's explicit, specific permissions and the authorized time period control access. See [roles-and-permissions.md](roles-and-permissions.md).

## AI boundaries

AI may adapt presentation, break activities into steps, suggest appointment questions, summarize member-selected information, explain presentation changes, and allow correction of a personalization profile. It must not diagnose, make final medical decisions, silently change learning objectives, share automatically, hide original instructions, or treat patterns as proof of a condition.

## Demonstration and current implementation

Use fictional demonstration data only. The target demo data is described in [demo-data.md](demo-data.md). The current app is a Flask prototype with CSV and JSON sample data and session-only changes. It includes the member experience and five role-specific demonstration workspaces for Jordan, Dana, Dr. Priya Patel, Marisol, and Alex. Coach, professional, trusted-person, and administrator pages have separate navigation and sample actions with explicit information boundaries. The app does not implement durable accounts, production authorization, real packet or message delivery, or durable organization management. Sharing, encouragement, and administrator setting actions are demo-only; they do not deliver information or change a real organization.

The product-scope direction in this document supersedes the earlier statement that task lists and task planning are out of scope. Existing demo goals and routines remain distinct features and should not be removed as part of documentation work.

## Source of truth

Use [master-design-prompt.md](master-design-prompt.md) as the detailed UI/UX reference, [ui-ux-design-system.md](ui-ux-design-system.md) for presentation guidance, [roles-and-permissions.md](roles-and-permissions.md) for role boundaries, and [demo-walkthrough.md](demo-walkthrough.md) to distinguish current behavior from the intended experience.
