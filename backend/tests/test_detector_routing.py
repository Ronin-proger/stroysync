"""Маршрутизация бэкенда детектора: demo vs world (с моками)."""

import numpy as np
import pytest

from app.services.detector import EquipmentDetector, RawDetection


@pytest.fixture
def detector(monkeypatch):
    det = EquipmentDetector()
    monkeypatch.setattr(
        "app.services.detector.cv2.imread",
        lambda _path: np.zeros((480, 640, 3), dtype=np.uint8),
    )
    return det


def test_explicit_demo_skips_model_load(detector, monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.detector.settings.detector_backend", "demo")
    called = {"world": False, "coco": False}

    def _world():
        called["world"] = True
        return False

    def _coco():
        called["coco"] = True
        return False

    monkeypatch.setattr(detector, "_try_world", _world)
    monkeypatch.setattr(detector, "_try_coco", _coco)

    image = tmp_path / "photo.jpg"
    image.write_bytes(b"x")
    boxes = detector.detect(image, hint="foundation")

    assert detector.backend == "demo"
    assert called["world"] is False
    assert called["coco"] is False
    assert all(isinstance(b, RawDetection) for b in boxes)
    assert {b.equipment_code for b in boxes} >= {"excavator", "concrete_mixer"}


def test_world_backend_used_when_available(detector, monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.detector.settings.detector_backend", "world")

    def _world():
        detector.backend = "world"
        detector.model = object()
        return True

    monkeypatch.setattr(detector, "_try_world", _world)
    monkeypatch.setattr(
        detector,
        "_predict_ultralytics",
        lambda image, open_vocab: [
            RawDetection("excavator", "экскаватор", 0.95, 1, 1, 40, 40)
        ],
    )

    image = tmp_path / "site.jpg"
    image.write_bytes(b"x")
    boxes = detector.detect(image)

    assert detector.backend == "world"
    assert len(boxes) == 1
    assert boxes[0].equipment_code == "excavator"


def test_world_falls_back_to_demo(detector, monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.detector.settings.detector_backend", "world")
    monkeypatch.setattr(detector, "_try_world", lambda: False)

    image = tmp_path / "site.jpg"
    image.write_bytes(b"x")
    boxes = detector.detect(image, hint="roads")

    assert detector.load() == "demo"
    assert detector.backend == "demo"
    assert {b.equipment_code for b in boxes} >= {"roller"}


def test_auto_prefers_world_over_coco(detector, monkeypatch):
    monkeypatch.setattr("app.services.detector.settings.detector_backend", "auto")
    order = []

    def _world():
        order.append("world")
        detector.backend = "world"
        detector.model = object()
        return True

    def _coco():
        order.append("coco")
        return False

    monkeypatch.setattr(detector, "_try_world", _world)
    monkeypatch.setattr(detector, "_try_coco", _coco)

    assert detector.load() == "world"
    assert order == ["world"]


def test_sample_hint_uses_demo_unless_world(detector, monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.detector.settings.detector_backend", "auto")
    load_called = {"n": 0}

    def _load():
        load_called["n"] += 1
        detector.backend = "demo"
        detector._loaded = True
        return detector.backend

    monkeypatch.setattr(detector, "load", _load)

    image = tmp_path / "sample_foundation.jpg"
    image.write_bytes(b"x")
    boxes = detector.detect(image)

    assert load_called["n"] == 0
    assert {b.equipment_code for b in boxes} >= {"concrete_mixer"}
