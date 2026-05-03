#!/usr/bin/env python3
"""Split county images 80/20 into TrainingData/ and TestData/.

Source folders (inside this project):
  Orange, Jefferson, Midlands, Polk, Boward, Seminole
  All images copied flat into TrainingData/ and TestData/ (no subfolders).

Images are copied (originals untouched). Re-running is safe: existing
copies are skipped so the train/test split never changes.
"""
import os
import random
import shutil

SEED        = 42
TRAIN_RATIO = 0.80
IMAGE_EXTS  = {'.jpg', '.jpeg', '.png'}

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

SOURCES = {
    'Orange':    os.path.join(PROJECT_ROOT, 'Orange'),
    'Jefferson': os.path.join(PROJECT_ROOT, 'Jefferson'),
    'Midlands':  os.path.join(PROJECT_ROOT, 'Midlands'),
    'Polk':      os.path.join(PROJECT_ROOT, 'Polk'),
    'Boward':    os.path.join(PROJECT_ROOT, 'Boward'),
    'Seminole':  os.path.join(PROJECT_ROOT, 'Seminole'),
}

TRAIN_DIR = os.path.join(PROJECT_ROOT, 'TrainingData')
TEST_DIR  = os.path.join(PROJECT_ROOT, 'TestData')


def _split_county(county, src_dir):
    images = sorted(
        f for f in os.listdir(src_dir)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    )
    if not images:
        print(f"  {county}: no images found in {src_dir}")
        return

    rng = random.Random(SEED)
    rng.shuffle(images)

    split       = max(1, int(len(images) * TRAIN_RATIO))
    train_files = images[:split]
    test_files  = images[split:]

    county_train = os.path.join(TRAIN_DIR, county)
    os.makedirs(county_train, exist_ok=True)
    os.makedirs(TEST_DIR, exist_ok=True)

    copied_train = copied_test = skipped = 0
    for f in train_files:
        dst = os.path.join(county_train, f)
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(src_dir, f), dst)
            copied_train += 1
        else:
            skipped += 1

    for f in test_files:
        dst = os.path.join(TEST_DIR, f)
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(src_dir, f), dst)
            copied_test += 1
        else:
            skipped += 1

    print(f"  {county}: {len(train_files)} train / {len(test_files)} test"
          f"  ({len(images)} total, {skipped} already present)")


def main():
    print("Splitting images into TrainingData/ and TestData/ ...")
    for county, src in SOURCES.items():
        if not os.path.isdir(src):
            print(f"  {county}: source folder not found, skipping ({src})")
            continue
        _split_county(county, src)

    print(f"\nTrainingData -> {TRAIN_DIR}")
    print(f"TestData     -> {TEST_DIR}")
    print("\nNext steps:")
    print("  1. Train:    python ml/train.py")
    print("  2. Evaluate: python ml/evaluate.py --folder TestData")


if __name__ == '__main__':
    main()
