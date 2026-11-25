
import os
import secrets
from time import time

from flask import Flask, render_template, request, jsonify, session

from services.prediction_service import (
    ImageValidationError,
    PredictionServiceError,
    analyze_upload,
)
from services.disease_service import get_disease, search_diseases
from database.db import initialize_database
from routes.auth import auth_api
from routes.plants import plants_api
from routes.history import history_api
from routes.reminders import reminders_api
from routes.chatbot import chatbot_api
from routes.weather import weather_api

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "").lower() == "true"

app.register_blueprint(auth_api)
app.register_blueprint(plants_api)
app.register_blueprint(history_api)
app.register_blueprint(reminders_api)
app.register_blueprint(chatbot_api)
app.register_blueprint(weather_api)
initialize_database()

_login_attempts = {}


@app.before_request
def protect_mutating_requests():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    if request.path.startswith("/api/auth/login") or request.path.startswith("/api/auth/register"):
        key = request.remote_addr or "unknown"
        now = time()
        attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < 300]
        if len(attempts) >= 10:
            return jsonify({"error": "Too many attempts. Please try again later."}), 429
        attempts.append(now)
        _login_attempts[key] = attempts

    if request.endpoint == "static":
        return None
    csrf_token = session.get("csrf_token")
    if csrf_token:
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not supplied or supplied != csrf_token:
            return jsonify({"error": "Invalid or missing CSRF token."}), 403
    return None


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/analyze")
def analyze():
    if "image" not in request.files:
        return jsonify({
            "error": "Please select or capture a leaf image."
        }), 400

    file = request.files["image"]

    if not file.filename:
        return jsonify({
            "error": "No image selected."
        }), 400

    try:
        result = analyze_upload(file)
        return jsonify(result)
    except ImageValidationError as error:
        return jsonify({"error": str(error)}), 400
    except PredictionServiceError as error:
        app.logger.exception("Image analysis failed")
        return jsonify({
            "error": str(error)
        }), 503
    except Exception:
        app.logger.exception("Image analysis failed")
        return jsonify({
            "error": "Could not analyze the image. Please try again."
        }), 500


@app.get("/api/diseases")
def diseases():
    return jsonify({
        "diseases": search_diseases(
            query=request.args.get("q", "").strip(),
            category=request.args.get("category", "").strip(),
            plant=request.args.get("plant", "").strip(),
        )
    })


@app.get("/api/diseases/<disease_id>")
def disease_detail(disease_id):
    disease = get_disease(disease_id)
    if not disease:
        return jsonify({"error": "Disease record not found."}), 404
    return jsonify(disease)


@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "error": "Image is too large. Maximum size is 10 MB."
    }), 413


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
