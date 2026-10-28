from datetime import date

from app.services.detector import RawDetection
from app.services.matcher import match_snapshot


def _det(*codes, conf: float = 0.9):
    return [RawDetection(c, c, conf, 0, 0, 10, 10) for c in codes]


STAGES = [
    {
        "wbs": "3",
        "name": "Фундамент",
        "zone": "Котлован",
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "required_equipment": ["concrete_mixer"],
        "allowed_equipment": ["concrete_mixer", "excavator", "truck"],
        "forbidden_equipment": ["roller"],
        "typical_signature": ["concrete_mixer", "truck"],
    },
    {
        "wbs": "3.1",
        "name": "Бетонирование",
        "zone": "Котлован",
        "start_date": "2026-09-01",
        "end_date": "2026-09-22",
        "required_equipment": ["concrete_mixer"],
        "allowed_equipment": ["concrete_mixer", "excavator", "truck"],
        "forbidden_equipment": ["roller"],
        "typical_signature": ["concrete_mixer", "truck"],
    },
    {
        "wbs": "6",
        "name": "Благоустройство",
        "zone": "Периметр",
        "start_date": "2027-02-01",
        "end_date": "2027-03-31",
        "required_equipment": ["roller"],
        "allowed_equipment": ["roller", "dump_truck"],
        "forbidden_equipment": ["concrete_mixer"],
        "typical_signature": ["roller", "dump_truck"],
    },
    {
        "wbs": "2",
        "name": "Земляные работы",
        "zone": "Котлован",
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
        "required_equipment": ["excavator"],
        "allowed_equipment": ["excavator", "bulldozer", "dump_truck"],
        "forbidden_equipment": [],
        "typical_signature": ["excavator", "dump_truck"],
    },
]

CAMERA = {"id": "CAM-01", "linked_wbs": ["3.1", "6", "2", "3"], "zone": "Котлован"}


def test_on_track_foundation():
    result = match_snapshot(
        detections=_det("concrete_mixer", "truck"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert result["site_status"] in ("on_track", "warning")
    assert "ON_TRACK" in codes
    assert "FORBIDDEN_EQUIPMENT" not in codes


def test_forbidden_roller_on_foundation():
    result = match_snapshot(
        detections=_det("roller", "concrete_mixer"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    assert any(d["code"] == "FORBIDDEN_EQUIPMENT" for d in result["deviations"])
    assert result["site_status"] == "critical"


def test_ahead_of_schedule_signal():
    result = match_snapshot(
        detections=_det("roller", "dump_truck"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "AHEAD_OF_SCHEDULE" in codes or "MISSING_REQUIRED" in codes
    assert "criteria" in result
    assert "overall" in result["criteria"]


def test_scorecard_safety_zero_on_forbidden():
    result = match_snapshot(
        detections=_det("roller", "concrete_mixer"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    assert result["criteria"]["safety"] == 0.0
    assert result["criteria"]["grade"] in ("D", "F", "C")


def test_missing_required_equipment():
    result = match_snapshot(
        detections=_det("truck"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "MISSING_REQUIRED" in codes
    assert result["site_status"] == "warning"
    assert result["criteria"]["coverage"] < 1.0


def test_no_activity_on_active_stage():
    result = match_snapshot(
        detections=[],
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "NO_ACTIVITY" in codes
    assert result["criteria"]["activity"] == 0.0
    assert result["site_status"] == "warning"


def test_work_outside_schedule():
    result = match_snapshot(
        detections=_det("excavator"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 12, 15),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "WORK_OUTSIDE_SCHEDULE" in codes
    assert result["active_stages"] == []


def test_behind_schedule_signal():
    result = match_snapshot(
        detections=_det("excavator", "dump_truck"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "BEHIND_SCHEDULE" in codes or "MISSING_REQUIRED" in codes


def test_unexpected_equipment():
    result = match_snapshot(
        detections=_det("concrete_mixer", "mobile_crane"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "UNEXPECTED_EQUIPMENT" in codes


def test_rules_apply_to_leaf_stages_only():
    result = match_snapshot(
        detections=_det("concrete_mixer", "truck"),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    rule_wbs = {d["wbs"] for d in result["deviations"] if d["code"] == "ON_TRACK"}
    assert "3.1" in rule_wbs
    assert "3" not in rule_wbs


def test_low_confidence_flag():
    result = match_snapshot(
        detections=_det("concrete_mixer", conf=0.4),
        stages=STAGES,
        camera=CAMERA,
        on_day=date(2026, 9, 17),
    )
    codes = {d["code"] for d in result["deviations"]}
    assert "LOW_CONFIDENCE" in codes


def test_camera_wbs_filter():
    cam = {"id": "CAM-02", "linked_wbs": ["6"], "zone": "Периметр"}
    result = match_snapshot(
        detections=_det("roller", "dump_truck"),
        stages=STAGES,
        camera=cam,
        on_day=date(2027, 2, 15),
    )
    active_wbs = {s["wbs"] for s in result["active_stages"]}
    assert active_wbs == {"6"}
    assert "ON_TRACK" in {d["code"] for d in result["deviations"]}
