# Pair UI/UX Design System

This document summarizes the visual and interaction rules in [master-design-prompt.md](master-design-prompt.md). Use it as design guidance; it does not imply that all listed screens or controls exist in the current prototype.

## Design principles

- Give each section one clear primary action.
- Use text links for secondary navigation when a button would compete visually with the primary action.
- Explain privacy or safety once where it helps the member decide; do not repeat the same explanation on every screen.
- Do not display a control unless it produces a visible, working result.
- Use progressive disclosure for filters, connected sources, and additional details.
- Write in plain language with short sections and clear headings.
- Use generous spacing, rounded cards, and large interaction targets.
- Provide visible keyboard focus and sufficient color contrast.
- Support responsive desktop and mobile layouts.
- Use pictures with text labels when helpful.
- Respect reduced-motion settings and avoid unnecessary animation.
- Do not assume one visual style or information density suits everyone.
- Explain AI suggestions and keep the original instruction available.
- Keep common activities simple; put less common actions under More options.
- Keep charts completely visible in their card without internal scrolling.

## Member-selectable themes

| Theme | Direction |
|---|---|
| Ocean | Blue-green with warm gold accents. |
| Garden | Soft green with clay or warm brown accents. |
| Twilight | Accessible dark blue with soft blue and violet accents. |

Theme selection changes appearance only. It must not change permissions, data, or available features. Theme colors need contrast checks during implementation; names and descriptions alone do not establish accessible contrast.

The current prototype now uses Ocean, Garden, and Twilight as its selectable themes. Older saved Calm, Bright, and Dark values map to the closest new theme so existing browser sessions still render.

## Layout and interaction

- Member navigation: Home, Check In, My Plan, Health, Patterns, Appointments, My Circle, Settings.
- Keep Home focused on the next action. Your Day keeps Now and Up Next visible; My Pace changes how many activities My Plan reveals.
- Show My Plan's When and From controls as two compact dropdowns side by side; stack them on small screens. Default to Today and All; with no check-in today, show every matching activity.
- Show one activity step at a time by default.
- Keep Home's Now and Up Next schedule independent of My Pace; My Pace changes the number of activities revealed in My Plan.
- Pair icons or pictures with text labels; never make an icon the only explanation for an action.
- Keep secondary detail available through clear, optional controls.
- Make keyboard focus visible and controls usable by keyboard and touch.
- Do not rely on color alone to convey status.
- Use motion only when it helps comprehension; provide a reduced-motion experience.

## Activity presentation preferences

Pictures and Words is the default. Display preference choices (Pictures and Words, Words Only, and Pictures First), Read Aloud enablement, and speech rate live in Settings. Offer an activity control only when relevant and functional: Read Aloud for available instruction text, I Need Help only for coach-assigned activities with an identified coach, and difficulty feedback at the end of a supported activity. An adapted presentation must retain the educator's learning objective and required outcome. A Quiet Break is a single-screen, timer-free support action, not a learning sequence.

## Check-in choices

Show a clear icon or picture together with each label. Feelings include Calm, Okay, Tired, Worried, Overwhelmed, and Another Feeling. “What would help?” offers Quiet Break, Message Someone, and Nothing Right Now. Display preferences live in Settings, not on Check In. Check-in responses remain private; explain privacy at the point where it helps the member make a choice, without repeating the same banner on every result page.

## Health and sharing presentation

Show health details gradually and only after an appropriate permission check. Appointment packet content must identify its source and remain private until the member reviews and submits it. Sharing controls start unselected, say who will receive what, and support access expiration where the workflow provides it.

Use links for secondary actions such as opening Health details or returning to My Plan. Reserve filled buttons for the main action in each section. Keep responsive Health Patterns charts, labels, plotted points, usual-range bands, and recent-day highlights fully visible without an internally scrolling chart panel.

## Existing visual implementation

The prototype currently uses plain CSS theme variables in `public/css/style.css`, shared server-rendered layout in `templates/base.html`, and small JavaScript files in `public/js/` for theme preview, routine steps, and celebrations. Preserve this architecture when implementing the design. Do not add a frontend framework or a new package without approval.
