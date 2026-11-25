import urllib.parse
import urllib.request
import json

from flask import Blueprint, jsonify, request


weather_api = Blueprint("weather_api", __name__)


@weather_api.get("/api/weather")
def weather():
    try:
        latitude = float(request.args.get("latitude", ""))
        longitude = float(request.args.get("longitude", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "Provide a valid latitude and longitude."}), 400
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify({"error": "Coordinates are outside valid ranges."}), 400

    params = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code",
        "timezone": "auto",
    })
    url = "https://api.open-meteo.com/v1/forecast?" + params
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return jsonify({
            "error": "Weather information is temporarily unavailable. Check local weather instead."
        }), 503

    current = payload.get("current") or {}
    temperature = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    rain = current.get("rain")
    weather_code = current.get("weather_code")
    if temperature is None:
        return jsonify({"error": "The weather service returned no current reading."}), 502

    guidance = "Check soil moisture before watering."
    if rain is not None and rain > 0:
        guidance = "Rain is present or recently detected; delay watering if the soil remains moist."
    elif humidity is not None and humidity > 85:
        guidance = "High humidity increases disease risk; improve airflow and avoid overhead watering."
    elif temperature is not None and temperature > 32:
        guidance = "Use shade during peak heat and check water needs carefully."

    return jsonify({
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "rain_mm": rain,
        "weather_code": weather_code,
        "timezone": payload.get("timezone"),
        "guidance": guidance,
        "source": "Open-Meteo",
    })
