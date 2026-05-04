"""Label images in Images/<County>/ subfolders.

Two things this script does:
  1. Move images from the flat Images/ root into county subfolders based on
     filename prefix (e.g. ORANGE_abc.jpg → Images/Orange/).
  2. Rename images inside each county subfolder that are missing the county
     prefix (e.g. Images/Boward/image_0.jpg → Images/Boward/Boward_image_0.jpg)
     so the classifier can infer the correct county during evaluation.
"""
import os
import shutil
from config import IMAGES_DIR

IMAGE_EXTS = {'.jpg', '.jpeg', '.png'}

# Maps filename prefix → destination subfolder (for flat Images/ root files)
PREFIX_TO_FOLDER = {
    "ORANGE_":    os.path.join(IMAGES_DIR, "Orange"),
    "JEFFERSON_": os.path.join(IMAGES_DIR, "Jefferson"),
    "MIDLANDS_":  os.path.join(IMAGES_DIR, "Midlands"),
    "BOWARD_":    os.path.join(IMAGES_DIR, "Boward"),
    "POLK_":      os.path.join(IMAGES_DIR, "Polk"),
    "SEMINOLE_":  os.path.join(IMAGES_DIR, "Seminole"),
    "PALMBEACH_": os.path.join(IMAGES_DIR, "PalmBeach"),
}

# Maps subfolder name → prefix to add when renaming unprefixed files
COUNTY_PREFIX = {
    "Orange":    "Orange_",
    "Jefferson": "Jefferson_",
    "Midlands":  "Midlands_",
    "Boward":    "Boward_",
    "Polk":      "Polk_",
    "Seminole":  "Seminole_",
    "PalmBeach": "PalmBeach_",
}


def _move_from_root(source_dir):
    """Move prefixed files from the flat Images/ root into county subfolders."""
    moved = 0
    for filename in os.listdir(source_dir):
        if os.path.splitext(filename)[1].lower() not in IMAGE_EXTS:
            continue
        for prefix, folder in PREFIX_TO_FOLDER.items():
            if filename.upper().startswith(prefix):
                os.makedirs(folder, exist_ok=True)
                shutil.move(os.path.join(source_dir, filename),
                            os.path.join(folder, filename))
                print(f"Moved:   {filename} → {folder}/")
                moved += 1
                break
    return moved


def _rename_in_subfolders():
    """Add county prefix to any unprefixed images inside each county subfolder."""
    renamed = 0
    for county, prefix in COUNTY_PREFIX.items():
        folder = os.path.join(IMAGES_DIR, county)
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            if os.path.splitext(filename)[1].lower() not in IMAGE_EXTS:
                continue
            if not filename.lower().startswith(prefix.lower()):
                new_name = prefix + filename
                os.rename(os.path.join(folder, filename),
                          os.path.join(folder, new_name))
                print(f"Renamed: {filename} → {new_name}  [{county}]")
                renamed += 1
    return renamed


def label_images(source_dir=IMAGES_DIR):
    moved   = _move_from_root(source_dir)
    renamed = _rename_in_subfolders()
    print(f"\nDone. {moved} file(s) moved, {renamed} file(s) renamed.")


if __name__ == "__main__":
    label_images()
