import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_connection


auth_api = Blueprint("auth_api", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@auth_api.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(name) < 2 or len(name) > 100:
        return jsonify({"error": "Name must be between 2 and 100 characters."}), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify({"error": "Enter a valid email address."}), 400
    if len(password) < 8 or len(password) > 128:
        return jsonify({"error": "Password must be between 8 and 128 characters."}), 400

    now = utc_now()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users (name, email, password_hash, role, created_at, updated_at) "
                "VALUES (?, ?, ?, 'user', ?, ?)",
                (name, email, generate_password_hash(password), now, now),
            )
            user_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO user_settings (user_id, language, notifications_enabled, created_at, updated_at) "
                "VALUES (?, 'en', 0, ?, ?)",
                (user_id, now, now),
            )
    except Exception as error:
        if "UNIQUE" in str(error).upper():
            return jsonify({"error": "An account already exists for this email."}), 409
        raise

    session.clear()
    session["user_id"] = user_id
    session["csrf_token"] = __import__("secrets").token_urlsafe(32)
    return jsonify({"user": {"id": user_id, "name": name, "email": email}, "csrf_token": session["csrf_token"]}), 201


@auth_api.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session["csrf_token"] = __import__("secrets").token_urlsafe(32)
    return jsonify({
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
        "csrf_token": session["csrf_token"],
    })


@auth_api.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_api.get("/api/auth/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None})
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not user:
        session.clear()
        return jsonify({"user": None})
    return jsonify({"user": {"id": user["id"], "name": user["name"], "email": user["email"]}})


@auth_api.get("/api/csrf")
def csrf():
    if not session.get("csrf_token"):
        session["csrf_token"] = __import__("secrets").token_urlsafe(32)
    return jsonify({"csrf_token": session["csrf_token"]})
