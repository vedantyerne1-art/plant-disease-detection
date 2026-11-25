from pathlib import Path
from huggingface_hub import hf_hub_download

REPO_ID = "KumarjitC/plantulus-doctor"
MODEL_DIR = Path(__file__).parent / "model"
MODEL_DIR.mkdir(exist_ok=True)

files = [
    "plantulus_doctor.keras",
    "classes.json",
    "class_info.json",
    "preprocessing.json",
]

for filename in files:
    print(f"Downloading {filename} ...")
    downloaded = hf_hub_download(repo_id=REPO_ID, filename=filename)
    destination = MODEL_DIR / filename
    if destination.exists():
        destination.unlink()
    # Copy the cached file into this project's model folder.
    import shutil
    shutil.copy2(downloaded, destination)
    print(f"Saved: {destination}")

print("\nModel files downloaded successfully.")
print("Next run: python app.py")
