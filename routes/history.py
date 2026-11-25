import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database.db import get_connection


history_api = Blueprint("history_api", __name__)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@history_api.post("/api/scans")
def save_scan():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to save scans."}), 401
    data = request.get_json(silent=True) or {}
    prediction = str(data.get("prediction", "")).strip()
    status = str(data.get("status", "")).strip()
    confidence = float(data.get("confidence", 0) or 0)
    if not prediction or not status:
        return jsonify({"error": "Prediction and status are required."}), 400

    plant_id = data.get("plant_id")
    if plant_id is not None:
        try:
            plant_id = int(plant_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid plant."}), 400
        with get_connection() as connection:
            owned = connection.execute(
                "SELECT id FROM plants WHERE id = ? AND user_id = ?",
                (plant_id, user_id),
            ).fetchone()
        if not owned:
            return jsonify({"error": "Plant not found."}), 404

    top_predictions = data.get("top_predictions", [])
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO scans (user_id, plant_id, plant_name, prediction, status, confidence, low_confidence, "
            "raw_label, top_predictions, image_quality, scan_date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                plant_id,
                str(data.get("plant_name", "")).strip() or None,
                prediction,
                status,
                confidence,
                1 if data.get("low_confidence") else 0,
                str(data.get("raw_label", "")).strip() or None,
                json.dumps(top_predictions),
                json.dumps(data.get("image_quality")) if data.get("image_quality") else None,
                str(data.get("scan_date", "")).strip() or now,
                now,
            ),
        )
        scan_id = cursor.lastrowid
        for rank, item in enumerate(top_predictions, start=1):
            connection.execute(
                "INSERT INTO scan_predictions (scan_id, name, confidence, raw_label, rank) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    scan_id,
                    str(item.get("name", ""))[:200],
                    float(item.get("confidence", 0) or 0),
                    str(item.get("raw_label", ""))[:200] or None,
                    rank,
                ),
            )
        scan = connection.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    return jsonify({"scan": dict(scan)}), 201


@history_api.get("/api/scans")
def list_scans():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to view scan history."}), 401
    query = request.args.get("q", "").strip()
    conditions = ["user_id = ?"]
    parameters = [user_id]
    if query:
        conditions.append("(prediction LIKE ? OR plant_name LIKE ?)")
        pattern = f"%{query}%"
        parameters.extend([pattern, pattern])
    sql = "SELECT * FROM scans WHERE " + " AND ".join(conditions) + " ORDER BY scan_date DESC"
    with get_connection() as connection:
        rows = connection.execute(sql, parameters).fetchall()
    scans = []
    for row in rows:
        item = dict(row)
        item["top_predictions"] = json.loads(item["top_predictions"]) if item["top_predictions"] else []
        item["image_quality"] = json.loads(item["image_quality"]) if item["image_quality"] else None
        scans.append(item)
    return jsonify({"scans": scans})


@history_api.delete("/api/scans/<int:scan_id>")
def delete_scan(scan_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in."}), 401
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, user_id),
        )
    if cursor.rowcount == 0:
        return jsonify({"error": "Scan not found."}), 404
    return jsonify({"ok": True})
