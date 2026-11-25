import io
import unittest
from unittest.mock import patch

from PIL import Image

from app import app
from database.db import get_connection


def image_bytes(size=(100, 100), image_format="PNG"):
    output = io.BytesIO()
    image = Image.new("RGB", size, (64, 128, 64))
    image.save(output, format=image_format)
    return output.getvalue()


class PlantCareApiTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        with get_connection() as connection:
            connection.execute(
                "DELETE FROM users WHERE email IN (?, ?)",
                ("grower@example.com", "reminder@example.com"),
            )

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_missing_image(self):
        response = self.client.post("/api/analyze")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_invalid_extension(self):
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(b"text"), "leaf.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("JPG", response.get_json()["error"])

    def test_corrupt_image(self):
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(b"not an image"), "leaf.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("valid", response.get_json()["error"].lower())

    def test_small_image(self):
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(image_bytes((50, 50))), "leaf.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("too small", response.get_json()["error"].lower())

    def test_oversized_image(self):
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(b"x" * (10 * 1024 * 1024 + 1)), "leaf.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("too large", response.get_json()["error"].lower())

    @patch("services.prediction_service.predict_leaf")
    def test_valid_supported_formats_preserve_api_contract(self, mock_predict):
        mock_predict.return_value = {
            "plant_diagnosis": "Tomato - Healthy",
            "confidence": 75.0,
            "status": "Healthy-class prediction",
            "top_predictions": [],
            "note": "Preliminary guidance",
            "raw_label": "tomato_healthy",
        }
        for image_format, filename in (
            ("PNG", "leaf.png"),
            ("JPEG", "leaf.jpg"),
            ("WEBP", "leaf.webp"),
        ):
            with self.subTest(image_format=image_format):
                response = self.client.post(
                    "/api/analyze",
                    data={
                        "image": (
                            io.BytesIO(image_bytes(image_format=image_format)),
                            filename,
                        )
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertIn("plant_diagnosis", payload)
                self.assertIn("confidence", payload)
                self.assertIn("top_predictions", payload)
                self.assertIn("scan_date", payload)
                self.assertIn("image_quality", payload)
        self.assertEqual(mock_predict.call_count, 3)

    def test_registration_login_plants_and_scan_isolation(self):
        csrf_response = self.client.get("/api/csrf")
        csrf_token = csrf_response.get_json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf_token}

        registered = self.client.post("/api/auth/register", json={
            "name": "Test Grower",
            "email": "grower@example.com",
            "password": "StrongPass123!",
        }, headers=headers)
        self.assertEqual(registered.status_code, 201)
        payload = registered.get_json()
        headers["X-CSRF-Token"] = payload["csrf_token"]

        plant = self.client.post("/api/plants", json={
            "name": "Kitchen Tomato",
            "plant_type": "Tomato",
            "planting_date": "2026-11-01",
            "location": "Balcony",
            "notes": "Check leaves weekly",
        }, headers=headers)
        self.assertEqual(plant.status_code, 201)
        plant_id = plant.get_json()["plant"]["id"]

        scan = self.client.post("/api/scans", json={
            "prediction": "Tomato - Healthy",
            "status": "Healthy-class prediction",
            "confidence": 82.5,
            "raw_label": "tomato_healthy",
            "plant_id": plant_id,
            "top_predictions": [{"name": "Tomato - Healthy", "confidence": 82.5}],
        }, headers=headers)
        self.assertEqual(scan.status_code, 201)

        history = self.client.get("/api/scans", headers=headers)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.get_json()["scans"]), 1)

        logout = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout.status_code, 200)

        unauthorized = self.client.get("/api/plants")
        self.assertEqual(unauthorized.status_code, 401)
        unauthorized_history = self.client.get("/api/scans")
        self.assertEqual(unauthorized_history.status_code, 401)

    def test_reminder_creation_completion_and_isolation(self):
        csrf_response = self.client.get("/api/csrf")
        csrf_token = csrf_response.get_json()["csrf_token"]

        registered = self.client.post("/api/auth/register", json={
            "name": "Reminder Grower",
            "email": "reminder@example.com",
            "password": "StrongPass123!",
        }, headers={"X-CSRF-Token": csrf_token})
        headers = {"X-CSRF-Token": registered.get_json()["csrf_token"]}

        created = self.client.post("/api/reminders", json={
            "title": "Water balcony tomato",
            "reminder_type": "Watering",
            "due_at": "2026-12-01T09:00",
        }, headers=headers)
        self.assertEqual(created.status_code, 201)
        reminder_id = created.get_json()["reminder"]["id"]

        completed = self.client.patch(
            f"/api/reminders/{reminder_id}",
            json={"completed": True},
            headers=headers,
        )
        self.assertEqual(completed.status_code, 200)

        listed = self.client.get("/api/reminders", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(listed.get_json()["reminders"][0]["completed"])

        self.client.post("/api/auth/logout", headers=headers)
        unauthorized = self.client.get("/api/reminders")
        self.assertEqual(unauthorized.status_code, 401)

    def test_database_grounded_plant_doctor(self):
        response = self.client.post("/api/doctor/chat", json={
            "message": "How can I prevent fungal infection on tomato?"
        })
        self.assertEqual(response.status_code, 200)
        answer = response.get_json()["answer"]
        self.assertIn("Tomato", answer)
        self.assertIn("preliminary", answer.lower())

    @patch("routes.weather.urllib.request.urlopen")
    def test_weather_endpoint(self, mock_urlopen):
        class WeatherResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b'{"timezone":"Asia/Kolkata","current":{"temperature_2m":28.4,"relative_humidity_2m":70,"rain":0,"weather_code":1}}'

        mock_urlopen.return_value = WeatherResponse()
        response = self.client.get("/api/weather?latitude=18.52&longitude=73.85")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["temperature_c"], 28.4)
        self.assertEqual(payload["source"], "Open-Meteo")

    def test_disease_library_endpoints(self):
        response = self.client.get("/api/diseases")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("diseases", payload)
        self.assertEqual(len(payload["diseases"]), 54)

        detail = self.client.get("/api/diseases/tomato_healthy")
        self.assertEqual(detail.status_code, 200)
        disease = detail.get_json()
        self.assertEqual(disease["affected_plant"], "Tomato")
        self.assertEqual(disease["disease_category"], "Healthy")


if __name__ == "__main__":
    unittest.main()
