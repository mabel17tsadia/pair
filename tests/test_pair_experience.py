"""Exercise the main Pair routes and member-controlled workflows with Flask's test client."""

import os
import re
import unittest
from unittest.mock import patch
from html.parser import HTMLParser

os.environ["SECRET_KEY"] = "pair-test-secret"
os.environ["ANTHROPIC_API_KEY"] = ""

import app as pair
import data
from demo_data import load_demo_data, plan_activities


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

    # Open each role card into its actual route and show the matching role shell.
    def test_role_entry_opens_distinct_workspaces(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Whose view would you like to explore?", page.data)
        self.assertIn(b"brand-mark", page.data)
        self.assertNotIn(b"Choose a demo person", page.data)
        self.assertNotIn(b"Maya Chen", page.data)
        self.assertNotIn(b"Theo Okafor", page.data)
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
        self.assertIn(b"Want to check in before choosing your next step?", page.data)
        plan_page = self.client.get("/my-plan")
        self.assertIn(b"One thing at a time", plan_page.data)
        self.assertIn(b"Show my full day", plan_page.data)
        self.assertIn(b"pace-focus-icon", plan_page.data)
        self.assertIn(b"pace-day-icon", plan_page.data)
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

    # Keep the Home timeline limited to current-day items and preserve both My Pace views.
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
        self.client.post("/my-plan", data={"action": "pace", "pace": "full_day", "time": "today"})
        full_day = self.client.get("/today").data.split(b'<ol class="day-timeline">', 1)[1].split(b'</ol>', 1)[0]
        self.assertIn(b"Practice a simple meal", full_day)
        self.assertIn(b"Tidy my desk", full_day)
        self.assertIn(b"Later", full_day)
        self.assertGreaterEqual(full_day.count(b'class="day-activity"'), 4)

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
        self.assertIn(b"Today at 1:00 PM", plan)

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

    # Keep the default pace focused, retain a saved choice, and clear it with the member's demo data.
    def test_my_pace_default_saved_and_reset(self):
        self.assertNotIn(b"Later", self.client.get("/today").data.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0])
        with self.client.session_transaction() as state:
            self.assertNotIn("plan_pace", state)
        self.client.post("/my-plan", data={"action": "pace", "pace": "full_day"})
        self.assertIn(b"Later", self.client.get("/today").data.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0])
        self.client.post("/settings/delete-data", data={"confirm_delete": "yes"})
        with self.client.session_transaction() as state:
            self.assertNotIn("p1", state.get("plan_pace", {}))
            state["person_id"] = "p1"
            state["demo_role"] = "member"
        self.assertNotIn(b"Later", self.client.get("/today").data.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0])

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
        self.assertIn(b"Detailed preview", page.data)
        self.client.post("/settings?section=notifications", data={
            "action": "save_notification_privacy", "notification_privacy": "detailed"})
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
                self.assertIn(f"time={time_filter}".encode(), response.data)
                self.assertIn(f"source={source_filter}".encode(), response.data)
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
        for label in [b"Good afternoon, Jordan.", b"Choose one thing. Details stay tucked away until you want them.",
                      b"Pair noticed", b"Your week at a glance", b"Your Day", b"Now", b"Up Next",
                      b"Upcoming appointment", b"My Climb", b"data-demo-role=\"member\""]:
            self.assertIn(label, page.data)
        self.assertNotIn(b"Last Check In", page.data)
        self.assertNotIn(b"What feels like a good next step?", page.data)
        self.assertIn(b"day-timeline", page.data)

    # Keep sidebar and mobile member navigation in the approved order.
    def test_member_navigation_order_matches_across_screen_sizes(self):
        page = self.client.get("/today").data.decode()
        expected = ["Home", "Check In", "Health", "My Plan", "Patterns", "Appointments", "My Circle", "Settings"]
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
                                 "help_with": "Prepare questions", "appointment_on": data.get_today()})
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
        for label in [b"Step 5 of 5", b"What I would like help with", b"Left out",
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

    # Keep the focused plan display and full-day preference member-specific and usable.
    def test_my_pace_switches_between_one_and_all_activities(self):
        page = self.client.get("/my-plan?time=this_week&source=all")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"One thing at a time", page.data)
        self.assertIn(b"Show my full day", page.data)
        self.assertIn(b"Show the other", page.data)
        response = self.client.post("/my-plan", data={"action": "pace", "pace": "full_day",
                                   "time": "this_week", "source": "all"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertEqual(state["plan_pace"]["p1"], "full_day")
        page = self.client.get("/my-plan?time=this_week&source=all")
        self.assertIn(b'value="full_day" checked', page.data)
        self.assertNotIn(b"Show the other", page.data)
        response = self.client.post("/my-plan", data={"action": "pace", "pace": "one_at_a_time",
                                   "time": "this_week", "source": "all"})
        self.assertEqual(response.status_code, 302)
        page = self.client.get("/my-plan?time=this_week&source=all")
        self.assertIn(b"Show the other", page.data)

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
        action = next(item for item in self.records["health_follow_ups"] if item["status"] == "proposed")
        response = self.client.post(f"/health/next-steps/{action['id']}", data={"choice": "accept"})
        self.assertEqual(response.status_code, 302)
        plan_page = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        health_page = self.client.get("/health/next-steps")
        self.assertIn(action["instruction"].encode(), plan_page.data)
        self.assertIn(action["instruction"].encode(), health_page.data)
        self.assertIn(b"Accepted", health_page.data)

    # Verify accepted follow-ups appear once, while declined and proposed steps stay out of My Plan.
    def test_health_followups_enter_plan_only_once_after_acceptance(self):
        proposed = [item for item in self.records["health_follow_ups"] if item["status"] == "proposed"]
        page = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        self.assertNotIn(proposed[0]["instruction"].encode(), page.data)
        self.assertNotIn(proposed[1]["instruction"].encode(), page.data)
        self.client.post(f"/health/next-steps/{proposed[0]['id']}", data={"choice": "accept"})
        page = self.client.get("/my-plan", query_string={"time": "later", "source": "health"})
        self.assertEqual(page.data.count(proposed[0]["instruction"].encode()), 1)
        self.assertIn(f"/health/next-steps#{proposed[0]['id']}".encode(), page.data)
        self.client.post(f"/health/next-steps/{proposed[1]['id']}", data={"choice": "decline"})
        self.assertNotIn(proposed[1]["instruction"].encode(), self.client.get(
            "/my-plan", query_string={"time": "later", "source": "health"}).data)

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
        self.assertNotIn(f"/my-plan?time=today&amp;source=all&amp;activity={action['id']}#{action['id']}".encode(), self.client.get("/today").data)
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
        for action in ["fewer", "example", "different", "original", "pictures",
                       "feedback:Okay", "break", "help", "next", "back"]:
            response = self.client.post(url, data={"step": "1", "action": action})
            self.assertEqual(response.status_code, 302, action)
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Learning goal", page.data)

    # Exercise mood choices, display settings, and every visual theme without third-party calls.
    def test_checkin_theme_and_motion_controls(self):
        checkin_page = self.client.get("/checkin")
        for label in [b"Calm", b"Okay", b"Tired", b"Worried", b"Overwhelmed",
                      b"Quiet Break", b"Smaller Step", b"Message Someone", b"Read Aloud",
                      b"Reduce Screen Content", b"Nothing Right Now"]:
            self.assertIn(label, checkin_page.data)
        for display in ["pictures_words", "words_only", "pictures_first"]:
            response = self.client.post("/checkin", data={"action": "display", "display": display})
            self.assertEqual(response.status_code, 302)
        response = self.client.post("/checkin", data={"feeling": "Okay", "help_choice": "quiet_break"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/checkin").status_code, 200)
        for theme in pair.THEMES:
            self.assertEqual(self.client.post("/theme", data={"theme": theme}).status_code, 302)
            page = self.client.get("/settings")
            self.assertIn(f'data-theme="{theme}"'.encode(), page.data)
        for motion in pair.CELEBRATIONS:
            self.assertEqual(self.client.post("/celebrations", data={"celebrations": motion}).status_code, 302)

    # Keep every check-in question optional and allow an empty private entry to be saved.
    def test_ema_questions_can_all_be_skipped_without_a_score(self):
        page = self.client.get("/checkin")
        self.assertIn(b"How manageable does today feel right now?", page.data)
        form = page.data.split(b'class="card checkin-form', 1)[1].split(b"</form>", 1)[0]
        self.assertNotIn(b" required", form)
        self.assertEqual(self.client.post("/checkin", data={"action": "save"}).status_code, 302)
        saved = self.client.get("/checkin").data
        self.assertIn(b"You can decide when you are ready", saved)
        self.assertIn(b"You chose not to answer these questions right now.", saved)
        self.assertIn(b"Private check-in history", saved)
        self.assertNotIn(b"%", saved)
        self.assertNotIn(b"readiness score", saved.lower())
        with self.client.session_transaction() as state:
            checkin = state["checkins"][-1]
            self.assertEqual(checkin["visibility"], "private")
            self.assertTrue(checkin["created_at"])
            self.assertEqual(checkin["manageability"], "")
            self.assertEqual(checkin["guidance_action"], "")
        climb = self.client.get("/climb").data
        goal_list = climb.split(b'<ul class="goal-list">', 1)[1].split(b"</ul>", 1)[0]
        self.assertNotIn(b"Check in", goal_list)

    # Explain the momentary state in plain words matching the member's selected answers.
    def test_ema_readiness_state_and_explanation_match_selected_choices(self):
        self.client.post("/checkin", data={"action": "save", "feeling": "Overwhelmed",
                          "help_choice": "smaller_step", "manageability": "one_small_step"})
        page = self.client.get("/checkin").data
        self.assertIn(b"Ready for one small step", page)
        self.assertIn("You selected “Overwhelmed,” “Smaller Step,” and “One small step.”".encode(), page)
        for action in [b"Show one small step", b"Show my full day", b"Take a quiet break",
                       b"Remind me later", b"Nothing right now"]:
            self.assertIn(action, page)
        for score_word in [b"%", b"risk score", b"readiness score", b"capacity score"]:
            self.assertNotIn(score_word, page.lower())

    # A check-in choice temporarily narrows Home without overwriting My Pace or changing activities.
    def test_ema_one_step_is_temporary_and_does_not_mutate_activities(self):
        fixture_records = load_demo_data()
        fixture_instructions = fixture_records["health_follow_ups"]
        fixture_medications = fixture_records["medications"]
        self.client.post("/my-plan", data={"action": "pace", "pace": "full_day"})
        with self.client.session_transaction() as state:
            before_progress = dict(state.get("activity_progress", {}))
            before_health = dict(state.get("health_plan_states", {}))
        self.client.post("/checkin", data={"action": "save", "manageability": "one_small_step",
                          "help_choice": "smaller_step"})
        with self.client.session_transaction() as state:
            checkin_id = state["checkins"][-1]["id"]
        self.client.post("/checkin", data={"action": "guidance", "checkin_id": checkin_id,
                          "choice": "show_one_step"})
        home = self.client.get("/today").data
        timeline = home.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0]
        self.assertIn(b"One small step", timeline)
        self.assertEqual(timeline.count(b'class="day-activity"'), 1)
        self.assertIn(b"Walk for 15 minutes daily", timeline)
        self.assertIn(b"Dr. Priya Patel", timeline)
        self.assertIn(b"1:00 PM", timeline)
        with self.client.session_transaction() as state:
            self.assertEqual(state["plan_pace"]["p1"], "full_day")
            self.assertEqual(state.get("activity_progress", {}), before_progress)
            self.assertEqual(state.get("health_plan_states", {}), before_health)
        self.assertEqual(load_demo_data()["health_follow_ups"], fixture_instructions)
        self.assertEqual(load_demo_data()["medications"], fixture_medications)
        self.client.post("/checkin", data={"action": "guidance", "checkin_id": checkin_id,
                          "choice": "show_full_day"})
        full_day = self.client.get("/today").data
        timeline = full_day.split(b'<ol class="day-timeline">', 1)[1].split(b"</ol>", 1)[0]
        self.assertIn(b"Later", timeline)
        with self.client.session_transaction() as state:
            self.assertEqual(state["plan_pace"]["p1"], "full_day")

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
        with open(os.path.join(os.path.dirname(__file__), "..", "static", "css", "style.css"),
                  encoding="utf-8") as stylesheet:
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
