# Pair UI/UX Design System

This document summarizes the visual and interaction rules in [master-design-prompt.md](master-design-prompt.md). Use it as design guidance; it does not imply that all listed screens or controls exist in the current prototype.

## Design principles

- Use progressive disclosure and put one clear primary action first.
- Write in plain language with short sections and clear headings.
- Use generous spacing, rounded cards, and large interaction targets.
- Provide visible keyboard focus and sufficient color contrast.
- Support responsive desktop and mobile layouts.
- Use pictures with text labels when helpful.
- Respect reduced-motion settings and avoid unnecessary animation.
- Do not assume one visual style or information density suits everyone.
- Explain AI suggestions and keep the original instruction available.

## Member-selectable themes

| Theme | Direction |
|---|---|
| Ocean | Blue-green with warm gold accents. |
| Garden | Soft green with clay or warm brown accents. |
| Twilight | Accessible dark blue with soft blue and violet accents. |

Theme selection changes appearance only. It must not change permissions, data, or available features. Theme colors need contrast checks during implementation; names and descriptions alone do not establish accessible contrast.

The current prototype now uses Ocean, Garden, and Twilight as its selectable themes. Older saved Calm, Bright, and Dark values map to the closest new theme so existing browser sessions still render.

## Layout and interaction

- Member navigation: Home, Check In, Health, My Plan, Patterns, Appointments, My Circle, Settings.
- Keep Home focused on the next action. Show Now and Up Next by default; show Later only when the member chooses the full-day view.
- Show one activity step at a time by default.
- Pair icons or pictures with text labels; never make an icon the only explanation for an action.
- Keep secondary detail available through clear, optional controls.
- Make keyboard focus visible and controls usable by keyboard and touch.
- Do not rely on color alone to convey status.
- Use motion only when it helps comprehension; provide a reduced-motion experience.

## Activity presentation preferences

Support Pictures and Words, Words Only, and Pictures First. Offer Read Aloud, Show Fewer Words, Show an Example, Explain Differently, View the Original Instruction, I Need a Break, I Need Help, and Easy / Okay / Difficult feedback. An adapted presentation must retain the educator's learning objective and required outcome.

## Check-in choices

Show a clear icon or picture together with each label. Feelings include Calm, Okay, Tired, Worried, Overwhelmed, and Another Feeling. “What would help?” options include a quiet break, a smaller step, messaging someone trusted, read aloud, reducing screen content, or Nothing Right Now. Offer Pictures and Words, Words Only, and Pictures First display preferences. Check-in privacy remains clear at the point of entry and sharing.

## Health and sharing presentation

Show health details gradually and only after an appropriate permission check. Appointment packet content must identify its source and remain private until the member reviews and submits it. Sharing controls start unselected, say who will receive what, and support access expiration where the workflow provides it.

## Existing visual implementation

The prototype currently uses plain CSS theme variables in `public/css/style.css`, shared server-rendered layout in `templates/base.html`, and small JavaScript files in `public/js/` for theme preview, routine steps, and celebrations. Preserve this architecture when implementing the design. Do not add a frontend framework or a new package without approval.
