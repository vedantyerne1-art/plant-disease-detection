"""Inference adapter for KumarjitC/plantulus-doctor (EfficientNetV2-B0)."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageOps
from threading import Lock

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model" / "plantulus_doctor.keras"
CLASSES_PATH = BASE_DIR / "model" / "classes.json"
INFO_PATH = BASE_DIR / "model" / "class_info.json"

_model = None
_classes = None
_class_info = None
_model_lock = Lock()

def _load_model():
    global _model, _classes, _class_info
    if _model is not None:
        return

    missing = [p.name for p in (MODEL_PATH, CLASSES_PATH, INFO_PATH) if not p.exists()]
    if missing:
        raise RuntimeError(
            "Pretrained model files are missing: " + ", ".join(missing) +
            ". Run 'python download_model.py' first."
        )

    # Set the backend before importing Keras.
    import os
    os.environ.setdefault("KERAS_BACKEND", "tensorflow")
    import keras

    _model = keras.models.load_model(MODEL_PATH, compile=False)
    _classes = json.loads(CLASSES_PATH.read_text(encoding="utf-8"))
    _class_info = json.loads(INFO_PATH.read_text(encoding="utf-8"))

def _preprocess(image):
    # Follow the model card's published preprocessing exactly.
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    scale = 256 / min(width, height)
    new_size = (round(width * scale), round(height * scale))
    image = image.resize(new_size, Image.Resampling.BICUBIC)

    left = (image.width - 256) // 2
    top = (image.height - 256) // 2
    image = image.crop((left, top, left + 256, top + 256))
    image = image.crop((16, 16, 240, 240))  # centre crop 224 × 224

    # Model expects float32 values in [0, 255]; do NOT divide by 255.
    arr = np.asarray(image, dtype=np.float32)
    return np.expand_dims(arr, axis=0)

def _class_details(raw_label, index):
    if isinstance(_class_info, list) and index < len(_class_info):
        item = _class_info[index]
        if isinstance(item, dict):
            return {
                "display_name": item.get("display_name") or item.get("label") or raw_label,
                "plant": item.get("plant", ""),
                "disease": item.get("disease", ""),
                "is_healthy": bool(item.get("is_healthy", "healthy" in raw_label.lower())),
            }
    return {
        "display_name": raw_label.replace("___", " — ").replace("_", " "),
        "plant": "",
        "disease": "",
        "is_healthy": "healthy" in raw_label.lower(),
    }

def predict_leaf(image):
    with _model_lock:
        _load_model()
        batch = _preprocess(image)
        scores = np.asarray(_model.predict(batch, verbose=0)[0], dtype=np.float32)

    if len(scores) != len(_classes):
        raise RuntimeError(
            f"Model returned {len(scores)} scores but classes.json has {len(_classes)} labels."
        )

    order = np.argsort(scores)[::-1][:3]
    best_index = int(order[0])
    best_score = float(scores[best_index])
    raw_label = _classes[best_index]
    details = _class_details(raw_label, best_index)

    low_confidence = best_score < 0.50
    margin = best_score - float(scores[int(order[1])])
    confidence_warning = low_confidence or margin < 0.10
    top_predictions = []
    for i in order:
        top_details = _class_details(_classes[int(i)], int(i))
        top_predictions.append({
            "name": top_details["display_name"],
            "confidence": round(float(scores[int(i)]) * 100, 1),
            "raw_label": _classes[int(i)],
            "plant": top_details["plant"],
            "disease": top_details["disease"],
        })
    return {
        "plant_diagnosis": details["display_name"],
        "plant": details["plant"],
        "disease": details["disease"],
        "raw_label": raw_label,
        "confidence": round(best_score * 100, 1),
        "status": (
            "Inconclusive — try a clearer leaf photo"
            if low_confidence else
            ("Healthy-class prediction" if details["is_healthy"] else "Possible disease detected")
        ),
        "low_confidence": low_confidence,
        "confidence_warning": confidence_warning,
        "confidence_margin": round(margin * 100, 1),
        "severity": "Unknown",
        "severity_basis": "Severity is not inferred from model confidence; visual examination and local expertise are required.",
        "note": (
            "This model always selects one of its 54 known classes. "
            "Even a high score cannot confirm an unfamiliar plant, disease, or non-leaf image. "
            "Use this as preliminary guidance and confirm important decisions with an agricultural expert."
        ),
        "top_predictions": top_predictions
    }
