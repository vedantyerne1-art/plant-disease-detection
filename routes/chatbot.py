from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database.db import get_connection
from services.disease_service import search_diseases


chatbot_api = Blueprint("chatbot_api", __name__)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_answer(message):
    text = message.lower()
    keywords = []
    for word in ("tomato", "potato", "grape", "apple", "peach", "corn", "maize", "aloe",
                 "fungus", "fungal", "bacterial", "viral", "yellow", "brown", "spot", "rust",
                 "mildew", "blight", "water", "watering", "fertilizer"):
        if word in text:
            keywords.append(word)

    matches = []
    seen = set()
    for keyword in keywords:
        for disease in search_diseases(query=keyword):
            if disease["disease_id"] not in seen:
                seen.add(disease["disease_id"])
                matches.append(disease)
        if len(matches) >= 3:
            break

    if not matches:
        if any(word in text for word in ("water", "watering")):
            return (
                "Water according to soil moisture and plant needs rather than a fixed schedule. "
                "Check the upper soil layer, ensure drainage, and avoid keeping roots saturated. "
                "Local climate and plant type should determine frequency."
            )
        return (
            "I can provide general plant-care guidance using the verified model class records, "
            "but I do not have enough context for a confirmed diagnosis. Include the plant name "
            "and symptoms, or review the Disease Library."
        )

    disease = matches[0]
    prevention = "; ".join(disease["prevention"][:2])
    treatment = "; ".join(disease["treatment"][:2])
    return (
        f"The closest record is {disease['disease_name']} for {disease['affected_plant']}. "
        f"{disease['description']} "
        f"General prevention: {prevention}. "
        f"General care: {treatment}. "
        "This is preliminary guidance, not a confirmed diagnosis."
    )


@chatbot_api.post("/api/doctor/chat")
def chat():
    user_id = session.get("user_id")
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if len(message) < 2 or len(message) > 1000:
        return jsonify({"error": "Enter a question between 2 and 1000 characters."}), 400

    answer = build_answer(message)
    if not user_id:
        return jsonify({"answer": answer, "saved": False})

    now = utc_now()
    with get_connection() as connection:
        conversation = connection.execute(
            "SELECT id FROM chatbot_conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if conversation:
            conversation_id = conversation["id"]
            connection.execute(
                "UPDATE chatbot_conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        else:
            cursor = connection.execute(
                "INSERT INTO chatbot_conversations (user_id, title, created_at, updated_at) "
                "VALUES (?, 'Plant Doctor conversation', ?, ?)",
                (user_id, now, now),
            )
            conversation_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO chatbot_messages (conversation_id, role, content, created_at) "
            "VALUES (?, 'user', ?, ?)",
            (conversation_id, message, now),
        )
        connection.execute(
            "INSERT INTO chatbot_messages (conversation_id, role, content, created_at) "
            "VALUES (?, 'assistant', ?, ?)",
            (conversation_id, answer, now),
        )
    return jsonify({"answer": answer, "saved": True})


@chatbot_api.post("/api/doctor/clear")
def clear_chat():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": True})
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM chatbot_conversations WHERE user_id = ?",
            (user_id,),
        )
    return jsonify({"ok": True})
