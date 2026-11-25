# PlantCare AI — camera + gallery + pretrained AI model

## Step 2: Install and download the pretrained model

This project uses **Plantulus Doctor**, an EfficientNetV2-B0 model published on Hugging Face under the MIT license. Its model card lists 54 plant/disease classes across 19 plants and provides the Keras model, ordered class labels, class information, and preprocessing instructions.

Model card: https://huggingface.co/KumarjitC/plantulus-doctor

### Windows PowerShell

Use Python 3.11 for this setup.

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_model.py
```

The download script saves these files into `model/`:

```text
model/
  plantulus_doctor.keras
  classes.json
  class_info.json
  preprocessing.json
```

The model weights are downloaded separately and are not included in the starter ZIP.

### Run the app

```powershell
python app.py
```

Open: http://127.0.0.1:5000

## Model details and important limitations

- Architecture: EfficientNetV2-B0
- Output: 54 known classes across 19 plants
- Input: RGB, 224 × 224
- Preprocessing: EXIF orientation; resize shorter side to 256; centre crop 256 × 256; centre crop 224 × 224
- Pixel values: float32 in [0, 255]. Do not divide by 255; preprocessing is included in the model.
- The model card reports 98.04% accuracy on its held-out 16,697-image test set. This is the model publisher's reported result, not a guarantee for your images or deployment.
- Most training images have plain backgrounds. Results may be less reliable for real field photos, mixed symptoms, poor lighting, or unsupported plants.
- The classifier always selects one of its 54 classes. The app flags scores below 50% as inconclusive, but this threshold is only a cautious app setting, not a scientifically validated unknown-class detector.

Do not make pesticide or crop-disposal decisions from this prediction alone. Confirm with a qualified local agricultural expert.

## Troubleshooting

**PowerShell does not activate venv:**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

**Model download fails:** Check internet access, rerun `python download_model.py`, and confirm the Hugging Face model repository is accessible.

**TensorFlow installation fails:** Confirm Python is 3.11 (run `python --version`) and use a supported 64-bit Python installation.

**Model files missing:** Confirm all four downloaded files are inside the project's `model` folder.

## Included functionality

- Camera capture and image gallery upload
- Preview, clear, and replace image
- Flask API for image analysis
- Pretrained model integration
- Top-three predictions and confidence
- Responsive mobile/desktop interface

## Phase 1 baseline safeguards

- Uploads are limited to 10 MB.
- Extension, Pillow format, file integrity, and minimum dimensions are validated.
- `/api/analyze` continues to accept multipart field name `image`.
- Model loading and prediction use one guarded model instance.
- Model preprocessing and model weights are unchanged.

## Phase 3 diagnosis safeguards

- Results include a UTC scan timestamp and an image-detail quality warning.
- Severity is always `Unknown`; confidence is not used to infer severity.
- Disease guidance is stored in SQLite for the 54 model classes.
- Disease library records include category, general symptoms, causes, prevention, treatment, references, and verification date.
- AI guidance remains preliminary and does not confirm an unfamiliar plant or non-leaf image.

## Phase 4 account and data safeguards

- Users are stored in SQLite with Werkzeug password hashes.
- Sessions use secure HTTP-only cookies and CSRF tokens for mutating API requests.
- Plants and scans are scoped to the authenticated user.
- Login and registration attempts have a basic in-process rate limit.
- Uploaded scan images are not permanently stored.

Optional environment variables:

```text
SECRET_KEY=replace-with-a-long-random-value
SESSION_COOKIE_SECURE=true
```

## Phase 5 intelligent features

- English, Hindi, and Marathi navigation language switching.
- Database-grounded Plant Doctor responses use disease records and clearly remain preliminary guidance.
- Authenticated reminders support creation, completion, and deletion.
- Weather uses Open-Meteo and supports browser location or manual coordinates.
- Weather and Plant Doctor views provide clear unavailable/error states.

## Deploy on Render

The repository includes a free-tier Render Blueprint in `render.yaml`.

1. Push this project to GitHub. The model weights and local SQLite data are intentionally ignored by Git; the Render build downloads the published model files.
2. In Render, choose **New → Blueprint**, select this GitHub repository, and apply `render.yaml`.
3. Wait for the `/health` check to pass, then open the Render service URL.

This free configuration has no persistent disk. Render may stop the service when idle, and SQLite account, plant, scan, and reminder data can be lost when the service restarts or redeploys. Do not use it for important or sensitive records. TensorFlow model loading may also exceed free-tier resources; if deployment fails or the app runs out of memory, a larger paid service may be required. GPU discovery is disabled because this service runs on CPU. `SECRET_KEY` is generated by Render and secure cookies are enabled for HTTPS.

For local development, create a `.env` from `.env.example` and set a stable `SECRET_KEY` if you want login sessions to survive app restarts.
