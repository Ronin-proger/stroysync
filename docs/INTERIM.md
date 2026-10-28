# StroySync — промежуточные заметки

StroySync связывает снимок камеры с этапом календарного графика. Техника распознаётся YOLO-World (запасной путь — YOLOv8 COCO; для pytest — детерминированный `demo`). Backend — FastAPI, UI — React, данные — PostgreSQL/SQLite, поставка — Docker Compose.

Камера привязана к зоне и списку WBS. Этап описан множествами техники: обязательно / допустимо / запрещено и `typical_signature`. Соответствие — Jaccard; предупреждение ссылается на правило и код этапа.

Классы: dump truck, excavator, road roller, knuckle boom crane, concrete mixer truck, bulldozer, cargo truck, mobile crane.

Цепочка: `дата снимка × linked_wbs → активные этапы → сравнение состава машин`.
