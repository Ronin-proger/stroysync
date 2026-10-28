# StroySync

[![CI](https://github.com/Ronin-proger/stroysync/actions/workflows/ci.yml/badge.svg)](https://github.com/Ronin-proger/stroysync/actions/workflows/ci.yml)

Construction-site monitoring that links a camera frame to the project schedule. Equipment is detected in the frame, the active WBS stages for that camera and date are resolved, and the observed machinery is scored against what each stage requires, allows or forbids. The result is a status (on schedule, deviation, critical) with the rule that triggered it.

![Site map](docs/screens/unit-map-wide.png)

## Pipeline

```text
frame ─► detector ─► detections ─┬─► schedule matcher ─► scorecard + rule ids
                                 │        ▲
                                 │        └── camera × date → active leaf WBS stages
                                 └─► ground projection ─► 3D site twin (glTF)
```

**Detection.** Backends are selected with `DETECTOR_BACKEND`:

| Backend | Model | Use |
|---|---|---|
| `world` | YOLO-World, open-vocabulary prompts for 8 equipment classes | default when Ultralytics is installed |
| `coco` | YOLOv8n, COCO classes remapped | fallback |
| `demo` | deterministic boxes keyed by sample scene, no model | offline CI and tests |
| `auto` | `world → coco → demo` | default |

**Schedule matching** (`services/matcher.py`). Each criterion is scored from 0 to 1, and the overall index is a weighted sum:

- coverage: the share of required equipment that is visible
- signature: the Jaccard similarity to the stage's `typical_signature`
- role fit: earthworks, concrete, lifting and similar roles
- safety: 0 if any forbidden machine is present
- activity: whether any machinery is present at all

Rules fire on leaf WBS nodes only, so parent and child stages never duplicate a warning.

**Site twin** (`services/reconstructor.py`). Two complementary paths feed a shared world frame:

- Pixels are back-projected onto the ground and the pit using known camera poses. AKAZE keypoints are matched between frames and triangulated into a point cloud.
- The bottom edge of each detection box is cast as a ray to the ground, which places the machine in 3D.

The scene is exported as binary glTF and rendered with three.js.

**Site notes** (`services/obsidian.py`). Shift logs and daily reports are stored as markdown in an Obsidian vault (`HACAOBS/`). Writes go through the Obsidian Local REST API when it is running, and directly to the filesystem otherwise. The note graph is rendered in the dashboard.

## Running

```bash
docker compose up --build
```

- UI: http://localhost:8080
- API and dashboard: http://localhost:8000
- OpenAPI: http://localhost:8000/docs

Copy `.env.example` to `.env` to override settings. `CORS_ORIGINS` is an explicit comma-separated list.

Without Docker:

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: start-backend.bat
pip install -r backend/requirements.txt           # + `pip install ultralytics` for YOLO
PYTHONPATH=backend DETECTOR_BACKEND=demo uvicorn app.main:app --app-dir backend --reload

cd frontend && npm install && npm run dev
```

CLI:

```bash
PYTHONPATH=backend python -m app.cli analyze data/samples/sample_foundation.jpg \
  --camera CAM-01 --at 2026-09-17T10:15:00
```

Tests and lint:

```bash
cd backend
DETECTOR_BACKEND=demo pytest -q
ruff check app tests
```

## Layout

```text
backend/app/
  api/            FastAPI routers: analyze, catalog, twin, notes
  services/       detector, matcher, reconstructor, site_map, obsidian
  static/         embedded dashboard (three.js twin, notes graph)
frontend/         React + Vite UI
data/schedule/    WBS calendar (CSV / XLSX)
tools/site_dcc/   procedural site assembly, triplanar shaders (GLSL, Unity, Unreal)
HACAOBS/          site notes vault
docs/             DATA_MODEL.md, screenshots
```

![Buildings](docs/screens/buildings.png)
![Crane](docs/screens/crane-close.png)

## Limitations

- The detector is not fine-tuned on site imagery. Open-vocabulary and COCO classes are coarse for specialised machinery.
- `demo` does not recognise arbitrary photos. It returns fixed boxes per sample scene for tests.
- Matching works on single frames: equipment sets are compared per snapshot, without tracking across video.
- Generated twin artefacts (`media/twins/*.bin`, `*.ply`) are built at runtime and are not committed.

Entity model: [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md).
