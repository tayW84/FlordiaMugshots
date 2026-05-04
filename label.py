"""Sort images into county subfolders inside Images/ based on filename prefix."""
import os
import shutil
from config import IMAGES_DIR

PREFIX_TO_FOLDER = {
    "ORANGE_":    os.path.join(IMAGES_DIR, "Orange"),
    "JEFFERSON_": os.path.join(IMAGES_DIR, "Jefferson"),
    "MIDLANDS_":  os.path.join(IMAGES_DIR, "Midlands"),
    "BOWARD_":    os.path.join(IMAGES_DIR, "Boward"),
    "POLK_":      os.path.join(IMAGES_DIR, "Polk"),
    "SEMINOLE_":  os.path.join(IMAGES_DIR, "Seminole"),
    "PALMBEACH_": os.path.join(IMAGES_DIR, "PalmBeach"),
}


def label_images(source_dir=IMAGES_DIR):
    for filename in os.listdir(source_dir):
        for prefix, folder in PREFIX_TO_FOLDER.items():
            if filename.startswith(prefix):
                os.makedirs(folder, exist_ok=True)
                shutil.move(
                    os.path.join(source_dir, filename),
                    os.path.join(folder, filename)
                )
                print(f"Moved: {filename} → {folder}/")
                break


if __name__ == "__main__":
    label_images()
