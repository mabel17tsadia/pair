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

The current member navigation order is Home, Check In, Health, My Plan, Patterns, Appointments, My Circle, and Settings.

Members can choose the Ocean, Garden, or Twilight visual theme. Theme choice changes appearance only.

- **Home** brings together the member's current context, a private check-in prompt when needed, fictional health observations, and a manageable next step. The schedule can show Now and Up Next or the full day when the member chooses.
- **Check In** offers labeled feelings, “What would help?” choices, and an optional note. Responses are private unless the member deliberately shares selected information.
- **Health** provides a broader health overview and relevant records, including previous appointment details, medications, care-team instructions, patterns, and connected sources. It uses additional permission checks and progressive disclosure.
- **My Plan** organizes activities the member may choose to prioritize after considering their check-in, health context, personal goals, and guidance they have accepted. It supports filters and one-step-at-a-time activity completion. Pair does not automatically prescribe or medically determine the member’s priorities.
- **Activity experience** supports My Plan by presenting one step at a time, with picture and text preferences, read aloud, simpler explanations, examples, original instructions, breaks, help requests, and difficulty feedback. Presentation changes must preserve the educator's objective and required outcome.
- **Patterns** lets the member review one selected health or wellbeing pattern at a time and see its source and comparison with their usual range.
- **Appointments** supports appointment preparation, member-reviewed packets, and follow-through on proposed care-team instructions. Health provides the broader health overview; Appointments provides the preparation and packet workflow.
- **My Circle** lets the member review, change, revoke, or time-limit each person's permissions.
- **Settings** provides member-specific accessibility, display, and privacy controls.

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

Use this hierarchy when product and implementation statements differ:

- This document defines Pair's product purpose and scope.
- [master-design-prompt.md](master-design-prompt.md) contains detailed intended UI/UX direction.
- [ui-ux-design-system.md](ui-ux-design-system.md) defines presentation and accessibility guidance.
- [roles-and-permissions.md](roles-and-permissions.md) defines intended role and information boundaries.
- [demo-walkthrough.md](demo-walkthrough.md) explains the current demonstrable flows.
- The current application code and tests establish what is actually implemented. Design documents do not override verified implementation claims.
