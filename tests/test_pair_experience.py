"""Exercise the main Pair routes and member-controlled workflows with Flask's test client."""

import os
import re
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from html.parser import HTMLParser

os.environ["SECRET_KEY"] = "pair-test-secret"
os.environ["ANTHROPIC_API_KEY"] = ""

import app as pair
import data
from demo_data import activity_assignments, load_demo_data, plan_activities


class ControlNames(HTMLParser):
    """Collect labels and controls so rendered pages can be checked for accessible names."""

    def __init__(self):
        super().__init__()
        self.labels = set()
        self.controls = []
        self.label_depth = 0

    # Track explicit or wrapped labels and form controls in one rendered document.
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "label":
            self.label_depth += 1
            if attrs.get("for"):
                self.labels.add(attrs["for"])
        if tag in ["input", "select", "textarea"] and attrs.get("type") != "hidden":
            self.controls.append({"id": attrs.get("id"), "named": bool(
                attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("title")),
                "wrapped": self.label_depth > 0})

    # Close wrapping labels after their last nested element.
    def handle_endtag(self, tag):
        if tag == "label":
            self.label_depth = max(0, self.label_depth - 1)


class PairExperienceTests(unittest.TestCase):
    """Share a fresh demo member session across the small route-level checks."""

    def setUp(self):
        pair.app.config["TESTING"] = True
        self.client = pair.app.test_client()
        self.records = load_demo_data()
        with self.client.session_transaction() as state:
            state["person_id"] = "p1"
            state["demo_role"] = "member"
            state["signup"] = {"first_name": "Jordan"}

    # Read generated Health activities inside the Flask request context that supplies member session state.
    def plan_health_rows(self, activity_date):
        with self.client:
            self.client.get("/health")
            return pair.plan_health_follow_ups(pair.current_person(), self.records, activity_date)

    # Open each role card into its actual route and show the matching role shell.
    def test_role_entry_opens_distinct_workspaces(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Welcome to Pair", page.data)
        self.assertIn(b"Get started", page.data)
        self.assertIn(b"Whose view would you like to explore?", page.data)
        self.assertEqual(page.data.count(b'class="role-card"'), 5)
        self.assertIn(b'href="/start">Get started</a>', page.data)
        self.assertIn(b'href="/signin">Sign in</a>', page.data)
        self.assertNotIn(b"Continue sign-up", page.data)
        self.assertNotIn(b'href="#role-choice"', page.data)
        self.assertIn(b"brand-mark", page.data)
        self.assertNotIn(b"Choose a demo person", page.data)
        self.assertNotIn(b"Maya Chen", page.data)
        self.assertNotIn(b"Theo Okafor", page.data)
        chooser = self.client.get("/?view=roles")
        self.assertEqual(chooser.status_code, 200)
        self.assertIn(b"Whose view would you like to explore?", chooser.data)
        self.assertEqual(chooser.data.count(b'class="role-card"'), 5)
        self.assertIn(b"Continue sign-up", chooser.data)
        destinations = {"member": ("/today", b"Jordan Reyes"),
                        "coach": ("/coach", b"Dana Brooks"),
                        "healthcare": ("/professional", b"Dr. Priya Patel"),
                        "trusted": ("/trusted", b"Marisol Reyes"),
                        "admin": ("/admin", b"Alex Morgan")}
        for role, (path, identity) in destinations.items():
            response = self.client.post("/demo/role", data={"role": role})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.headers["Location"].endswith(path))
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200, role)
            self.assertIn(f'data-demo-role="{role}"'.encode(), page.data)
            self.assertIn(identity, page.data)
            self.assertIn(b"role-sidebar", page.data)
            self.assertIn(b"mobile-role-nav", page.data)
            if role == "member":
                for label in [b"Pair member", b"Your information, your choices", b"Pair keeps the member in control", b"Patterns", b"Appointments"]:
                    self.assertIn(label, page.data)
                member_nav = page.data.split(b'<nav aria-label="Pair member navigation">', 1)[1].split(b"</nav>", 1)[0]
                nav_labels = [b"Home", b"Check In", b"My Plan", b"Health", b"Patterns",
                              b"Appointments", b"My Circle", b"Settings"]
                positions = [member_nav.index(label) for label in nav_labels]
                self.assertEqual(positions, sorted(positions))

    # Keep the denser public and member pages complete, labeled, and responsive.
    def test_density_pages_keep_choices_content_and_accessible_controls(self):
        landing = self.client.get("/").data
        for identity in [b"Jordan Reyes", b"Dana Brooks", b"Dr. Priya Patel",
                         b"Marisol Reyes", b"Alex Morgan", b"Members control what they share"]:
            self.assertIn(identity, landing)

        appointment = self.client.get("/visit").data
        self.assertEqual(appointment.count(b'class="card visit-choice"'), 7)
        self.assertIn(b"What kind of appointment is it?", appointment)

        circle = self.client.get("/circle").data
        level_help = circle.split(b'class="card levels-help"', 1)[1].split(b"</details>", 1)[0]
        self.assertIn(b"What each level means", level_help)
        self.assertIn(b"Manage", circle)

        plan = self.client.get("/my-plan").data
        for label in [b"When", b"From", b"Today", b"Tomorrow", b"This Week", b"Later", b"Added by Me",
                      b"From My Coach", b"From Health", b"No check-in today."]:
            self.assertIn(label, plan)
        self.assertNotIn(b"Save My Pace", plan)

        patterns = self.client.get("/patterns").data
        for label in [b"Sleep", b"Movement", b"Screen Use", b"Time Away from Home",
                      b"Blood Sugar", b"Heart Rate", b"Usual range", b"Last 5 days"]:
            self.assertIn(label, patterns)
        self.assertNotIn(b"Usual range</strong> is the band around your earlier days", patterns)
        self.assertNotIn(b"Comparison period: the last five days", patterns)
        self.assertNotIn(b'class="card pattern-key"', patterns)

        with open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn(".entry-roles .role-grid { grid-template-columns: repeat(5, minmax(0, 1fr))", css)
        self.assertIn("@media (min-width: 768px) and (max-width: 1199px)", css)
        self.assertIn("@media (min-width: 1200px)", css)
        self.assertIn("@media (max-width: 767px) {\n  .entry-roles .role-grid { grid-template-columns: 1fr; }", css)

    # Keep prototype sign-in links honest and never submit the displayed password fields.
    def test_demo_sign_in_and_help_pages_are_transparent(self):
        page = self.client.get("/signin")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"name=\"role\" value=\"member\"", page.data)
        self.assertIn(b"Forgot password?", page.data)
        self.assertIn(b"Organization sign-in", page.data)
        self.assertIn(b"not submitted or checked", page.data)
        self.assertIn(b"signin-layout", page.data)
        self.assertIn(b"prototype-note", page.data)
        self.assertNotIn(b"Email me a link", page.data)
        self.assertNotIn(b'name="sign-in-email"', page.data)
        self.assertNotIn(b'name="sign-in-password"', page.data)
        self.assertIn(b"not connected", self.client.get("/forgot-password").data)
        self.assertIn(b"cannot verify an account", self.client.get("/signin/organization").data)
        onboarding = self.client.get("/start/1")
        self.assertIn(b"onboarding-page", onboarding.data)
        self.assertIn(b"progress-dots", onboarding.data)

    # Do not allow direct links to another role's route to bypass the selected demo workspace.
    def test_cross_role_routes_redirect_to_active_workspace(self):
        response = self.client.get("/coach")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/today"))
        self.client.post("/demo/role", data={"role": "healthcare"})
        response = self.client.get("/my-plan")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/professional"))
        self.assertEqual(self.client.get(response.headers["Location"]).status_code, 200)
        response = self.client.get("/settings")
        self.assertTrue(response.headers["Location"].endswith("/professional/settings"))
        with self.client.session_transaction() as state:
            state["demo_role"] = "member"

    # Open every role navigation destination and verify mobile navigation is present.
    def test_role_navigation_destinations_and_overviews(self):
        pages = {
            "coach": ["/coach", "/coach/learners", "/coach/library", "/coach/settings", "/coach/learners/p1"],
            "healthcare": ["/professional", "/professional/packets", "/professional/next-steps", "/professional/settings",
                           "/professional/packets/packet-upcoming"],
            "trusted": ["/trusted", "/trusted/encouragement", "/trusted/settings"],
            "admin": ["/admin", "/admin/people", "/admin/invitations", "/admin/consent",
                      "/admin/templates", "/admin/settings"],
        }
        for role, routes in pages.items():
            with self.client.session_transaction() as state:
                state["demo_role"] = role
                state["person_id"] = "p1"
            for route in routes:
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200, f"{role}: {route}")
                self.assertIn(b"mobile-role-nav", response.data)
                self.assertIn(f'data-demo-role="{role}"'.encode(), response.data)

    # Keep the member's mobile bar to four main links and a keyboard-operable More menu.
    def test_mobile_navigation_keeps_secondary_destinations_in_more(self):
        page = self.client.get("/today").data
        mobile_nav = page.split(b'<nav class="mobile-role-nav"', 1)[1].split(b"</nav>", 1)[0]
        primary = mobile_nav.split(b'<details class="mobile-more-menu"', 1)[0]
        self.assertEqual(primary.count(b"<a "), 4)
        labels = [b"Home", b"Check In", b"My Plan", b"Health"]
        self.assertEqual([primary.index(label) for label in labels], sorted(primary.index(label) for label in labels))
        more = mobile_nav.split(b'<div class="mobile-more-links">', 1)[1]
        for label in [b"Patterns", b"Appointments", b"My Circle", b"Settings"]:
            self.assertIn(label, more)
        self.assertIn(b"<summary", mobile_nav)
        self.assertIn(b">More</span></summary>", mobile_nav)
        patterns = self.client.get("/patterns").data
        more_summary = patterns.split(b'<details class="mobile-more-menu">', 1)[1].split(b"</summary>", 1)[0]
        self.assertIn(b'aria-current="page"', more_summary)
        self.assertIn("@media (max-width: 767px)", open(
            os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8").read())

        with self.client.session_transaction() as state:
            state["demo_role"] = "admin"
        admin = self.client.get("/admin").data
        admin_nav = admin.split(b'<nav class="mobile-role-nav"', 1)[1].split(b"</nav>", 1)[0]
        self.assertEqual(admin_nav.split(b'<details class="mobile-more-menu"', 1)[0].count(b"<a "), 4)
        self.assertIn(b"Organization Settings", admin_nav)

    # Protect the focused mobile layout contracts while leaving desktop shell rules in place.
    def test_mobile_layout_rules_keep_content_and_desktop_shell(self):
        with open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn("@media (min-width: 900px)", css)
        self.assertIn(".role-sidebar { position: sticky", css)
        self.assertIn(".public-nav { display: none; }", css)
        self.assertIn("calc(.35rem + env(safe-area-inset-bottom))", css)
        self.assertIn("calc(6.5rem + env(safe-area-inset-bottom))", css)
        self.assertIn(".mobile-role-nav > a, .mobile-more-menu", css)
        self.assertIn(".mobile-more-links a {", css)
        self.assertIn(".entry-copy .actions > * { flex: 1 1 100%", css)
        self.assertIn(".visit-choice { min-height: 3.25rem", css)
        self.assertIn(".appointment-details summary, .source-summary", css)
        self.assertIn("max-width: min(10rem, 37vw)", css)
        self.assertIn("overflow-wrap: anywhere", css)

    # Keep desktop density changes isolated from the completed mobile-specific rules.
    def test_desktop_density_keeps_targets_and_compacts_shared_pages(self):
        with open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn("@media (min-width: 769px)", css)
        self.assertIn("@media (min-width: 900px)", css)
        self.assertIn("min-height: 5.25rem", css)
        self.assertIn("grid-template-columns: 15rem minmax(0, 1fr)", css)
        self.assertIn("min-height: var(--target-min)", css)
        self.assertIn("min-height: 12.5rem", css)
        self.assertIn(".entry-hero { box-sizing: border-box; min-height: 19rem", css)
        self.assertIn(".checkin-form .choice-box { min-height: 5.5rem", css)
        self.assertIn(".checkin-form .choice-box { min-height: 7rem", css)
        self.assertIn("grid-template-columns: repeat(6, minmax(0, 1fr))", css)
        self.assertIn(".landing-hero { min-height: min(19rem, calc(100vh - 7rem))", css)
        self.assertIn(".plan-filter-selects { gap: .5rem; margin-block: .65rem; }", css)
        self.assertIn(".circle-row-action", css)
        self.assertIn(".pattern-tile { min-height: 5.75rem", css)
        self.assertIn(".landing-hero { min-height: 7rem", css)
        self.assertIn(".visit-choice { box-sizing: border-box; min-height: 3.75rem", css)
        self.assertIn("@media (min-width: 900px) and (max-height: 650px)", css)
        for path in ["/", "/?view=roles", "/today", "/checkin", "/health", "/my-plan", "/visit/primary",
                     "/patterns", "/devices", "/settings"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    # Keep saved display preferences in Settings instead of repeating them in Check In.
    def test_display_preferences_are_saved_in_settings(self):
        page = self.client.get("/checkin")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b"Display preferences", page.data)
        settings = self.client.get("/settings?section=appearance")
        self.assertIn(b"Pictures and Words", settings.data)
        self.assertIn(b'value="pictures_words" checked', settings.data)

    # Keep the member Home brief and focused on next actions and private summaries.
    def test_member_home_summarizes_without_showing_all_pattern_details(self):
        page = self.client.get("/today")
        self.assertEqual(page.status_code, 200)
        for label in [b"Good afternoon, Jordan.", b"Your Day", b"Up Next", b"My Climb",
                      b"Your week at a glance", b"Upcoming appointment", b"Fictional demo schedule"]:
            self.assertIn(label, page.data)
        self.assertNotIn(b"Your usual average", page.data)
        self.assertNotIn(b"Last 5-day average", page.data)
        self.assertNotIn(b"Last Check In", page.data)
        self.assertNotIn(b"My Circle</p>", page.data)
        self.assertIn(b"Check In", page.data)
        self.assertNotIn(b"Choose one thing. Details stay tucked away until you want them.", page.data)
        self.assertNotIn(b"Want to check in before choosing your next step?", page.data)
        self.assertEqual(page.data.count(b'class="btn-primary" href="/checkin"'), 1)
        self.assertNotIn(b"home-checkin-invite", page.data)
        plan_page = self.client.get("/my-plan")
        self.assertIn(b"No check-in today. Showing all activities", plan_page.data)
        self.assertIn(b"Change in Check In", plan_page.data)
        self.assertNotIn(b"Save My Pace", plan_page.data)
        self.assertIn(b"activity-pictogram", plan_page.data)

    # Show the three ordered fictional health observations and their expandable provenance.
    def test_home_summary_uses_specific_supported_observations(self):
        page = self.client.get("/today").data
        summary = page.split(b'class="card home-health-summary"', 1)[1].split(b"</section>", 1)[0]
        self.assertEqual(summary.count(b'class="home-health-observation '), 3)
        first = summary.index(b"Resting heart rate stayed within the target range")
        second = summary.index(b"Glucose readings stayed within the target range")
        third = summary.index(b"Recent sleep was about 1 hour 8 minutes below Jordan")
        self.assertLess(first, second)
        self.assertLess(second, third)
        self.assertIn(b"Fictional demonstration data", summary)
        self.assertIn(b"Measurement period:", summary)
        self.assertIn(b"Date recorded:", summary)
        self.assertIn("below Jordan’s usual range".encode(), summary)
        self.assertNotIn(b"An activity in your plan is marked complete", summary)
        self.assertNotIn(b"normal", summary.lower())
        self.assertNotIn(b"abnormal", summary.lower())

    # Keep the Home timeline limited to its Now and Up Next schedule, independent of My Pace.
    def test_home_schedule_today_filter_pace_and_plan_links(self):
        page = self.client.get("/today")
        day = page.data.split(b'<ol class="day-timeline">', 1)[1].split(b'</ol>', 1)[0]
        self.assertNotIn(b"Plan a bus trip", day)
        self.assertNotIn(b"Primary care", day)
        self.assertIn(b"Scheduled time:", day)
        self.assertIn(b"Duration: About", day)
        self.assertIn(b"Tidy my desk", day)
        self.assertIn(b"Walk for 15 minutes daily", day)
        self.assertNotIn(b"Later", day)
        self.assertNotIn(b"activities are hidden", day)
        self.assertIn(b"/my-plan?time=today", day)
        focused = self.client.get("/my-plan", query_string={"time": "today", "activity": "assignment-wellness-demo-today"})
        self.assertIn(b'id="assignment-wellness-demo-today"', focused.data)
        self.assertEqual(day.count(b'class="timeline-marker"'), 2)
        self.assertIn(b"Now", day)
        self.assertIn(b"Up Next", day)
        self.assertNotIn(b"Later", day)

    # Keep the landing page focused while placing appointment and instruction details behind actions.
    def test_health_overview_summarizes_visit_appointment_and_care_instructions(self):
        page = self.client.get("/health")
        self.assertEqual(page.status_code, 200)
        for label in [b"Last appointment", b"Primary care follow-up", b"20 October", b"Dr. Priya Patel",
                      b"4 vitals recorded", b"1 medication", b"3 instructions", b"View appointment details",
                      b"Next appointment", b"November 12", b"2:30 PM", b"Prepare for appointment",
                      b"Instructions from your care team", b"Review instructions",
                      b"View my health activities in My Plan"]:
            self.assertIn(label, page.data)
        self.assertIn(b'<details class="appointment-details">', page.data)
        self.assertIn(b"Recorded vitals", page.data)
        self.assertIn(b"Medication or prescription received", page.data)
        self.assertIn(b"Full after-visit information", page.data)
        self.assertNotIn(b"My accepted health actions", page.data)
        self.assertNotIn(b"Instructions from your last visit", page.data)
        self.assertNotIn(b"Glucose:</strong>", page.data)
        self.assertLessEqual(page.data.count(b'class="health-instruction-row"'), 3)
        for label in [b"My Shared Packets", b"My Health Plan", b"My Medications", b"Health Patterns",
                      b"Connected Data Sources", b"health-row-chevron"]:
            self.assertIn(label, page.data)

    # Use the shared Health action record for the walking duration on Home, Plan, and Health.
    def test_walking_activity_duration_matches_across_member_pages(self):
        walk = next(item for item in self.records["health_follow_ups"] if item["id"] == "follow-up-demo-today")
        self.assertEqual(walk["estimated_minutes"], 15)
        for route in ["/today", "/my-plan?time=today&source=health", "/health"]:
            page = self.client.get(route)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Walk for 15 minutes daily", page.data)
            self.assertIn(b"About 15 minutes", page.data)
        plan = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn(b"From Health", plan)
        self.assertIn(b"Start", plan)
        self.assertIn(b"Done", plan)
        self.assertNotIn(b"Next action: Review the details in Health", plan)

    # Test the in-progress controls for one occurrence without altering the Health record.
    def test_daily_health_start_pause_continue_done_and_remove(self):
        occurrence = f"follow-up-demo-today@{data.get_today()}"
        url = f"/my-plan/health-action/{occurrence}"
        self.assertEqual(self.client.post(url, data={"choice": "start"}).status_code, 302)
        page = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn(b">Pause</button>", page)
        self.assertIn(b'value="done"', page)
        self.client.post(url, data={"choice": "pause"})
        paused = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn("Paused — continue when ready".encode(), paused)
        self.assertIn(b'value="continue"', paused)
        self.client.post(url, data={"choice": "continue"})
        continued = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn(b'value="pause"', continued)
        self.client.post(url, data={"choice": "done"})
        self.assertNotIn(occurrence.encode(), self.client.get("/my-plan?time=today&source=health").data)

        with self.client.session_transaction() as state:
            state["health_plan_states"] = {"p1": {}}
        page = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn(b"Remove this recurring activity from My Plan? Future daily occurrences will stop.", page)
        self.client.post(url, data={"choice": "remove"})
        self.assertNotIn(occurrence.encode(), self.client.get("/my-plan?time=today&source=health").data)

    # Give a daily Health instruction a separate, idempotent occurrence for each demo date.
    def test_daily_health_activity_is_repeatable_and_counted_once_per_day(self):
        action_id = "follow-up-demo-today"
        today = data.get_today()
        occurrence = f"{action_id}@{today}"
        page = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn(f'id="{occurrence}"'.encode(), page)
        self.assertIn(b"More options", page)
        self.assertIn(b"View health details", page)
        self.assertIn(b"confirm('Remove this recurring activity", page)
        for hidden_copy in [b"Choose another date", b"Reschedule", b"Open Health follow-up",
                            b"Proposal date", b"Next action:"]:
            self.assertNotIn(hidden_copy, page)

        done_url = f"/my-plan/health-action/{occurrence}"
        self.assertEqual(self.client.post(done_url, data={"choice": "done"}).status_code, 302)
        self.client.post(done_url, data={"choice": "done"})
        with self.client.session_transaction() as state:
            completions = state["health_activity_completions"]["p1"]
            self.assertEqual(len(completions), 1)
            self.assertEqual(completions[occurrence]["date"], today)
        climb = self.client.get("/climb").data
        self.assertIn(b"1 of ", climb)
        self.assertIn(b"activities completed", climb)
        self.assertIn(b"0 of 7 days this week", climb)
        self.assertNotIn(occurrence.encode(), self.client.get("/my-plan?time=today&source=health").data)

        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
        with patch.object(data, "get_today", return_value=tomorrow):
            tomorrow_page = self.client.get("/my-plan?time=today&source=health").data
        self.assertIn(f'id="{action_id}@{tomorrow}"'.encode(), tomorrow_page)
        with self.client.session_transaction() as state:
            self.assertEqual(len(state["health_activity_completions"]["p1"]), 1)

    # Preserve a learning activity's current step when the member pauses and asks for help.
    def test_activity_break_resumes_saved_step_and_help_is_demo_only(self):
        activity_id = self.records["activity_assignments"][0]["id"]
        url = f"/activity/{activity_id}"
        paused = self.client.post(url, data={"step": "2", "action": "break"})
        self.assertIn("/my-plan", paused.headers["Location"])
        with self.client.session_transaction() as state:
            self.assertEqual(state["activity_progress"][activity_id]["status"], "paused")
            self.assertEqual(state["activity_progress"][activity_id]["step"], 2)
        plan = self.client.get(paused.headers["Location"]).data
        self.assertIn(b"Continue", plan)
        resumed = self.client.get(url)
        self.assertIn(b"Step 2 of", resumed.data)

        confirm = self.client.post(url, data={"step": "2", "action": "help"})
        panel = self.client.get(confirm.headers["Location"]).data
        self.assertIn(b"Ask Dana Brooks for help?", panel)
        self.assertIn(b"This prototype does not deliver a real message.", panel)
        sent = self.client.post(url, data={"step": "2", "action": "help_send"})
        self.assertIn(b"Help request saved for this demo.", self.client.get(sent.headers["Location"]).data)

    # Keep the colorful meal choices, single primary next action, and final-only feedback.
    def test_activity_step_layout_and_meal_picture_choices(self):
        meal = next(item for item in activity_assignments(self.records, "p1")
                    if item.get("template_id") == "template-coach-01")
        page = self.client.get(f"/activity/{meal['id']}").data
        for picture, label in [("🥪", "Sandwich"), ("🥣", "Oatmeal"), ("🥗", "Salad"), ("✨", "Something else")]:
            self.assertIn(picture.encode(), page)
            self.assertIn(label.encode(), page)
        self.assertLess(page.index(b"</fieldset>"), page.index(b"Next step"))
        self.assertLess(page.index(b"Next step"), page.index(b"Read Aloud"))
        self.assertNotIn(b"How did this activity feel?", page)
        final_page = self.client.get(f"/activity/{meal['id']}?step={len(meal['steps'])}").data
        self.assertIn(b"How did this activity feel?", final_page)
        for feedback in [b"Easy", b"Okay", b"Difficult"]:
            self.assertIn(feedback, final_page)

    # Let the member open every care-team instruction and its available choices.
    def test_health_instruction_review_has_back_navigation_and_all_choices(self):
        page = self.client.get("/health/next-steps")
        self.assertIn(b"Back to Health", page.data)
        self.assertIn(b"Accept", page.data)
        self.assertIn(b"Decline", page.data)
        self.assertIn(b"Record sleep for seven days", page.data)
        self.assertIn(b"Bring your blood-pressure readings", page.data)

    # Keep Health records member-only and expose only the values marked as measured.
    def test_health_visit_data_is_member_scoped_and_packet_navigation_is_visible(self):
        for route in ["/health", "/health/packets", "/health/packets/packet-completed"]:
            self.assertEqual(self.client.get(route).status_code, 200)
        packets = self.client.get("/health/packets")
        self.assertIn(b"Back to Health", packets.data)
        self.assertIn(b"Prepare another appointment", packets.data)
        detail = self.client.get("/health/packets/packet-completed")
        self.assertIn(b"Back to Health", detail.data)
        self.assertIn(b"Prepare another appointment", detail.data)
        with self.client.session_transaction() as state:
            state["person_id"] = "p2"
        page = self.client.get("/health")
        self.assertNotIn(b"118/76 mmHg", page.data)
        self.assertNotIn(b"Amoxicillin", page.data)

    # Hide the blood-pressure instruction when its only relevant source is unavailable.
    def test_blood_pressure_instruction_requires_a_requested_available_reading(self):
        records = load_demo_data()
        records["appointment_summaries"][0]["manual_readings"] = []
        with patch.object(pair, "load_demo_data", return_value=records), \
                patch.object(pair, "devices_for", return_value=[{"paired": False, "signals": ["blood_pressure"]}]):
            page = self.client.get("/health")
        self.assertNotIn(b"Bring your blood-pressure readings", page.data)

    # Replace medication placeholders with the exact fictional instruction and source details.
    def test_medication_page_has_coherent_fictional_fields_without_placeholders(self):
        page = self.client.get("/health/medications").data
        for text in [b"Fictional demonstration data", b"Amoxicillin 500 mg capsule", b"500 mg (one capsule)",
                     b"Three times daily, about every 8 hours, for 7 days",
                     b"Take one capsule by mouth three times daily until the 7-day course is finished.",
                     b"Dr. Priya Patel", b"20 October"]:
            self.assertIn(text, page)
        for placeholder in [b"example dose", b"example time", b"Example medication"]:
            self.assertNotIn(placeholder.lower(), page.lower())

    # Keep the Home schedule stable while Check In sets the session's My Pace value.
    def test_my_pace_is_saved_from_checkin_and_home_schedule_stays_basic(self):
        home = self.client.get("/today").data
        timeline = home.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0]
        self.assertEqual(timeline.count(b'class="timeline-marker"'), 2)
        self.assertIn(b"Now", timeline)
        self.assertIn(b"Up Next", timeline)
        self.assertNotIn(b"Later", timeline)
        self.assertGreater(self.client.get("/my-plan").data.count(b'class="card activity-card'), 3)
        form = self.client.get("/checkin").data
        submission_id = re.search(rb'name="submission_id" value="([^\"]+)"', form).group(1).decode()
        response = self.client.post("/checkin", data={"action": "save", "submission_id": submission_id,
                                    "manageability": "few_manageable"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertEqual(state["checkins"][-1]["my_pace"], "few_manageable")
        self.assertEqual(self.client.get("/my-plan?time=this_week&source=all").data.count(b'class="card activity-card'), 3)
        home = self.client.get("/today").data
        timeline = home.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0]
        self.assertEqual(timeline.count(b'class="timeline-marker"'), 2)
        self.client.post("/settings/delete-data", data={"confirm_delete": "yes"})
        with self.client.session_transaction() as state:
            state["person_id"] = "p1"
            state["demo_role"] = "member"
        self.assertGreater(self.client.get("/my-plan").data.count(b'class="card activity-card'), 3)

    # Keep care-team instructions private and separate from prescription details.
    def test_health_instructions_are_member_only_and_keep_original_sources(self):
        page = self.client.get("/health/my-plan")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Instructions from your care team", page.data)
        self.assertIn(b"Dr. Priya Patel", page.data)
        self.assertIn(b"Original instruction", page.data)
        self.assertIn(b"Fictional demo records", page.data)
        for role in ["coach", "trusted", "admin", "healthcare"]:
            with self.client.session_transaction() as state:
                state["demo_role"] = role
            self.assertNotEqual(self.client.get("/health/my-plan").status_code, 200)

    # Keep notification previews generic by default and settings controls progressively disclosed.
    def test_settings_sections_and_notification_preview_privacy(self):
        page = self.client.get("/settings")
        self.assertIn(b"Appearance and accessibility", page.data)
        self.assertIn(b"Notifications and celebrations", page.data)
        self.assertNotIn(b'id="speech-rate"', page.data)
        page = self.client.get("/settings?section=notifications")
        self.assertIn(b"Pair has a private check-in reminder for you.", page.data)
        self.assertIn(b"Show activity name", page.data)
        self.client.post("/settings?section=notifications", data={
            "action": "save_notification_privacy", "notification_privacy": "detailed",
            "activity_reminders": "on", "completion_celebration": "on", "reduced_motion": "off"})
        self.assertIn(b"Your planned activity is ready to view in Pair.",
                      self.client.get("/settings?section=notifications").data)
        self.assertEqual(self.client.get("/settings?section=appearance").status_code, 200)

    # Keep Connect visible beside a collapsed device row with details available on selection.
    def test_device_rows_show_user_categories_and_connection_actions(self):
        page = self.client.get("/devices")
        self.assertIn(b"Available to connect", page.data)
        self.assertIn(b"Health apps", page.data)
        self.assertIn(b"Bluetooth devices", page.data)
        self.assertIn(b"Connect</a>", page.data)
        self.assertIn(b"View details", page.data)
        self.assertIn(b"Privacy:", page.data)

    # Keep the coach dashboard useful while excluding private and unrelated member details.
    def test_coach_dashboard_uses_learning_only_signals(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "coach"
            state["checkins"] = [{"person_id": "p1", "note": "COACH_PRIVATE_CHECKIN_SENTINEL"}]
            state["visit_entries"] = {"p1": [{"value": "COACH_PRIVATE_HEALTH_SENTINEL"}]}
        page = self.client.get("/coach")
        for label in [b"Authorized learners", b"Activities needing attention", b"Completed this week",
                      b"Draft activity templates", b"Jordan Reyes", b"Theo Okafor", b"Maya Chen",
                      b"Help and adaptation requests", b"Show one step at a time with a picture"]:
            self.assertIn(label, page.data)
        self.assertNotIn(b"COACH_PRIVATE_CHECKIN_SENTINEL", page.data)
        self.assertNotIn(b"COACH_PRIVATE_HEALTH_SENTINEL", page.data)

    # Keep administrator pages on fictional account and audit metadata, not member content.
    def test_admin_pages_exclude_member_content(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "admin"
            state["checkins"] = [{"person_id": "p1", "note": "ADMIN_PRIVATE_CHECKIN_SENTINEL"}]
            state["visit_entries"] = {"p1": [{"value": "ADMIN_PRIVATE_HEALTH_SENTINEL"}]}
            state["activity_answers"] = {"p1": "ADMIN_PRIVATE_ANSWER_SENTINEL"}
        for route in ["/admin", "/admin/people", "/admin/invitations", "/admin/consent",
                      "/admin/templates", "/admin/settings"]:
            page = self.client.get(route)
            self.assertEqual(page.status_code, 200, route)
            if route in ["/admin", "/admin/people", "/admin/settings"]:
                self.assertIn(b"Role assignment grants product capabilities, not access to individual member content", page.data)
            for sentinel in [b"ADMIN_PRIVATE_CHECKIN_SENTINEL", b"ADMIN_PRIVATE_HEALTH_SENTINEL",
                             b"ADMIN_PRIVATE_ANSWER_SENTINEL"]:
                self.assertNotIn(sentinel, page.data)
        self.assertIn(b"First Place demonstration program", self.client.get("/admin").data)

    # Show Marisol only the weekly summary Jordan chose to share and keep encouragement session-only.
    def test_trusted_person_sees_only_shared_summary_and_safe_encouragement(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "trusted"
            state["checkins"] = [{"person_id": "p1", "note": "TRUSTED_PRIVATE_CHECKIN_SENTINEL"}]
            state["visit_entries"] = {"p1": [{"value": "TRUSTED_PRIVATE_HEALTH_SENTINEL"}]}
        page = self.client.get("/trusted")
        for label in [b"Jordan Reyes", b"3 of 5 personal goals completed", b"3 November through 30 November",
                      b"Support without surveillance", b"Encouragement"]:
            self.assertIn(label, page.data)
        self.assertNotIn(b"TRUSTED_PRIVATE_CHECKIN_SENTINEL", page.data)
        self.assertNotIn(b"TRUSTED_PRIVATE_HEALTH_SENTINEL", page.data)
        response = self.client.post("/trusted/encouragement", data={"contact": "Jordan Reyes", "encouragement": "cheer"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(b"not delivered", self.client.get(response.headers["Location"]).data)

    # Keep the sample permission visible in Circle and make its revoke action remove trusted access.
    def test_member_can_end_the_sample_trusted_summary(self):
        page = self.client.get("/circle")
        self.assertIn(b"Marisol Reyes", page.data)
        self.assertIn(b"Weekly summary", page.data)
        response = self.client.post("/circle/revoke-share", data={"name": "Marisol Reyes"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            state["demo_role"] = "trusted"
        page = self.client.get("/trusted")
        self.assertIn(b"No summary has been shared", page.data)

    # Keep professional review limited to packet fields, selected questions, and current authorization.
    def test_professional_overview_and_packet_boundary(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "healthcare"
            state["checkins"] = [{"person_id": "p1", "note": "PRO_PACKET_PRIVATE_CHECKIN_SENTINEL"}]
            state["visit_entries"] = {"p1": [{"value": "PRO_PACKET_PRIVATE_HEALTH_SENTINEL"}]}
        overview = self.client.get("/professional")
        for label in [b"New appointment packets", b"Shared by members and awaiting your review",
                      b"Follow-ups awaiting member action", b"Access expiring within 14 days",
                      b"Completed packet reviews"]:
            self.assertIn(label, overview.data)
        packet = self.client.get("/professional/packets/packet-upcoming")
        for label in [b"Jordan Reyes", b"Primary care", b"Dr. Priya Patel", b"Authorization period",
                      b"Communication and accommodation preferences", b"Questions the member chose to include",
                      b"Not included in this packet", b"Source:"]:
            self.assertIn(label, packet.data)
        self.assertNotIn(b"PRO_PACKET_PRIVATE_CHECKIN_SENTINEL", packet.data)
        self.assertNotIn(b"PRO_PACKET_PRIVATE_HEALTH_SENTINEL", packet.data)

    # Keep coach adaptation requests available only for learners with the relevant sharing level.
    def test_member_adaptation_request_appears_in_authorized_coach_view(self):
        activity_id = self.records["activity_assignments"][0]["id"]
        self.client.post(f"/activity/{activity_id}", data={"step": "1", "action": "help"})
        self.client.post(f"/activity/{activity_id}", data={"step": "1", "action": "help_send"})
        with self.client.session_transaction() as state:
            state["demo_role"] = "coach"
        page = self.client.get("/coach")
        self.assertIn(b"Help requested", page.data)

    # Replace route variables with known safe demo fixture values.
    def route_path(self, rule):
        values = {"activity_id": self.records["activity_assignments"][0]["id"], "person_id": "p1",
                  "step": "1", "learner_id": "p1", "action_id": self.records["health_follow_ups"][0]["id"],
                  "visit": "primary", "packet_id": self.records["appointment_packets"][0]["id"],
                  "name": "My%20phone", "index": "0", "filename": "css/style.css"}
        return re.sub(r"<(?:(?:int|path):)?([^>]+)>", lambda match: values[match.group(1)], rule)

    # Ensure every registered GET route renders, redirects, or returns an intentional client error.
    def test_all_registered_routes_match_without_server_errors(self):
        for rule in pair.app.url_map.iter_rules():
            path = self.route_path(rule.rule)
            response = self.client.get(path)
            self.assertLess(response.status_code, 500, f"{rule.endpoint} at {path}")

    # Submit safe demo values to every form endpoint and catch broken button handlers.
    def test_all_registered_post_routes_handle_empty_demo_submissions(self):
        for rule in pair.app.url_map.iter_rules():
            if "POST" not in rule.methods:
                continue
            path = self.route_path(rule.rule)
            response = self.client.post(path, data={})
            self.assertLess(response.status_code, 500, f"{rule.endpoint} at {path}")

    # Check each plan filter combination against the data provider and its rendered route.
    def test_activity_time_and_source_filters(self):
        for time_filter in ["today", "tomorrow", "this_week", "later"]:
            for source_filter in ["all", "member", "coach", "health"]:
                rows = plan_activities(self.records, data.get_today(), time_filter, source_filter)
                self.assertTrue(all(row["source"] == source_filter for row in rows)
                                if source_filter != "all" else rows)
                response = self.client.get("/my-plan", query_string={"time": time_filter,
                                                                      "source": source_filter})
                self.assertEqual(response.status_code, 200)
                self.assertIn(f'value="{time_filter}"'.encode(), response.data)
                self.assertIn(f'value="{source_filter}"'.encode(), response.data)
        accepted = [item for item in plan_activities(self.records, data.get_today(), "later", "health")]
        self.assertTrue(all(item["status"] == "accepted" for item in accepted))

    # Keep reusable templates separate from unique member assignment records.
    def test_activity_assignments_are_unique_and_meal_is_not_duplicated(self):
        assignments = self.records["activity_assignments"]
        ids = [item["id"] for item in assignments]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sum(item["title"] == "Practice a simple meal" for item in
                             plan_activities(self.records, data.get_today(), "today", "all")), 1)
        meal = next(item for item in self.records["activity_templates"]
                    if item["title"] == "Practice a simple meal")
        self.assertEqual(len(meal["steps"]), 6)
        self.assertEqual([item["label"] for item in meal["steps"][0]["choices"]],
                         ["Sandwich", "Oatmeal", "Salad", "Something else"])

    # Save a meal choice and make sure later instructions use the member's selection.
    def test_activity_choice_is_saved_and_used_in_later_steps(self):
        assignment = next(item for item in self.records["activity_assignments"]
                          if item.get("assigned_to") == "p1" and item.get("template_id") == "template-coach-01")
        response = self.client.post(f"/activity/{assignment['id']}?step=1",
                                    data={"action": "next", "choice": "oatmeal"})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(f"/activity/{assignment['id']}?step=2")
        self.assertIn(b"ingredients you need for Oatmeal", page.data)
        with self.client.session_transaction() as state:
            self.assertEqual(state["activity_responses"][assignment["id"]]["1"]["choice"], "oatmeal")
        export = self.client.get("/settings/export")
        self.assertIn(b'"responses"', export.data)
        self.assertIn(b'"choice": "oatmeal"', export.data)

    # Keep Home limited to the private summary, one clickable day timeline, and secondary climb/visit links.
    def test_member_home_is_simple_and_timeline_destinations_work(self):
        page = self.client.get("/today")
        self.assertEqual(page.status_code, 200)
        for label in [b"Good afternoon, Jordan.", b"Check In",
                      b"Pair noticed", b"Your week at a glance", b"Your Day", b"Now", b"Up Next",
                      b"Upcoming appointment", b"My Climb", b"data-demo-role=\"member\""]:
            self.assertIn(label, page.data)
        self.assertNotIn(b"Last Check In", page.data)
        self.assertNotIn(b"What feels like a good next step?", page.data)
        self.assertIn(b"day-timeline", page.data)

    # Keep sidebar and mobile member navigation in the approved order.
    def test_member_navigation_order_matches_across_screen_sizes(self):
        page = self.client.get("/today").data.decode()
        expected = ["Home", "Check In", "My Plan", "Health", "Patterns", "Appointments", "My Circle", "Settings"]
        sidebar = page.split('<nav aria-label="Pair member navigation">', 1)[1].split("</nav>", 1)[0]
        mobile = page.split('<nav class="mobile-role-nav"', 1)[1].split("</nav>", 1)[0]
        for nav in [sidebar, mobile]:
            positions = [nav.find(f">{label}</span>") for label in expected]
            self.assertTrue(all(position >= 0 for position in positions))
            self.assertEqual(positions, sorted(positions))

    # Preserve appointment answers when moving through the one-stage-at-a-time wizard.
    def test_appointment_wizard_steps_back_save_and_review_selected_items(self):
        self.assertEqual(self.client.get("/visit/primary?step=1").status_code, 200)
        response = self.client.post("/visit/primary?step=1", data={"reason": "Talk about my sleep",
                                 "appointment_on": data.get_today()})
        self.assertIn("step=2", response.headers["Location"])
        page = self.client.get("/visit/primary?step=2")
        self.assertIn(b"What Pair noticed", page.data)
        response = self.client.post("/visit/primary?step=2&item=0", data={"action": "include"})
        self.assertIn("item=1", response.headers["Location"])
        response = self.client.post("/visit/primary?step=2&item=1", data={"action": "leave_out"})
        self.assertIn("item=2", response.headers["Location"])
        item_count = int(re.search(rb"Item 1 of (\d+)", page.data).group(1))
        for item_index in range(2, item_count):
            response = self.client.post(f"/visit/primary?step=2&item={item_index}",
                                        data={"action": "leave_out"})
        self.assertIn("step=3", response.headers["Location"])
        response = self.client.post("/visit/primary?step=3", data={"communication": "Give me time to think",
                                 "accommodations": "Extra processing time"})
        self.assertIn("step=4", response.headers["Location"])
        response = self.client.post("/visit/primary?step=4", data={"questions": "Can you explain the next step?"})
        self.assertIn("/visit/primary/review", response.headers["Location"])
        review = self.client.get(response.headers["Location"])
        for label in [b"Step 5 of 5", b"What I would like to talk about", b"Left out",
                      b"Communication preferences", b"Can you explain the next step?", b"does not send packets"]:
            self.assertIn(label, review.data)
        invalid = self.client.post("/visit/primary/send", data={"recipient": "Dr. Patel",
                                    "expires_on": data.get_today()})
        self.assertEqual(invalid.status_code, 302)
        confirmed = self.client.post("/visit/primary/send", data={"recipient": "Dr. Patel",
                                      "expires_on": data.get_today(), "reviewed": "yes"})
        self.assertEqual(confirmed.status_code, 302)
        result = self.client.get(confirmed.headers["Location"])
        if result.status_code == 302:
            result = self.client.get(result.headers["Location"])
        self.assertIn(b"did not send or share the packet", result.data)
        self.assertEqual(self.client.post("/visit/primary?step=3", data={"action": "back"}).status_code, 302)
        with self.client.session_transaction() as state:
            self.assertTrue(state["visit_packet_drafts"]["p1"]["primary"]["changes"])
        response = self.client.post("/visit/primary?step=2&item=0", data={"action": "save"})
        self.assertIn("/health", response.headers["Location"])
        self.assertIn(b"Continue saved Primary care doctor draft", self.client.get("/visit").data)

    # Keep one member-authored visit topic and offer selectable, editable profession-based examples.
    def test_visit_topics_use_ai_or_built_in_guidance_without_personal_data(self):
        page = self.client.get("/visit/dietitian?step=1").data
        self.assertIn(b"What would you like to talk about at this visit?", page)
        self.assertIn(b"Not sure?</span>", page)
        self.assertIn(b">See common reasons for this type of visit</a>", page)
        self.assertNotIn(b"What would you like help with?", page)
        self.assertIn(b'id="common-reasons"', page)
        self.assertIn(b" hidden>", page)
        fallback = self.client.post("/visit/dietitian?step=1", data={"topic_action": "show",
                                                "reason": "My usual meals"}, follow_redirects=True)
        self.assertIn(b"Built-in suggestions", fallback.data)
        self.assertIn(b"Planning balanced meals", fallback.data)
        self.assertIn(b"dietitians-and-nutritionists.htm", fallback.data)
        self.assertIn(b"My usual meals", fallback.data)
        self.assertIn(b"class=\"visit-topic-choice\"", fallback.data)

        with patch("ai.os.getenv", return_value="demo-key"), patch(
                "ai.ask_claude", return_value='{"topics":["Daily routines","Nutrition questions","Food preferences"]}') as ask:
            ai_topics = pair.suggest_visit_topics("dietitian")
        self.assertEqual(ai_topics["source"], "ai")
        self.assertEqual(len(ai_topics["topics"]), 3)
        self.assertEqual(ai_topics["source_name"], "U.S. Bureau of Labor Statistics")
        self.assertEqual(ai_topics["reference"], "https://www.bls.gov/ooh/healthcare/dietitians-and-nutritionists.htm")
        self.assertNotIn("Jordan", ask.call_args.args[1])
        self.assertIn("dietitian", ask.call_args.args[1].lower())
        with patch("ai.os.getenv", return_value="demo-key"), patch(
                "ai.ask_claude", return_value='{"topics":["You have diabetes","Treatment plan","Question","Another"]}'):
            self.assertEqual(pair.suggest_visit_topics("dietitian")["source"], "rules")

    # Keep selected visit examples editable and preserve a phrase the member had typed independently.
    def test_visit_topic_selection_keeps_member_written_text_and_source_links(self):
        with patch.object(pair, "suggest_visit_topics", return_value={
                "topics": ["Planning balanced meals", "Food allergies or dietary needs"],
                "source": "ai", "source_name": "U.S. Bureau of Labor Statistics",
                "reference": "https://www.bls.gov/ooh/healthcare/dietitians-and-nutritionists.htm"}):
            opened = self.client.post("/visit/dietitian?step=1", data={"topic_action": "show",
                                             "reason": "My own note"}, follow_redirects=True)
        self.assertIn(b"AI-assisted suggestions", opened.data)
        self.assertIn(b'target="_blank" rel="noopener">U.S. Bureau of Labor Statistics</a>', opened.data)
        self.assertIn(b"value=\"Planning balanced meals\"", opened.data)
        source = open(os.path.join(pair.app.template_folder, "visit.html"), encoding="utf-8").read()
        self.assertIn("choice.dataset.addedByPair === 'yes'", source)
        self.assertIn("if (index >= 0) lines.splice(index, 1)", source)

        self.client.post("/visit/dietitian?step=1", data={"action": "continue", "reason": "Planning balanced meals\nMy own note",
                         "selected_topics": "Planning balanced meals", "topic_additions": ""})
        with self.client.session_transaction() as state:
            draft = state["visit_packet_drafts"]["p1"]["dietitian"]
            self.assertEqual(draft["reason"], "Planning balanced meals\nMy own note")
            self.assertEqual(draft["selected_topics"], ["Planning balanced meals"])

    # Check today's My Pace choice controls the number of plan activities without another selector.
    def test_my_pace_controls_plan_count_and_pause_can_return_explicitly(self):
        page = self.client.get("/my-plan")
        self.assertIn(b'<select id="plan-when" name="time"', page.data)
        self.assertIn(b'<option value="today" selected>Today</option>', page.data)
        self.assertIn(b'<select id="plan-from" name="source"', page.data)
        self.assertIn(b'<option value="all" selected>All</option>', page.data)
        expected_default = plan_activities(self.records, data.get_today(), "today", "all", {})
        self.assertEqual(page.data.count(b'class="card activity-card'), len(expected_default) + 1)
        self.assertNotIn(b"Save My Pace", page.data)
        self.assertNotIn(b"Show my full day", page.data)

        expected = {"one_small_step": 1, "few_manageable": 3, "pause": 0, "not_sure": 1}
        messages = {"one_small_step": "Based on your check-in, we\u2019re showing one activity at a time.",
                    "few_manageable": "Based on your check-in, we\u2019re showing a few activities.",
                    "pause": "You chose to pause. Return when you\u2019re ready.",
                    "not_sure": "We\u2019ll start with one activity."}
        for pace, count in expected.items():
            with self.client.session_transaction() as state:
                state["checkins"] = [{"person_id": "p1", "date": data.get_today(), "created_at": pace,
                                      "my_pace": pace, "manageability": pace}]
            page = self.client.get("/my-plan?time=this_week&source=all")
            self.assertEqual(page.data.count(b'class="card activity-card'), count, pace)
            self.assertIn(messages[pace].encode("utf-8"), page.data)
            self.assertIn(b"Change in Check In", page.data)
            if pace == "pause":
                self.assertIn(b"Return when ready", page.data)
                resumed = self.client.get("/my-plan?time=this_week&source=all&ready=yes")
                self.assertEqual(resumed.data.count(b'class="card activity-card'), 1)

    # One-activity views advance to the next incomplete item and name the all-complete state.
    def test_one_activity_view_advances_after_completion_and_handles_empty_view(self):
        with self.client.session_transaction() as state:
            state["checkins"] = [{"person_id": "p1", "date": data.get_today(), "created_at": "10:00",
                                  "my_pace": "one_small_step"}]
        with pair.app.test_request_context():
            daily_records = {**self.records,
                             "health_follow_ups": pair.plan_health_follow_ups(
                                 {"id": "p1"}, self.records, data.get_today())}
        matches = plan_activities(daily_records, data.get_today(), "today", "all", {})
        self.assertGreaterEqual(len(matches), 2)
        first, second = matches[:2]
        first_activity = next(item for item in activity_assignments(self.records, "p1")
                              if item["id"] == first["id"])
        response = self.client.post(f"/activity/{first['id']}?step={len(first_activity['steps'])}",
                                    data={"action": "next"})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response.headers["Location"]).data
        self.assertIn(f"{first['title']} completed.".encode(), page)
        shown = re.findall(rb'<article id="([^"]+)" class="card activity-card', page)
        self.assertEqual(len(shown), 1)
        self.assertNotEqual(shown[0].decode(), first["id"])
        self.assertIn(b"Clean the kitchen", page)

        with self.client.session_transaction() as state:
            state["activity_progress"] = {item["id"]: {"status": "completed"} for item in matches}
            state["health_plan_states"] = {"p1": {item["id"]: {"status": "completed"}
                                                   for item in matches if item["source"] == "health"}}
            state["routine_occurrences"] = {"p1": {
                f"routine-{routine['routine_id']}@{data.get_today()}": {"status": "completed"}
                for routine in data.get_routines("p1")
                if routine["frequency"] == "daily" or
                date.fromisoformat(data.get_today()).strftime("%A") in routine["days"]}}
        page = self.client.get("/my-plan").data
        self.assertIn(b"You completed everything in this view.", page)
        self.assertNotIn(b'class="card activity-card', page)

    # The two dropdown filters update server results and preserve both selections.
    def test_plan_dropdown_filters_update_activity_results(self):
        page = self.client.get("/my-plan?time=this_week&source=coach").data
        self.assertIn(b'<option value="this_week" selected>This Week</option>', page)
        self.assertIn(b'<option value="coach" selected>From My Coach</option>', page)
        expected = plan_activities(self.records, data.get_today(), "this_week", "coach", {})
        self.assertEqual(page.count(b'class="card activity-card'), len(expected))
        stylesheet = open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8").read()
        self.assertIn(".plan-filter-selects { grid-template-columns: 1fr; }", stylesheet)

    # Put a consistent pictogram beside every access label on Circle.
    def test_circle_access_levels_have_pictograms_and_text(self):
        page = self.client.get("/circle")
        self.assertEqual(page.status_code, 200)
        for label in [b"Just in my circle", b"Cheers me on", b"Weekly summary",
                      b"Wellness details", b"Health summary"]:
            self.assertIn(label, page.data)
        self.assertIn(b"access-pictogram", page.data)
        self.assertIn(b"One-time snapshot", page.data)
        self.assertIn(b"Packet access is time limited", page.data)

    # Explain pattern charts with pictograms, source names, plain-language comparisons and a legend.
    def test_patterns_explain_sources_and_usual_ranges(self):
        page = self.client.get("/patterns")
        self.assertEqual(page.status_code, 200)
        for label in [b"Usual range", b"Last 5 days", b"Your usual average",
                      b"Last 5-day average", b"Source: My phone", b"Movement",
                      b"not its cause or a diagnosis", b"Recent private check-ins", b"Private to you"]:
            self.assertIn(label, page.data)
        self.assertIn(b"pattern-pictogram", page.data)

    # Keep coach views limited to activity progress and to members who shared wellness access.
    def test_coach_scope_excludes_private_and_health_information(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "coach"
            state["checkins"] = [{"person_id": "p1", "note": "PRIVATE_CHECKIN_SENTINEL"}]
            state["visit_entries"] = {"p1": [{"label": "health", "value": "PRIVATE_HEALTH_SENTINEL"}]}
        response = self.client.get("/coach/learners/p1")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"PRIVATE_CHECKIN_SENTINEL", response.data)
        self.assertNotIn(b"PRIVATE_HEALTH_SENTINEL", response.data)
        self.assertEqual(self.client.get("/coach/learners/p4").status_code, 404)

    # Require opening a consented learner profile before the coach assigns a library activity.
    def test_coach_must_open_learner_before_assignment(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "coach"
        activity_id = self.records["activity_templates"][0]["id"]
        url = "/coach/learners/p1/assign"
        self.assertEqual(self.client.post(url, data={"activity_id": activity_id}).status_code, 403)
        self.client.get("/coach/learners/p1")
        self.assertEqual(self.client.post(url, data={"activity_id": activity_id}).status_code, 302)

    # Keep packet review explicit, validate its recipient and expiry, and never imply delivery.
    def test_appointment_packet_review_and_share_gates(self):
        review_url = "/visit/primary/review"
        self.assertEqual(self.client.post(review_url, data={"reason": "A member-selected reason",
                         "appointment_on": data.get_today(), "questions": "What should I ask?",
                         "selected": "0"}).status_code, 302)
        page = self.client.get(review_url)
        self.assertEqual(page.status_code, 200)
        send_url = "/visit/primary/send"
        invalid = {"recipient": "Mom", "expires_on": data.get_today(), "reviewed": "yes"}
        self.assertEqual(self.client.post(send_url, data=invalid).status_code, 302)
        self.assertEqual(self.client.post(send_url, data={"recipient": "Dr. Patel",
                         "expires_on": data.get_today()}).status_code, 302)
        packet_ids = [item["id"] for item in pair.professional_authorized_packets()]
        valid = {"recipient": "Dr. Patel", "expires_on": data.get_today(), "reviewed": "yes"}
        response = self.client.post(send_url, data=valid)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/visit/primary", response.headers["Location"])
        self.assertEqual([item["id"] for item in pair.professional_authorized_packets()], packet_ids)
        with self.client.session_transaction() as state:
            self.assertNotIn("circle_shared_snapshots", state)

    # Show healthcare professionals only the fixture packets with a current member authorization.
    def test_professional_packet_scope_and_member_health_boundary(self):
        with self.client.session_transaction() as state:
            state["demo_role"] = "healthcare"
        packets = pair.professional_authorized_packets()
        self.assertTrue(packets)
        page = self.client.get("/professional/packets")
        self.assertEqual(page.status_code, 200)
        self.assertIn(packets[0]["id"].encode(), page.data)
        self.assertEqual(self.client.get("/professional/packets/packet-completed").status_code, 404)
        with self.client.session_transaction() as state:
            state["demo_role"] = "member"
            state["person_id"] = "p2"
        member_page = self.client.get("/health/packets")
        self.assertEqual(member_page.status_code, 200)
        self.assertNotIn(b"packet-upcoming", member_page.data)
        self.assertNotIn(self.records["appointment_packets"][0]["appointment_type"].encode(), member_page.data)

    # Put only an accepted healthcare proposal in My Plan while it remains in Health.
    def test_accepting_health_next_step_adds_it_to_plan(self):
        action = next(item for item in self.records["health_follow_ups"] if item["id"] == "follow-up-01")
        response = self.client.post(f"/health/next-steps/{action['id']}", data={
            "choice": "accept", "when": data.get_today(), "reminder_time": "20:00"})
        self.assertEqual(response.status_code, 302)
        plan_page = self.client.get("/my-plan", query_string={"time": "today", "source": "health"})
        health_page = self.client.get("/health/next-steps")
        health_landing = self.client.get("/health")
        self.assertIn("Record today’s sleep".encode(), plan_page.data)
        self.assertIn(action["instruction"].encode(), health_page.data)
        self.assertIn(b"Accepted", health_page.data)
        self.assertIn(b"Daily for seven days", health_landing.data)
        self.assertIn(b"View in My Plan", health_landing.data)
        self.assertIn(b"Day 1 of 7", plan_page.data)

    # Render the acceptance action clearly and confirm it saves the member-selected schedule.
    def test_health_next_steps_accept_button_label_and_schedule_action(self):
        page = self.client.get("/health/next-steps").data
        self.assertIn(b"<summary class=\"btn-primary\">Accept and add to My Plan</summary>", page)
        self.assertIn(b">Decline</button>", page)
        css = open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8").read()
        self.assertIn(".health-schedule-review button.btn-primary", css)
        self.assertIn("color: #FFFFFF", css)
        response = self.client.post("/health/next-steps/follow-up-pressure", data={
            "choice": "accept", "when": data.get_today(), "frequency": "once", "reminder_time": "09:00"})
        self.assertEqual(response.status_code, 302)
        plan = self.client.get("/my-plan", query_string={"time": "today", "source": "health"}).data
        self.assertIn(b"Record blood-pressure reading", plan)
        with self.client.session_transaction() as state:
            self.assertEqual(state["health_plan_states"]["p1"]["follow-up-pressure"]["schedule"]["frequency"], "once")
            self.assertEqual(state["health_plan_states"]["p1"]["follow-up-pressure"]["schedule"]["reminder_time"], "09:00")

    # Verify accepted follow-ups appear once, while declined and proposed steps stay out of My Plan.
    def test_health_followups_enter_plan_only_once_after_acceptance(self):
        proposed = [item for item in self.records["health_follow_ups"] if item["status"] == "proposed"]
        page = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        self.assertNotIn(proposed[0]["instruction"].encode(), page.data)
        self.assertNotIn(proposed[1]["instruction"].encode(), page.data)
        self.client.post(f"/health/next-steps/{proposed[0]['id']}", data={
            "choice": "accept", "when": data.get_today(), "reminder_time": "20:00"})
        page = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        self.assertNotIn(proposed[0]["instruction"].encode(), page.data)
        today_page = self.client.get("/my-plan", query_string={"time": "today", "source": "health"})
        self.assertIn("Record today’s sleep".encode(), today_page.data)
        self.assertIn(f"/health/next-steps#{proposed[0]['id']}".encode(), today_page.data)
        self.client.post(f"/health/next-steps/{proposed[1]['id']}", data={"choice": "decline"})
        self.assertNotIn(proposed[1]["instruction"].encode(), self.client.get(
            "/my-plan", query_string={"time": "later", "source": "health"}).data)

    # Keep proposed instructions out of the plan until the member explicitly accepts or declines.
    def test_proposed_instructions_need_member_choice_and_selected_frequency(self):
        before = self.client.get("/my-plan", query_string={"time": "this_week", "source": "health"})
        self.assertNotIn(b"Record blood-pressure reading", before.data)
        pressure = next(item for item in self.records["health_follow_ups"] if item["id"] == "follow-up-pressure")
        self.client.post("/health/next-steps/follow-up-pressure", data={
            "choice": "accept", "when": data.get_today(), "reminder_time": "09:00"})
        self.assertIn(b"Choose a reminder schedule", self.client.get("/health/next-steps").data)
        with self.client:
            self.client.get("/health")
            self.assertEqual(next(item for item in pair.health_follow_ups_for(pair.current_person())
                                  if item["id"] == pressure["id"])["status"], "proposed")
        self.client.post("/health/next-steps/follow-up-pressure", data={
            "choice": "accept", "when": data.get_today(), "frequency": "daily",
            "reminder_time": "09:00"})
        plan = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        self.assertIn(b"Record blood-pressure reading", plan.data)
        self.assertIn(b"09:00", plan.data)
        rows = self.plan_health_rows(data.get_today())
        prep = next(item for item in rows if item["id"] == "follow-up-pressure-bring")
        appointment = pair.next_appointment_date(self.records)
        self.assertEqual(prep["due_on"], (date.fromisoformat(appointment) - timedelta(days=1)).isoformat())
        self.assertEqual(prep["schedule"]["reminder_time"], "09:00")
        today = date.fromisoformat(data.get_today())
        prep_day = date.fromisoformat(prep["due_on"])
        week_end = today + timedelta(days=6 - today.weekday())
        when = ("today" if prep_day == today else "tomorrow" if prep_day == today + timedelta(days=1)
                else "this_week" if prep_day <= week_end else "later")
        plan_rows = plan_activities({**self.records, "activity_assignments": [], "health_follow_ups": rows},
                                    data.get_today(), when, "health")
        self.assertTrue(any(item["id"] == "follow-up-pressure-bring" for item in plan_rows))

    # Create exactly seven member-selected sleep-recording occurrences with editable reminder times.
    def test_sleep_recording_creates_seven_daily_occurrences_and_stops(self):
        today = date.fromisoformat(data.get_today())
        self.client.post("/health/next-steps/follow-up-01", data={
            "choice": "accept", "when": today.isoformat(), "reminder_time": "20:00"})
        occurrences = self.plan_health_rows(today.isoformat())
        sleep = [item for item in occurrences if item.get("health_action_id") == "follow-up-01"]
        self.assertEqual(len(sleep), 7)
        self.assertEqual(sleep[2]["progress_label"], "Day 3 of 7")
        self.assertEqual(sleep[0]["schedule"]["reminder_time"], "20:00")
        self.client.post(f"/my-plan/health-action/follow-up-01@{today.isoformat()}", data={
            "choice": "done", "health_action_id": "follow-up-01"})
        self.client.post(f"/my-plan/health-action/follow-up-01@{today.isoformat()}", data={
            "choice": "done", "health_action_id": "follow-up-01"})
        with self.client.session_transaction() as state:
            self.assertEqual(len(state["health_activity_completions"]["p1"]), 1)
        tomorrow = self.plan_health_rows((today + timedelta(days=1)).isoformat())
        self.assertFalse(any(item["id"] == f"follow-up-01@{today.isoformat()}" for item in tomorrow))
        self.assertTrue(any(item["id"] == f"follow-up-01@{(today + timedelta(days=1)).isoformat()}"
                            for item in tomorrow))
        final_day = self.plan_health_rows((today + timedelta(days=7)).isoformat())
        self.assertFalse(any(item.get("health_action_id") == "follow-up-01" for item in final_day))

    # Let the member change the recurring walking reminder and complete one occurrence per date.
    def test_daily_walking_uses_saved_time_and_reappears_next_day(self):
        today = date.fromisoformat(data.get_today())
        url = f"/my-plan/health-action/follow-up-demo-today@{today.isoformat()}"
        self.client.post(url, data={"choice": "save_time", "health_action_id": "follow-up-demo-today",
                                   "reminder_time": "07:30"})
        home = self.client.get("/today")
        plan = self.client.get("/my-plan", query_string={"time": "today", "source": "health"})
        self.assertIn(b"7:30 AM", home.data)
        self.assertIn(b"7:30 AM", plan.data)
        self.client.post(url, data={"choice": "done", "health_action_id": "follow-up-demo-today"})
        tomorrow = self.plan_health_rows((today + timedelta(days=1)).isoformat())
        self.assertTrue(any(item["id"] == f"follow-up-demo-today@{(today + timedelta(days=1)).isoformat()}"
                            for item in tomorrow))

    # Mark due activities inline without separate reminder cards or repeated disclaimers.
    def test_due_activity_badge_is_inline_on_home_and_plan(self):
        activity = {"title": "Record today’s sleep", "due_on": data.get_today(),
                    "id": "sleep-today", "schedule": {"reminder_time": "09:00"}, "status": "accepted"}
        self.assertEqual(pair.due_in_app_reminders([activity], "08:59"), [])
        self.assertEqual(pair.due_in_app_reminders([activity], "09:00"), [activity])
        self.assertEqual(pair.due_in_app_reminders([{**activity, "status": "completed"}], "09:00"), [])
        self.client.post("/health/next-steps/follow-up-01", data={
            "choice": "accept", "when": data.get_today(), "reminder_time": "00:01"})
        home = self.client.get("/today").data
        plan = self.client.get("/my-plan").data
        self.assertIn(b"Due now", home)
        self.assertIn(b"Due now", plan)
        for page in [home, plan]:
            self.assertNotIn(b"In-app demonstration reminder", page)
            self.assertNotIn(b"No message was sent outside Pair", page)
            self.assertNotIn(b'class="in-app-reminder"', page)

    # Keep pausing, rescheduling, and removing from My Plan separate from the Health record.
    def test_health_plan_controls_preserve_the_health_history(self):
        action = next(item for item in self.records["health_follow_ups"] if item["status"] == "accepted")
        url = f"/my-plan/health-action/{action['id']}"
        today = data.get_today()
        with self.client.session_transaction() as state:
            state["health_plan_states"] = {"p1": {action["id"]: {
                "status": "active", "scheduled_for": today,
                "schedule": {"date": today, "label": "Member-selected date"}}}}
        home = self.client.get("/today")
        self.assertIn(f"/my-plan?time=today&amp;source=all&amp;activity={action['id']}#{action['id']}".encode(), home.data)
        self.client.post(url, data={"choice": "pause"})
        paused = self.client.get("/my-plan", query_string={"time": "this_week", "source": "health"})
        self.assertIn(b"Paused", paused.data)
        self.assertIn(action["instruction"].encode(), self.client.get("/today").data)
        self.assertIn(action["instruction"].encode(), self.client.get("/health/next-steps").data)
        self.client.post(url, data={"choice": "reschedule", "schedule": "2026-11-20"})
        moved = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        self.assertIn(b"November 20", moved.data)
        self.client.post(url, data={"choice": "remove"})
        self.assertNotIn(action["instruction"].encode(), self.client.get(
            "/my-plan", query_string={"time": "later", "source": "health"}).data)
        self.assertIn(action["instruction"].encode(), self.client.get("/health/next-steps").data)
        self.client.post(url, data={"choice": "add"})
        self.assertIn(action["instruction"].encode(), self.client.get(
            "/my-plan", query_string={"time": "later", "source": "health"}).data)

    # Verify exact fictional medication details, one-time reminder choice, and private reminder responses.
    def test_medication_view_preserves_source_text_and_remains_private(self):
        medication = self.records["medications"][0]
        with patch.object(pair, "explain_week", side_effect=AssertionError("Medication fields must not use AI")):
            page = self.client.get("/health/medications")
        self.assertEqual(page.status_code, 200)
        for field in ["medication_name", "dose_as_entered", "time_as_entered", "instruction",
                      "instruction_source", "entered_by"]:
            self.assertIn(medication[field].encode(), page.data)
        self.assertIn(b"Pair displays the instruction as entered", page.data)
        url = "/health/medications"
        self.client.post(url, data={"action": "reminder_choice", "reminders": "yes"})
        self.client.post(url, data={"action_id": medication["id"], "action": "skip"})
        self.assertIn(b"Skip", self.client.get(url).data)
        for role, route in [("coach", url), ("trusted", url), ("admin", url), ("healthcare", url)]:
            with self.client.session_transaction() as state:
                state["demo_role"] = role
            self.assertNotEqual(self.client.get(route).status_code, 200)
        with self.client.session_transaction() as state:
            state["demo_role"] = "admin"
        self.assertNotEqual(self.client.get("/my-plan").status_code, 200)

    # Ensure clinician-only proposals remain unavailable to coaches and trusted people.
    def test_non_clinicians_cannot_create_health_followups(self):
        for role in ["coach", "trusted", "admin"]:
            with self.client.session_transaction() as state:
                state["demo_role"] = role
            self.assertNotEqual(self.client.post("/professional/next-steps").status_code, 200)

    # Keep only one pattern chart visible while exposing all six named choices.
    def test_patterns_progressively_disclose_one_selected_signal(self):
        page = self.client.get("/patterns?pattern=sleep")
        for label in [b"Sleep", b"Movement", b"Screen Use", b"Time Away from Home",
                      b"Blood Sugar", b"Heart Rate", b"Choose a health pattern"]:
            self.assertIn(label, page.data)
        self.assertEqual(page.data.count(b'<svg class="chart"'), 1)
        self.assertIn(b'viewBox="0 0 600 280"', page.data)
        css = open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8").read()
        self.assertIn(".pattern-card .chart { max-height: 26.25rem; }", css)
        self.assertIn(".pattern-card .chart { max-height: 14rem; }", css)
        self.assertIn("width: 100%;\n  height: auto;", css)
        self.assertIn(b"class=\"pattern-tile is-selected", page.data)
        screen = self.client.get("/patterns?pattern=screen")
        self.assertEqual(screen.data.count(b'<svg class="chart"'), 1)
        self.assertIn(b"Phone pickups", screen.data)
        with self.client.session_transaction() as state:
            state["person_id"] = "p2"
        body = self.client.get("/patterns?pattern=blood_sugar")
        self.assertIn(b"Glucose monitor (CGM)", body.data)
        self.assertIn(b"mg/dL", body.data)
        self.assertEqual(body.data.count(b'<svg class="chart"'), 1)

    # Keep device details collapsed in selectable rows and preserve pair and disconnect actions.
    def test_device_sources_use_compact_details_and_keep_pairing_actions(self):
        page = self.client.get("/devices")
        for text in [b"Connected devices", b"Available to connect", b"Smart washing machine",
                     b"Pair reads:", b"Privacy:", b"Connect"]:
            self.assertIn(text, page.data)
        self.assertIn(b'<details class="source-option">', page.data)
        self.assertNotIn(b'<details class="source-option" open', page.data)
        response = self.client.post("/devices/pair/Mattress sleep sensor")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertTrue(state["paired"]["p1"]["Mattress sleep sensor"])
        response = self.client.post("/devices/stop/Mattress sleep sensor")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertFalse(state["paired"]["p1"]["Mattress sleep sensor"])

    # Exercise the main activity presentation buttons and retain one-step navigation.
    def test_activity_buttons_keep_the_route_working(self):
        activity_id = self.records["activity_assignments"][0]["id"]
        url = f"/activity/{activity_id}"
        for action in ["break", "help", "help_cancel", "help_send", "next", "back"]:
            response = self.client.post(url, data={"step": "1", "action": action})
            self.assertEqual(response.status_code, 302, action)
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Learning goal", page.data)
        for control in [b"Show Fewer Words", b"Show an Example", b"Explain Differently",
                        b"View Original", b"Hide Pictures"]:
            self.assertNotIn(control, page.data)
        self.assertLess(page.data.index(b"Next step"), page.data.index(b"Read Aloud"))

    # Exercise mood choices, display settings, and every visual theme without third-party calls.
    def test_checkin_theme_and_motion_controls(self):
        checkin_page = self.client.get("/checkin")
        for label in [b"Calm", b"Okay", b"Tired", b"Worried", b"Overwhelmed",
                      b"Quiet Break", b"Message Someone", b"Nothing Right Now"]:
            self.assertIn(label, checkin_page.data)
        for removed in [b"Smaller Step", b"Read Aloud", b"Reduce Screen Content"]:
            self.assertNotIn(removed, checkin_page.data)
        for display in ["pictures_words", "words_only", "pictures_first"]:
            response = self.client.post("/settings?section=appearance", data={
                "action": "save_member_preferences", "density": "comfortable",
                "picture_preference": display, "speech_rate": "1"})
            self.assertEqual(response.status_code, 302)
        page = self.client.get("/checkin").data
        submission_id = re.search(rb'name="submission_id" value="([^"]+)"', page).group(1).decode()
        response = self.client.post("/checkin", data={"action": "save", "submission_id": submission_id,
                                    "feeling": "Okay", "help_choice": "quiet_break"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/quiet-break?activity_id=quiet-break-"))
        saved_page = self.client.get(response.headers["Location"]).data
        self.assertIn(b"Take a quiet break", saved_page)
        self.assertNotIn(b"Display preferences", saved_page)
        for theme in pair.THEMES:
            self.assertEqual(self.client.post("/theme", data={"theme": theme}).status_code, 302)
            page = self.client.get("/settings")
            self.assertIn(f'data-theme="{theme}"'.encode(), page.data)
        for motion in pair.CELEBRATIONS:
            self.assertEqual(self.client.post("/celebrations", data={"celebrations": motion}).status_code, 302)

    # Keep the Check In introduction brief and offer only three outcome-specific help choices.
    def test_checkin_introduction_and_help_choices_are_simplified(self):
        page = self.client.get("/checkin").data
        heading = page.index(b"<h1>Check In</h1>")
        form = page.index(b'<form method="post" class="card checkin-form')
        self.assertLess(heading, form)
        self.assertNotIn(b"Your check-in and optional note are private by default", page)
        for label in [b"Quiet Break", b"Message Someone", b"Nothing Right Now"]:
            self.assertIn(label, page)
        for label in [b"Smaller Step", b"Read Aloud", b"Reduce Screen Content"]:
            self.assertNotIn(label, page)
        self.assertEqual(page.count(b'name="help_choice"'), 3)

    # Route a selected Quiet Break to its timer-free screen, then resume at the next plan activity.
    def test_quiet_break_is_simple_and_returns_to_next_incomplete_plan_item(self):
        form = self.client.get("/checkin").data
        submission = re.search(rb'name="submission_id" value="([^"]+)"', form).group(1).decode()
        before = plan_activities(self.records, data.get_today(), "today", "all", {})
        next_activity = next(item for item in before if item["status"] != "completed")
        response = self.client.post("/checkin", data={"action": "save", "submission_id": submission,
                                    "manageability": "one_small_step", "help_choice": "quiet_break"})
        self.assertTrue(response.headers["Location"].startswith("/quiet-break?activity_id=quiet-break-"))
        page = self.client.get(response.headers["Location"]).data
        for label in [b"Take a quiet break", b"Find a quiet or comfortable place. Take a few minutes to rest or do something calming.",
                      b"Done", b"Back to My Plan"]:
            self.assertIn(label, page)
        for removed in [b"Step 1 of 2", b"Progressbar", b"Next step", b"Previous step", b"I need a break",
                        b"I need help", b"Easy", b"Difficult", b"Learning goal", b"Assigned by", b"20 minutes"]:
            self.assertNotIn(removed, page)
        with self.client.session_transaction() as state:
            self.assertEqual(state.get("activity_progress", {}), {})
        done = self.client.post(response.headers["Location"], data={"action": "done"})
        self.assertIn("/my-plan", done.headers["Location"])
        plan = self.client.get(done.headers["Location"]).data
        self.assertIn(b"Take a quiet break completed.", plan)
        visible = re.findall(rb'<article id="([^"]+)" class="card activity-card', plan)
        self.assertEqual(len(visible), 1)
        self.assertNotEqual(visible[0].decode(), next_activity["id"])
        self.assertNotIn(b"Take a quiet break</h2>", plan)
        with self.client.session_transaction() as state:
            self.assertEqual(len(state["quiet_break_completions"]), 1)
            self.assertEqual(state["quiet_break_completions"][0]["person_id"], "p1")

    # Keep one routine definition while marking only its selected daily occurrence complete.
    def test_daily_routine_occurrence_repeats_without_double_counting(self):
        today = data.get_today()
        next_day = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
        before = self.client.get("/my-plan?time=today&source=all").data
        self.assertIn(b"Clean the kitchen", before)
        self.assertIn(b"Added by Mom", before)
        with self.client:
            self.client.get("/my-plan")
            routines = pair.routines_for(pair.current_person())
        index = next(i for i, routine in enumerate(routines) if routine["routine"] == "Clean the kitchen")
        done = self.client.post(f"/routines/{index}/finish", data={"occurrence": today})
        with self.client.session_transaction() as state:
            items = state["routine_occurrences"]["p1"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[f"routine-clean-kitchen@{today}"]["status"], "completed")
        page = self.client.get("/my-plan?time=today&source=all").data
        self.assertIn(b"This occurrence is complete", page)
        with patch.object(data, "get_today", return_value=next_day):
            following = self.client.get("/my-plan?time=today&source=all").data
        self.assertIn(f"routine-clean-kitchen@{next_day}".encode(), following)

    # A member can mark a timed walk done without starting its optional countdown.
    def test_timed_walk_done_without_start_counts_only_once(self):
        today = data.get_today()
        occurrence = f"follow-up-demo-today@{today}"
        self.client.post(f"/my-plan/health-action/{occurrence}", data={"choice": "done"})
        self.client.post(f"/my-plan/health-action/{occurrence}", data={"choice": "done"})
        with self.client.session_transaction() as state:
            self.assertEqual(len(state["health_activity_completions"]["p1"]), 1)
            self.assertEqual(state["health_activity_completions"]["p1"][occurrence]["date"], today)

    # Confirm reset clears progress and preferences while leaving the selected demo identity intact.
    def test_demo_reset_restores_session_defaults_and_fixtures(self):
        with self.client.session_transaction() as state:
            state["activity_progress"] = {"sample": {"status": "completed"}}
            state["member_preferences"] = {"p1": {"density": "compact"}}
            state["daily_summits"] = {"p1": [data.get_today()]}
        response = self.client.post("/settings/reset-demo", data={"confirm_reset": "yes"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertEqual(state["person_id"], "p1")
            self.assertEqual(state["demo_role"], "member")
            self.assertNotIn("activity_progress", state)
            self.assertNotIn("daily_summits", state)
        with self.client:
            self.client.get("/settings")
            self.assertEqual(pair.member_preferences("p1")["density"], "comfortable")

    # Keep today's climb sourced from the same activity set shown in the member's Plan.
    def test_today_climb_and_home_share_plan_progress_source(self):
        page = self.client.get("/my-plan?time=today&source=all").data
        plan_count = page.count(b'class="card activity-card')
        home = self.client.get("/today").data
        climb = self.client.get("/climb").data
        self.assertIn(f"0 of {plan_count} activities completed".encode(), home)
        self.assertIn(f"0 of {plan_count} activities completed".encode(), climb)
        self.assertEqual(climb.count(b'class="flag open'), plan_count)
        self.assertNotIn("Today’s activities</h2>".encode(), climb)

    # Award one weekly summit entry only when the last current-day activity is completed.
    def test_daily_summit_is_recorded_once_for_a_completed_today_item(self):
        person = {"id": "p1"}
        with pair.app.test_request_context():
            with patch.object(pair, "climb_today_activities", return_value=[
                    {"id": "today-item", "status": "completed"}]):
                pair.record_plan_completion(person, "Today item", "today-item")
                pair.record_plan_completion(person, "Today item", "today-item")
                self.assertEqual(pair.session["daily_summits"]["p1"], [data.get_today()])
                self.assertTrue(pair.session["plan_completion_notices"]["p1"]["summit"])
            with patch.object(pair, "climb_today_activities", return_value=[
                    {"id": "today-item", "status": "completed"}]):
                pair.record_plan_completion(person, "Future item", "future-item")
                self.assertFalse(pair.session["plan_completion_notices"]["p1"]["summit"])
                self.assertEqual(pair.session["daily_summits"]["p1"], [data.get_today()])

    # Let the member choose a Circle contact and prepare a demo-only message without external delivery.
    def test_message_someone_opens_circle_and_nothing_now_adds_no_action(self):
        form = self.client.get("/checkin").data
        submission = re.search(rb'name="submission_id" value="([^"]+)"', form).group(1).decode()
        response = self.client.post("/checkin", data={"action": "save", "submission_id": submission,
                                    "help_choice": "message_someone"})
        self.assertEqual(response.headers["Location"], "/circle/message")
        page = self.client.get(response.headers["Location"]).data
        self.assertIn(b"Who would you like to message?", page)
        self.assertIn(b"Choose a person in My Circle", page)
        self.assertIn(b"Marisol Reyes", page)
        self.assertIn(b'name="message"', page)
        self.assertIn(b"This prototype does not send a real message", page)
        self.assertNotIn(b"WhatsApp", page)
        sent = self.client.post("/circle/message", data={"recipient": "Marisol Reyes",
                                     "message": "Thinking of you."})
        self.assertEqual(sent.status_code, 302)
        self.assertIn(b"No real message was sent", self.client.get(sent.headers["Location"]).data)

        with self.client.session_transaction() as state:
            state["activity_progress"] = {"before": {"status": "active"}}
            state["health_plan_states"] = {"p1": {"before": {"status": "active"}}}
        form = self.client.get("/checkin").data
        submission = re.search(rb'name="submission_id" value="([^"]+)"', form).group(1).decode()
        response = self.client.post("/checkin", data={"action": "save", "submission_id": submission,
                                    "help_choice": "nothing_now"})
        self.assertIn("/checkin?result=", response.headers["Location"])
        self.client.get(response.headers["Location"])
        with self.client.session_transaction() as state:
            self.assertEqual(state["activity_progress"], {"before": {"status": "active"}})
            self.assertEqual(state["health_plan_states"], {"p1": {"before": {"status": "active"}}})
            self.assertNotIn("quiet_break_completions", state)

    # Hide redundant activity controls and show the single-screen presentation for assigned breaks.
    def test_assigned_quiet_break_is_not_a_learning_sequence(self):
        page = self.client.get("/activity/assignment-wellness-demo-tomorrow")
        self.assertEqual(page.status_code, 200)
        for label in [b"Take a quiet break", b"Find a quiet or comfortable place.", b"Done", b"Back to My Plan"]:
            self.assertIn(label, page.data)
        for removed in [b"Step 1 of 2", b"Next step", b"Previous step", b"I need a break",
                        b"I need help", b"Easy", b"Difficult", b"Learning goal", b"Assigned by", b"20 minutes"]:
            self.assertNotIn(removed, page.data)
        response = self.client.post("/activity/assignment-wellness-demo-tomorrow", data={"action": "done"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertEqual(state["activity_progress"]["assignment-wellness-demo-tomorrow"]["status"], "completed")

    # Show Help only for coach-assigned activities and hide Read Aloud when the member disables it.
    def test_activity_support_controls_match_the_activity_and_settings(self):
        coach_activity = self.client.get("/activity/assignment-coach-01").data
        member_activity = self.client.get("/activity/assignment-member-01").data
        self.assertIn(b"I need help", coach_activity)
        self.assertNotIn(b"I need help", member_activity)
        self.assertIn(b"Read Aloud", member_activity)
        self.client.post("/settings?section=appearance", data={"action": "save_member_preferences",
                         "density": "comfortable", "picture_preference": "pictures_words", "speech_rate": "1"})
        no_read_aloud = self.client.get("/activity/assignment-coach-01").data
        self.assertNotIn(b"Read Aloud", no_read_aloud)

    # Keep every check-in question optional and allow an empty private entry to be saved.
    def test_ema_questions_can_all_be_skipped_without_a_score(self):
        page = self.client.get("/checkin")
        self.assertIn(b"<strong>My Pace</strong><br>How manageable does today feel right now?", page.data)
        self.assertNotIn(b"Display preferences", page.data)
        self.assertNotIn(b"Your check-in and optional note are private by default", page.data)
        self.assertIn(b"Appearance and accessibility", self.client.get("/settings?section=appearance").data)
        self.assertIn(b"data-disable-repeat", page.data)
        with open(os.path.join(pair.app.static_folder, "js", "main.js"), encoding="utf-8") as script:
            self.assertIn('form.dataset.submitted = "yes"', script.read())
        form = page.data.split(b'class="card checkin-form', 1)[1].split(b"</form>", 1)[0]
        self.assertNotIn(b" required", form)
        self.assertIn(b"Skip", form)
        self.assertEqual(self.client.get("/today").status_code, 200)
        with self.client.session_transaction() as state:
            self.assertEqual(state.get("checkins", []), [])
        submission_id = re.search(rb'name="submission_id" value="([^"]+)"', page.data).group(1).decode()
        result = self.client.post("/checkin", data={"action": "save", "submission_id": submission_id})
        self.assertEqual(result.status_code, 302)
        saved = self.client.get(result.headers["Location"]).data
        self.assertIn(b"Thank you for checking in.", saved)
        self.assertIn(b"Continue to My Plan", saved)
        self.assertIn(b"Change my choice", saved)
        confirmation = saved.split(b'<section class="card soft-card"', 1)[1].split(b"</section>", 1)[0]
        self.assertNotIn(b"You can decide when you are ready", confirmation)
        self.assertNotIn(b"private by default", confirmation)
        self.assertNotIn(b"Take it one small step at a time", confirmation)
        self.assertIn(b"Private check-in history", saved)
        self.assertNotIn(b"%", saved)
        self.assertNotIn(b"readiness score", saved.lower())
        with self.client.session_transaction() as state:
            checkin = state["checkins"][-1]
            self.assertEqual(checkin["visibility"], "private")
            self.assertTrue(checkin["created_at"])
            self.assertEqual(checkin["manageability"], "")
            self.assertEqual(checkin["my_pace"], "")
        climb = self.client.get("/climb").data
        self.assertNotIn(b'<ul class="goal-list">', climb)
        self.assertIn(b'class="flag open', climb)

    # Keep the confirmation minimal and the complete responses inside collapsed private history.
    def test_ema_readiness_state_and_explanation_match_selected_choices(self):
        form = self.client.get("/checkin").data
        submission_id = re.search(rb'name="submission_id" value="([^"]+)"', form).group(1).decode()
        result = self.client.post("/checkin", data={"action": "save", "submission_id": submission_id,
                          "feeling": "Overwhelmed", "help_choice": "smaller_step",
                          "manageability": "one_small_step"})
        page = self.client.get(result.headers["Location"]).data
        result_card = page.split(b'<section class="card soft-card"', 1)[1].split(b"</section>", 1)[0]
        self.assertIn(b"Thank you for checking in.", result_card)
        self.assertIn(b'href="/my-plan"', result_card)
        self.assertIn(b"Continue to My Plan", result_card)
        self.assertIn(b"Change my choice", result_card)
        for answer in [b"Ready for one small step", b"Overwhelmed", b"Smaller Step", b"One small step"]:
            self.assertNotIn(answer, result_card)
        self.assertEqual(result_card.count(b"<a "), 2)
        for action in [b"Show one small step", b"Take a quiet break", b"Nothing right now", b"Show my full day"]:
            self.assertNotIn(action, result_card)
        self.assertIn(b"Overwhelmed", page)  # The answer remains inside the collapsed private history.
        history = page.split(b"Private check-in history", 1)[1]
        self.assertIn(b'<details><summary>', history)
        self.assertNotIn(b'<details open', history)
        for score_word in [b"%", b"risk score", b"readiness score", b"capacity score"]:
            self.assertNotIn(score_word, page.lower())

    # A repeated submission identifier and result refresh must keep one saved history entry.
    def test_checkin_save_is_idempotent_and_result_refresh_is_safe(self):
        form = self.client.get("/checkin").data
        submission_id = re.search(rb'name="submission_id" value="([^"]+)"', form).group(1).decode()
        answers = {"action": "save", "submission_id": submission_id, "feeling": "Tired",
                   "manageability": "pause", "note": "Private demo note"}
        first_post = self.client.post("/checkin", data=answers)
        self.assertEqual(first_post.status_code, 302)
        result_url = first_post.headers["Location"]
        result_page = self.client.get(result_url).data
        self.assertIn(b"Thank you for checking in.", result_page)
        self.assertIn(b"Continue to My Plan", result_page)
        before_history, private_history = result_page.split(b'<ul class="checkin-list">', 1)
        for private_answer in [b"Tired", b"pause", b"Private demo note"]:
            self.assertNotIn(private_answer, before_history)
            self.assertIn(private_answer, private_history)
        with self.client.session_transaction() as state:
            self.assertEqual(len(state["checkins"]), 1)
            saved = state["checkins"][0]
            self.assertEqual(saved["submission_id"], submission_id)
            self.assertTrue(saved["created_at"])
            self.assertEqual(saved["note"], "Private demo note")
        refreshed = self.client.get(result_url)
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn(b"Thank you for checking in.", refreshed.data)
        duplicate_post = self.client.post("/checkin", data=answers)
        self.assertEqual(duplicate_post.headers["Location"], result_url)
        with self.client.session_transaction() as state:
            self.assertEqual(len(state["checkins"]), 1)

    # Serve stylesheet and scripts from the same public directory used by Vercel's CDN.
    def test_public_static_assets_and_templates_use_flask_paths(self):
        for path in ["/css/style.css", "/js/main.js", "/js/steps.js", "/js/confetti.js"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertGreater(len(response.data), 0, path)
            response.close()
        page = self.client.get("/today")
        self.assertIn(b'href="/css/style.css"', page.data)
        self.assertIn(b'src="/js/main.js"', page.data)

    # Without OAuth keys, Google sign-in returns to sample data without contacting Google.
    def test_google_signin_is_optional_without_credentials(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
            response = self.client.get("/google/login")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/settings?section=demo")
            with self.client.session_transaction() as state:
                state["google_from_devices"] = True
            response = self.client.get("/google/login")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/devices")

    # Home confirms completion without revealing responses and keeps its basic two-part schedule.
    def test_home_checkin_card_is_simplified_and_schedule_is_unchanged(self):
        fixture_records = load_demo_data()
        fixture_instructions = fixture_records["health_follow_ups"]
        fixture_medications = fixture_records["medications"]
        with self.client.session_transaction() as state:
            before_progress = dict(state.get("activity_progress", {}))
            before_health = dict(state.get("health_plan_states", {}))
        form = self.client.get("/checkin").data
        submission_id = re.search(rb'name="submission_id" value="([^\"]+)"', form).group(1).decode()
        self.client.post("/checkin", data={"action": "save", "submission_id": submission_id,
                          "feeling": "Overwhelmed", "manageability": "one_small_step",
                          "help_choice": "smaller_step"})
        home = self.client.get("/today").data
        card = home.split(b'class="card home-guidance-card"', 1)[1].split(b"</section>", 1)[0]
        self.assertIn(b"Check-in complete", card)
        self.assertIn(b"Continue to My Plan", card)
        self.assertNotIn(b"Overwhelmed", card)
        self.assertNotIn(b"one_small_step", card)
        timeline = home.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0]
        self.assertEqual(timeline.count(b'class="timeline-marker"'), 2)
        self.assertIn(b"Now", timeline)
        self.assertIn(b"Up Next", timeline)
        self.assertNotIn(b"Later", timeline)
        plan = self.client.get("/my-plan").data
        self.assertIn(b"Based on your check-in, we\xe2\x80\x99re showing one activity at a time.", plan)
        self.assertEqual(plan.count(b'class="card activity-card'), 1)
        with self.client.session_transaction() as state:
            self.assertEqual(state.get("activity_progress", {}), before_progress)
            self.assertEqual(state.get("health_plan_states", {}), before_health)
        self.assertEqual(load_demo_data()["health_follow_ups"], fixture_instructions)
        self.assertEqual(load_demo_data()["medications"], fixture_medications)

    # Keep all new check-in fields unavailable in the other role workspaces by default.
    def test_other_roles_cannot_see_private_ema_responses(self):
        with self.client.session_transaction() as state:
            state["checkins"] = [{"id": "private-ema", "person_id": "p1", "date": data.get_today(),
                "time": "10:30", "feeling": "Overwhelmed", "help_choice": "smaller_step",
                "manageability": "one_small_step", "note": "PRIVATE_EMA_NOTE_SENTINEL",
                "readiness_state": "PRIVATE_EMA_STATE_SENTINEL",
                "readiness_reason": "PRIVATE_EMA_REASON_SENTINEL", "visibility": "private"}]
        routes = {"coach": "/coach", "healthcare": "/professional", "trusted": "/trusted", "admin": "/admin"}
        for role, route in routes.items():
            with self.client.session_transaction() as state:
                state["demo_role"] = role
            private_page = self.client.get("/checkin")
            self.assertEqual(private_page.status_code, 302, role)
            self.assertNotIn("/checkin", private_page.headers["Location"], role)
            page = self.client.get(route).data
            for sentinel in [b"PRIVATE_EMA_NOTE_SENTINEL", b"PRIVATE_EMA_STATE_SENTINEL",
                             b"PRIVATE_EMA_REASON_SENTINEL"]:
                self.assertNotIn(sentinel, page, role)

    # Check semantic landmarks, labels, keyboard focus, responsive breakpoints, and theme contrast.
    def test_accessibility_and_responsive_contracts(self):
        routes = [("member", route) for route in ["/today", "/my-plan", "/checkin", "/circle",
                  "/circle/message", "/quiet-break",
                  "/health", "/health/my-plan", "/settings", "/settings?section=appearance",
                  "/settings?section=notifications", "/devices", "/activity/" + self.records["activity_assignments"][0]["id"],
                  "/visit/primary"]]
        routes += [("coach", route) for route in ["/coach", "/coach/library", "/coach/settings"]]
        routes += [("healthcare", route) for route in ["/professional", "/professional/packets",
                   "/professional/next-steps", "/professional/settings"]]
        routes += [("trusted", route) for route in ["/trusted", "/trusted/encouragement", "/trusted/settings"]]
        routes += [("admin", route) for route in ["/admin", "/admin/people", "/admin/invitations",
                   "/admin/consent", "/admin/templates", "/admin/settings"]]
        for role, route in routes:
            with self.client.session_transaction() as state:
                state["demo_role"] = role
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, route)
            parser = ControlNames()
            parser.feed(response.data.decode())
            for control in parser.controls:
                self.assertTrue(control["named"] or control["wrapped"] or
                                control["id"] in parser.labels,
                                f"Unlabelled control on {route}: {control}")
        with open(os.path.join(pair.app.static_folder, "css", "style.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn(":focus-visible", css)
        self.assertIn("@media (max-width: 899px)", css)
        self.assertIn("@media (min-width: 900px)", css)
        self.assertIn("@media (max-width: 767px)", css)
        self.assertIn("@media (max-width: 480px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn(".workspace-shell", css)
        self.assertIn(".role-sidebar", css)
        self.assertIn(".mobile-role-nav", css)
        for theme in ["ocean", "garden", "twilight"]:
            colors = re.search(rf'\[data-theme="{theme}"\]\s*\{{([^}}]+)\}}', css).group(1)
            values = dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", colors))
            for foreground, background in [("text", "bg"), ("text", "surface"),
                                           ("muted", "bg"), ("on-primary", "primary")]:
                self.assertGreaterEqual(self.contrast(values[foreground], values[background]), 4.5,
                                        f"{theme}: {foreground} on {background}")

    # Compute WCAG contrast for two six-digit colors.
    def contrast(self, first, second):
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            channels = [((value + .055) / 1.055) ** 2.4 if value > .04045 else value / 12.92
                        for value in channels]
            return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]
        high, low = sorted([luminance(first), luminance(second)], reverse=True)
        return (high + .05) / (low + .05)


if __name__ == "__main__":
    unittest.main()
