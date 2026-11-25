import json
import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("APP_DATA_DIR", BASE_DIR / "instance"))
DB_PATH = DATA_DIR / "diseases.db"
CLASS_INFO_PATH = BASE_DIR / "model" / "class_info.json"


def _category(raw_label):
    label = raw_label.lower()
    if "healthy" in label:
        return "Healthy"
    if any(word in label for word in ("bacterial", "bacter")):
        return "Bacterial"
    if any(word in label for word in ("mosaic", "yellow_leaf_curl", "virus", "greening")):
        return "Viral"
    if any(word in label for word in ("fungal", "rust", "scab", "blight", "mildew", "mold",
                                      "anthracnose", "leaf_spot", "leaf_scorch", "leaf_blight",
                                      "rot")):
        return "Fungal"
    if any(word in label for word in ("mite", "dactylopius", "pest", "opuntia")):
        return "Pest"
    if "manganese" in label or "toxicity" in label or "necrosis" in label:
        return "Nutrient or toxicity"
    if "sunburn" in label or "withering" in label:
        return "Environmental stress"
    return "Unclassified"


def _guidance(category, plant, disease, healthy):
    if healthy:
        return {
            "description": f"The model class is associated with a healthy {plant} leaf.",
            "symptoms": ["No disease-specific symptoms are represented by this healthy class."],
            "causes": ["No disease cause is assigned to a healthy prediction."],
            "prevention": [
                "Inspect plants regularly.",
                "Water based on plant needs and soil moisture.",
                "Provide appropriate light and airflow.",
            ],
            "treatment": [
                "Continue normal care.",
                "A healthy prediction is preliminary and should be confirmed by visual inspection.",
            ],
        }

    guidance = {
        "Bacterial": (
            "The model label indicates a bacterial plant condition.",
            ["Leaf spots or lesions may be present; exact symptoms require visual confirmation."],
            ["Bacterial infection or spread through contaminated water, tools, or plant debris."],
            ["Sanitize tools, avoid overhead watering, and remove heavily damaged tissue when appropriate."],
            ["Isolate affected plants and obtain local agricultural guidance before applying treatments."],
        ),
        "Fungal": (
            "The model label indicates a fungal or fungus-like plant condition.",
            ["Visible lesions, spots, powdery growth, or blighted tissue may be present."],
            ["Fungal pathogens are often encouraged by moisture, poor airflow, or infected debris."],
            ["Improve airflow, avoid overhead watering, remove affected tissue safely, and sanitize tools."],
            ["Use only locally approved treatments and follow label or professional instructions."],
        ),
        "Viral": (
            "The model label indicates a possible viral plant condition.",
            ["Discoloration, mosaic patterns, curling, or abnormal growth may be visible."],
            ["Plant viruses can spread through infected material or insect vectors."],
            ["Control insect vectors and use clean, pathogen-free planting material."],
            ["Seek an agricultural specialist for confirmation; isolation or removal may be advised locally."],
        ),
        "Pest": (
            "The model label indicates a possible pest or pest-associated condition.",
            ["Leaf lesions, insects, waxy residues, stippling, or abnormal growth may be visible."],
            ["Pest feeding, pest vectors, or secondary infestation may contribute to symptoms."],
            ["Inspect both leaf surfaces and isolate affected plants for monitoring."],
            ["Use gentle physical controls first and consult local guidance before pesticide use."],
        ),
        "Nutrient or toxicity": (
            "The model label indicates a possible nutrient imbalance or toxicity condition.",
            ["Discoloration, tip damage, or abnormal leaf tissue may be visible."],
            ["Nutrient availability, excess mineral levels, soil conditions, or watering practices may contribute."],
            ["Use soil or tissue testing and avoid changing fertilizer rates without evidence."],
            ["Consult a local agronomist if symptoms persist."],
        ),
        "Environmental stress": (
            "The model label indicates a possible environmental stress condition.",
            ["Leaf discoloration, withering, or localized tissue damage may be visible."],
            ["Light, heat, water, humidity, or acclimation stress may contribute."],
            ["Adjust light and watering gradually and compare multiple plants or growing conditions."],
            ["Monitor recovery; seek professional advice for severe or spreading damage."],
        ),
        "Unclassified": (
            "The model label is not assigned to a detailed disease category.",
            ["Specific symptoms are not reliably established by the model label alone."],
            ["The cause cannot be confirmed from classification alone."],
            ["Review visible symptoms and follow general plant sanitation and monitoring practices."],
            ["Consult a qualified plant-health specialist for diagnosis."],
        ),
    }
    description, symptoms, causes, prevention, treatment = guidance[category]
    return {
        "description": description,
        "symptoms": symptoms,
        "causes": causes,
        "prevention": prevention,
        "treatment": treatment,
    }


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS diseases (
                disease_id TEXT PRIMARY KEY,
                disease_name TEXT NOT NULL,
                scientific_name TEXT,
                affected_plant TEXT NOT NULL,
                disease_category TEXT NOT NULL,
                description TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                causes TEXT NOT NULL,
                spread_mechanism TEXT NOT NULL,
                prevention TEXT NOT NULL,
                treatment TEXT NOT NULL,
                reference_sources TEXT NOT NULL,
                last_verified_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_diseases_plant
            ON diseases (affected_plant)
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_diseases_category
            ON diseases (disease_category)
        """)

        class_info = json.loads(CLASS_INFO_PATH.read_text(encoding="utf-8"))
        for item in class_info:
            raw_label = item["label"]
            plant = item.get("plant", "")
            disease = item.get("disease", "")
            healthy = bool(item.get("is_healthy"))
            category = "Healthy" if healthy else _category(raw_label)
            guidance = _guidance(category, plant, disease, healthy)
            now = "2026-11-25"
            spread = (
                "Not applicable to a healthy class."
                if healthy else
                "Spread mechanism must be confirmed for the specific diagnosis."
            )
            sources = json.dumps([
                "Plantulus Doctor model card: https://huggingface.co/KumarjitC/plantulus-doctor",
                "Class label and plant metadata supplied with the model.",
            ])
            connection.execute("""
                INSERT INTO diseases (
                    disease_id, disease_name, scientific_name, affected_plant,
                    disease_category, description, symptoms, causes,
                    spread_mechanism, prevention, treatment, reference_sources,
                    last_verified_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(disease_id) DO UPDATE SET
                    disease_name=excluded.disease_name,
                    affected_plant=excluded.affected_plant,
                    disease_category=excluded.disease_category,
                    description=excluded.description,
                    symptoms=excluded.symptoms,
                    causes=excluded.causes,
                    spread_mechanism=excluded.spread_mechanism,
                    prevention=excluded.prevention,
                    treatment=excluded.treatment,
                    reference_sources=excluded.reference_sources,
                    updated_at=excluded.updated_at
            """, (
                raw_label,
                item.get("display_name", raw_label),
                None,
                plant,
                category,
                guidance["description"],
                json.dumps(guidance["symptoms"]),
                json.dumps(guidance["causes"]),
                spread,
                json.dumps(guidance["prevention"]),
                json.dumps(guidance["treatment"]),
                sources,
                now,
                now,
                now,
            ))


def get_connection():
    initialize_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection
