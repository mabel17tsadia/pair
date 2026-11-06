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

The current member navigation order is Home, Check In, My Plan, Health, Patterns, Appointments, My Circle, and Settings.

Members can choose the Ocean, Garden, or Twilight visual theme. Theme choice changes appearance only.

- **Home (implemented)** shows a short greeting and one Check In button, fictional health observations, and a Now / Up Next schedule. The schedule remains visible regardless of My Pace. After a check-in, Home shows a compact completion card with a Continue to My Plan link. At its scheduled time, an incomplete activity receives a small Due now badge; completed activities do not. No push, text, or email notification is sent.
- **Check In (implemented)** offers picture-supported feelings, My Pace, three “What would help?” choices (Quiet Break, Message Someone, and Nothing Right Now), and an optional private note. Every question is optional. For Nothing Right Now or no support choice, the confirmation offers Continue to My Plan and Change my choice; choosing Quiet Break or Message Someone opens that action directly. Full responses remain in collapsed private history.
- **My Pace (implemented in Check In)** saves the member's current choice in the Flask session. “One small step” and “Not sure” reveal one incomplete activity in My Plan; after completion, the next incomplete activity is shown. “A few things feel manageable” reveals up to three activities. “I need a pause” initially reveals no activity; Return when ready reveals one. If there is no check-in today, My Plan shows all matching activities with Today and All selected. My Plan has side-by-side When and From dropdown filters. It does not ask the member to choose My Pace again.
- **My Plan (implemented)** brings together member-added activities, coach- or educator-assigned activities, accepted healthcare instructions, and appointment-preparation activities. Proposed care-team instructions remain in Health until the member accepts them; declined or unanswered proposals do not enter My Plan. Accepted instructions use a member-selected date, recurrence, and optional reminder time where needed. A recurring instruction creates dated occurrences; completed occurrences are not counted twice and the next scheduled occurrence can appear on its next date. The member's choices organize activity display; Pair does not prescribe or medically determine priorities.
- **Routines and My Climb (implemented)** represent a routine once and show dated occurrences in My Plan according to its daily or selected weekly schedule. Completing one occurrence does not remove the reusable routine. My Climb Today uses the same scheduled activity records as My Plan, with one flag per activity and a weekly history of days when all of today's activities were completed.
- **Activity experience (implemented)** presents coach-assigned learning activities one step at a time. Picture and text presentation, Read Aloud, and reading speed are controlled in Settings. Supported activities include shorter wording, examples, alternate explanations, original instructions, break and help requests, and Easy / Okay / Difficult feedback. A help request is a session-only demo item visible in the coach workspace. Presentation changes preserve the educator's objective and required outcome.
- **Quiet Break (implemented)** is an immediate, timer-free support screen, not a multi-step learning activity. Done returns the member to My Plan without creating a new plan activity.
- **Health (implemented)** provides the member's overview and relevant records, including previous appointment details, medications, care-team instructions, patterns, and connected sources. It uses progressive disclosure. Accepted instructions show their status, schedule, and a View in My Plan link rather than duplicating the entire plan card.
- **Patterns (implemented)** lets the member select one health or wellbeing pattern at a time and see its source, plain-language comparison, usual-range band, and responsive chart. Desktop uses selectable pictogram tiles; mobile uses a compact select control.
- **Appointments (implemented)** supports appointment preparation, member-reviewed packets, and follow-through on proposed care-team instructions. Common-reason suggestions are optional, editable, labeled as AI-assisted or built-in, and linked to a profession-scope source. They are general discussion topics, not diagnoses or treatment advice. Health provides the broader health overview; Appointments provides preparation and packet workflows.
- **My Circle (implemented)** lets the member review, change, revoke, or time-limit permissions. Message Someone opens My Circle so the member selects an existing relationship and composes a demo message. No real or external message is sent.
- **Settings (implemented)** provides member-specific theme, density, picture preference, read-aloud, speech-rate, reminder, celebration, and reduced-motion controls. Demo data and reset offers a fictional data download and a confirmed session reset; reset clears progress and preferences while restoring fixture defaults. Pictures and Words is the default activity presentation. Display preferences are not repeated on Check In.

## Appointment and follow-up experience

Appointment preparation is a guided flow through appointment type and date/reason; member-selected changes; communication preferences; questions; packet review; and recipient and access-expiration selection. Nothing is shared before the member reviews and submits the packet. Each item identifies its source. The “Not sure?” common-reason link offers optional examples based on the selected professional's scope. Examples are built-in or AI-assisted, show their provenance and source, and can be selected, edited, or ignored.

Healthcare professionals may propose a prescription pickup, laboratory test, referral, follow-up appointment, discharge instruction, or other healthcare action. Proposals identify who submitted them, provide plain-language instructions, may include a due date and supporting details, and let the member accept, ask a question, or decline. Only accepted actions enter My Plan. When a proposal supplies no recurrence, the member may choose a reminder schedule; Pair never invents a medically required frequency. Reminders are shown in-app in the local demo only.

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
