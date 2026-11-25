from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database.db import get_connection


reminders_api = Blueprint("reminders_api", __name__)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@reminders_api.get("/api/reminders")
def list_reminders():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to view reminders."}), 401
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM reminders WHERE user_id = ? ORDER BY completed, due_at",
            (user_id,),
        ).fetchall()
    return jsonify({"reminders": [dict(row) for row in rows]})


@reminders_api.post("/api/reminders")
def create_reminder():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to add reminders."}), 401
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    reminder_type = str(data.get("reminder_type", "")).strip()
    due_at = str(data.get("due_at", "")).strip()
    if len(title) < 2 or len(title) > 120:
        return jsonify({"error": "Reminder title must be between 2 and 120 characters."}), 400
    if reminder_type not in {"Watering", "Fertilizer", "Inspection", "Disease follow-up", "Pruning", "Seasonal care"}:
        return jsonify({"error": "Choose a valid reminder type."}), 400
    if not due_at:
        return jsonify({"error": "Choose a reminder date and time."}), 400
    now = utc_now()
    plant_id = data.get("plant_id")
    if plant_id is not None:
        try:
            plant_id = int(plant_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid plant."}), 400
    with get_connection() as connection:
        if plant_id is not None:
            owned = connection.execute(
                "SELECT id FROM plants WHERE id = ? AND user_id = ?",
                (plant_id, user_id),
            ).fetchone()
            if not owned:
                return jsonify({"error": "Plant not found."}), 404
        cursor = connection.execute(
            "INSERT INTO reminders (user_id, plant_id, title, reminder_type, due_at, completed, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (user_id, plant_id, title, reminder_type, due_at, now, now),
        )
        reminder = connection.execute(
            "SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return jsonify({"reminder": dict(reminder)}), 201


@reminders_api.patch("/api/reminders/<int:reminder_id>")
def update_reminder(reminder_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in."}), 401
    data = request.get_json(silent=True) or {}
    completed = 1 if data.get("completed") else 0
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE reminders SET completed = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (completed, now, reminder_id, user_id),
        )
    if cursor.rowcount == 0:
        return jsonify({"error": "Reminder not found."}), 404
    return jsonify({"ok": True})


@reminders_api.delete("/api/reminders/<int:reminder_id>")
def delete_reminder(reminder_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in."}), 401
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
        )
    if cursor.rowcount == 0:
        return jsonify({"error": "Reminder not found."}), 404
    return jsonify({"ok": True})
