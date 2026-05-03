"""Sort images from BlankSlate into county subfolders based on filename prefix."""
import os
import shutil
from config import IMAGES_DIR, DATA_ROOT

PREFIX_TO_FOLDER = {
    "ORANGE_":    os.path.join(DATA_ROOT, "ORANGE"),
    "JEFFERSON_": os.path.join(DATA_ROOT, "JEFFERSON"),
    "MIDLANDS_":  os.path.join(DATA_ROOT, "MIDLANDS"),
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
