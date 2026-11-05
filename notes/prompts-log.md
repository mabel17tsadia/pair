# Early development prompts

This file preserves the available early development prompts from 28 October 2026, when the prototype was initially called Pace. They show the beginning of the project and are not a complete prompt history. The product later evolved into Pair; later significant prompts will be represented in the challenge AI Prompts PDF.

## Stage 0: 28 October 2026
   "Create a simple Flask app in this folder. This folder already has CLAUDE.md; keep it. Use this structure: app.py, templates/, static/css/, static/js/, data/, notes/. Create a virtual environment and a requirements.txt with only flask, pandas, python-dotenv, and anthropic. The home page should just say 'Pace'. Add a .gitignore that includes .env, venv/, and pycache/. Add a short README with how to run the app. Explain each file and folder you created in plain English."

## Stage 1: Themes, layout, navigation — 28 October 2026

Stage 1: themes, layout and navigation.

Create templates/base.html that every screen will extend. Load the Google

Fonts Atkinson Hyperlegible (body) and Lexend (headings).

In static/css/style.css, define four themes as CSS variables on

<body data-theme="...">:

- calm: bg #F3F5F7, surface #FFFFFF, surface2 #E3E8ED, text #26323C,

  muted #55626E, border #DCE2E8, primary #3E5C76, primary-soft #E2EAF1,

  secondary #3F6F6A, secondary-soft #DDEDEA, alert #7A5410,

  alert-soft #F6EBD3

- colorful: bg #FFF7EC, surface #FFFFFF, surface2 #F5E3C8, text #231F3A,

  muted #5A5570, border #F0DFC6, primary #5B3FD0, primary-soft #ECE6FF,

  secondary #08706E, secondary-soft #D9F3F0, alert #8A4B00,

  alert-soft #FFE9B8

- bright: bg #FFFFFF, surface #F3F6F9, surface2 #DCE4EC, text #0B1220,

  muted #3E4A57, border #C8D2DC, primary #0A58CA, primary-soft #E5EFFF,

  secondary #00695C, secondary-soft #DDF2EE, alert #7A4A00,

  alert-soft #FFEFC7

- dark: bg #15191C, surface #1F2529, surface2 #323A40, text #ECEFF1,

  muted #A7B2B8, border #323A40, primary #8CC2A3, primary-soft #24352C,

  secondary #9EB9D4, secondary-soft #23303D, alert #E6C46C,

  alert-soft #3A3221

Use white text on primary buttons, except dark text (#10181A) in the

dark theme. Never use red for alerts.

Layout: on phones (under 900 px) show a bottom navigation bar with

Today, Check in, Circle, Me, each with a simple inline SVG icon and a

label. On wider screens show a top bar instead with the Pace name and

the same links. Tap targets at least 48 px.

Add a route /theme/<name> that saves the theme in the Flask session and

returns to the previous page. Create simple placeholder pages for Today,

Check in, Circle and Me that just show their title, so the navigation

can be tested.

Keep it short and commented, following CLAUDE.md.

## Stage 2: Sample data and the demo person picker — 28 October 2026

Before this stage, download each tab of the Google Sheet "Pace Sample Data (demo, fictional)" as CSV (File, Download, Comma separated values) and save them in the data folder as people.csv, daily.csv, heart.csv, tasks.csv and inbox.csv. The README tab is for people and does not need to be downloaded.

Stage 2: sample data and the demo person picker.

The data/ folder has five CSV files with fictional demo data:

- people.csv: id, first_name, last_name, usual_sleep_min,

  usual_resting_hr, drains, calms (drains and calms are separated by |)

- daily.csv: person_id, date, sleep_min, steps (last 7 days, today is

  2026-10-28)

- heart.csv: person_id, time, bpm (every 15 minutes today, 8:00 to 18:00)

- tasks.csv: person_id, title, time, part_of_day, load, source, steps

  (source is manual, calendar or inbox; steps are separated by |)

- inbox.csv: person_id, from, summary, deadline, suggested_task

Write data.py with small commented functions that read these with

pandas: get_people(), get_person(id), get_daily(id), get_heart(id),

get_tasks(id), get_inbox(id). Split the | lists into Python lists.

Build a "Choose a demo person" page as the home page (/). Show each

person as a large card with their initials in a circle and their full

name, plus the small note "Demo mode. Sample data." Tapping a card

saves the person's id in the Flask session and opens Today. Add a small

"Switch person" link in the top bar or the Me page that returns here.

Keep it short and commented, following CLAUDE.md.

## Stage 3: Pace rule and Today screen — 28 October 2026

Stage 3: the pace rule and the Today screen.

Write pace.py with one commented function get_pace(person, daily,

heart) that returns the level, plus short plain-English reasons:

- Gentle if last night's sleep is 45 or more minutes below the

  person's usual_sleep_min, OR the average heart rate over the last

  30 minutes of readings is 15 or more bpm above usual_resting_hr

- Ready if sleep is at or above usual AND heart rate is within 5 bpm

  of usual

- Steady otherwise

Reasons look like "Slept 6 h 40 min, less than usual" and "Heart rate

a bit higher than usual".

Build the Today page for the chosen person:

1. The date and the title "Today".

2. A "Your pace today" card: the level in large text, a 3-part bar

   (Gentle, Steady, Ready) with the current one filled, the reasons

   with small moon and heart icons, and the question "Does this feel

   right?" with a "Yes" button and a "Not really" link to Check in.

3. If the person has an inbox item, a "From your inbox" card with the

   summary and two buttons: "Add to my plan" and "Not now".

4. "My plan": a card per task with a simple icon, the title, the time,

   "from your calendar" or "from your inbox" when that is the source,

   and a load tag. Light shows 1 filled bar of 3, Medium 2, Heavy 3,

   always with the word, never color alone. Light uses primary colors,

   Medium uses secondary, Heavy uses alert.

5. A round "+" button for adding a task (it can link to a placeholder

   page for now).

Test with all three people: Jordan Reyes should be Gentle, Maya Chen

Steady and Theo Okafor Ready.

Keep it short and commented, following CLAUDE.md.

## Stage 4: Task steps — 28 October 2026
Task steps "Build the Task steps page: one step at a time with a progress bar, Done, Back, and I need a break, and a gentle finish message. Use a small script in static/js for moving between steps."

## Stage 5: Check in — 28 October 2026
Check in "Build the Check in page with five picture buttons, an optional note, Save and Skip. Store check ins in the Flask session for this demo."

## Stage 6: AI and Add a task — 28 October 2026
AI and Add a task "Write ai.py that calls Claude using the key from .env. Add a function suggest_task(text) that returns a load level and up to 4 short steps as JSON. If the call fails, use a simple keyword lookup as a backup. Build the Add a task page so the person can change the suggestion before saving."
  
## Stage 6 fix: missing API key — 28 October 2026
Bug found while testing: missing API key crashed the Add a task page.
[Bug found while testing the backup: when ANTHROPIC_API_KEY is missing
from .env (commented out), the Add a task page crashes with
"TypeError: Could not resolve authentication method" from ai.py line 43,
instead of using the keyword backup.

Fix suggest_task so that:
1. If no API key is set, it skips the Claude call and uses the keyword
   backup straight away, printing "No API key found, using keyword backup".
2. Any unexpected error during the Claude call also falls back to the
   backup instead of crashing the page.
Keep the change small and commented. Then tell me how to test both cases.]
