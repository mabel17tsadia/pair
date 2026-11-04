"""Exercise the main Pair routes and member-controlled workflows with Flask's test client."""

import os
import re
import unittest
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

    # Replace route variables with known safe demo fixture values.
    def route_path(self, rule):
        values = {"activity_id": self.records["activities"][0]["id"], "person_id": "p1",
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

    # Explain pattern charts with pictograms, source names, plain-language comparisons and a legend.
    def test_patterns_explain_sources_and_usual_ranges(self):
        page = self.client.get("/patterns")
        self.assertEqual(page.status_code, 200)
        for label in [b"Usual range", b"Last 5 days", b"Your usual average",
                      b"Last 5-day average", b"Source:"]:
            self.assertIn(label, page.data)
        self.assertIn(b"pattern-pictogram", page.data)

    # Keep coach views limited to activity progress and to members who shared wellness access.
    def test_coach_scope_excludes_private_and_health_information(self):
        with self.client.session_transaction() as state:
            state["checkins"] = [{"person_id": "p1", "note": "PRIVATE_CHECKIN_SENTINEL"}]
            state["visit_entries"] = {"p1": [{"label": "health", "value": "PRIVATE_HEALTH_SENTINEL"}]}
        response = self.client.get("/coach/learners/p1")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"PRIVATE_CHECKIN_SENTINEL", response.data)
        self.assertNotIn(b"PRIVATE_HEALTH_SENTINEL", response.data)
        self.assertEqual(self.client.get("/coach/learners/p2").status_code, 404)

    # Require opening a consented learner profile before the coach assigns a library activity.
    def test_coach_must_open_learner_before_assignment(self):
        activity_id = self.records["activities"][0]["id"]
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
        packets = pair.professional_authorized_packets()
        self.assertTrue(packets)
        page = self.client.get("/professional/packets")
        self.assertEqual(page.status_code, 200)
        self.assertIn(packets[0]["id"].encode(), page.data)
        self.assertEqual(self.client.get("/professional/packets/packet-completed").status_code, 404)
        self.client.get("/choose/p2")
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

    # Exercise the main activity presentation buttons and retain one-step navigation.
    def test_activity_buttons_keep_the_route_working(self):
        activity_id = self.records["activities"][0]["id"]
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

    # Check semantic landmarks, labels, keyboard focus, responsive breakpoints, and theme contrast.
    def test_accessibility_and_responsive_contracts(self):
        routes = ["/today", "/my-plan", "/checkin", "/circle", "/health", "/settings",
                  "/activity/" + self.records["activities"][0]["id"], "/visit/primary",
                  "/coach/library", "/professional/packets", "/trusted"]
        for route in routes:
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
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
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
