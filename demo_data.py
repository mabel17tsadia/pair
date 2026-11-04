"""Typed access to fictional demo records through a replaceable data-source interface."""

import json
import os
from datetime import date, datetime, timedelta
from typing import Optional, Protocol, TypedDict


class DemoData(TypedDict):
    """The shared record groups exposed to pages, regardless of storage source."""
    member: dict
    professionals: list
    circle: list
    activity_templates: list
    activity_assignments: list
    health_follow_ups: list
    medications: list
    check_ins: list
    connected_sources: list
    appointment_packets: list


class DemoDataProvider(Protocol):
    """The small interface a fixture, API, or database provider can implement."""

    def load(self) -> DemoData:
        """Return all records used by the demonstration experience."""
        ...


class JsonDemoDataProvider:
    """Load the fictional demonstration records from the checked-in JSON fixture."""

    def __init__(self, path=None):
        """Keep the fixture path configurable for tests and alternate local fixtures."""
        self.path = path or os.path.join(os.path.dirname(__file__), "data", "demo_records.json")

    def load(self) -> DemoData:
        """Read the fixture without coupling presentation code to JSON or file paths."""
        with open(self.path, encoding="utf-8") as fixture:
            return json.load(fixture)


def load_demo_data(provider: Optional[DemoDataProvider] = None) -> DemoData:
    """Use the default JSON fixture or an injected provider with the same interface."""
    return (provider or JsonDemoDataProvider()).load()


def activity_assignments(records, member_id, extra=()):
    """Join a member's assignments to reusable templates and remove duplicate assignment IDs."""
    templates = {item["id"]: item for item in records.get("activity_templates", [])}
    rows = [item for item in records.get("activity_assignments", records.get("activities", []))
            if item.get("assigned_to") == member_id]
    rows += [item for item in extra if item.get("assigned_to") == member_id]
    output = []
    seen = set()
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        template = templates.get(row.get("template_id"), row)
        output.append({**template, **row, "steps": template.get("steps", row.get("steps", [])),
                       "objective": template.get("objective", row.get("objective", ""))})
    return output


def plan_activities(records, today, time_filter="today", source_filter="all", progress=None):
    """Return activities and accepted Health follow-ups matching the selected filters."""
    current = date.fromisoformat(today)
    tomorrow = current + timedelta(days=1)
    week_end = current + timedelta(days=6 - current.weekday())
    sources = {"all", "member", "coach", "health"}
    times = {"today", "tomorrow", "this_week", "later"}
    source_filter = source_filter if source_filter in sources else "all"
    time_filter = time_filter if time_filter in times else "today"
    rows = []

    progress = progress or {}
    activities = records.get("activity_assignments", records.get("activities", []))
    if records.get("activity_templates"):
        member_id = records.get("member", {}).get("application_person_id")
        activities = activity_assignments(records, member_id)
    for activity in activities:
        saved = progress.get(activity["id"], {})
        scheduled = activity.get("scheduled_for", "")
        time_label = (datetime.fromisoformat(scheduled).strftime("%I:%M %p").lstrip("0")
                      if scheduled else "Anytime today")
        rows.append({**activity, **saved, "time_label": time_label, "source_label": {
            "member": "Added by me", "coach": "From my coach"}.get(activity["source"], activity["source"])})
    seen_follow_ups = set()
    for follow_up in records["health_follow_ups"]:
        plan_state = follow_up.get("plan_state", {})
        plan_status = plan_state.get("status", "active")
        if follow_up["status"] == "accepted" and plan_status != "removed":
            if follow_up["id"] in seen_follow_ups:
                continue
            seen_follow_ups.add(follow_up["id"])
            due_on = plan_state.get("scheduled_for", follow_up.get("schedule", {}).get("date", follow_up.get("due_on", "")))
            schedule_time = follow_up.get("schedule", {}).get("time", "")
            scheduled_for = (datetime.strptime(f"{due_on} {schedule_time}", "%Y-%m-%d %I:%M %p").isoformat()
                             if due_on and schedule_time else "")
            status = "paused" if plan_status == "paused" else "accepted"
            rows.append({
                "id": follow_up["id"], "title": follow_up["instruction"], "source": "health",
                "source_name": follow_up["source_name"], "source_label": "From Health",
                "proposed_on": follow_up.get("proposed_on", ""),
                "accepted_on": plan_state.get("accepted_on", follow_up.get("accepted_on", "")),
                "due_on": due_on, "scheduled_for": scheduled_for,
                "time_label": (datetime.fromisoformat(scheduled_for).strftime("%I:%M %p").lstrip("0")
                               if scheduled_for else "Anytime today"),
                "schedule": plan_state.get("schedule", follow_up.get("schedule", {})),
                "plan_status": plan_status,
                "estimated_minutes": follow_up.get("estimated_minutes", 10),
                "status": status,
                "next_action": "Resume this step" if plan_status == "paused" else "Review the details in Health",
                "health_link": f"/health/next-steps#{follow_up['id']}",
            })

    visible = []
    for item in rows:
        planned_text = item["due_on"] or item["scheduled_for"][:10]
        planned_day = date.fromisoformat(planned_text) if planned_text else None
        if planned_day is None and time_filter != "later":
            continue
        if planned_day and time_filter == "today" and planned_day != current:
            continue
        if planned_day and time_filter == "tomorrow" and planned_day != tomorrow:
            continue
        if planned_day and time_filter == "this_week" and not current <= planned_day <= week_end:
            continue
        if planned_day and time_filter == "later" and planned_day <= week_end:
            continue
        if source_filter != "all" and item["source"] != source_filter:
            continue

        item["date_label"] = f"{planned_day:%A}, {planned_day:%B} {planned_day.day}" if planned_day else "No due date"
        if item["scheduled_for"]:
            scheduled = datetime.fromisoformat(item["scheduled_for"])
            item["date_label"] += f" · {scheduled:%I:%M %p}".replace(" 0", " ")
        item["status_label"] = item["status"].replace("_", " ").capitalize()
        visible.append(item)

    return sorted(visible,
                  key=lambda item: (item["due_on"] or item["scheduled_for"][:10] or "9999-12-31", item["scheduled_for"]))
