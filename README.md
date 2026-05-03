# Florida Mugshots County Classifier

A CNN image classifier that identifies which Florida (and South Carolina) county jail a mugshot photo came from. Supports six counties: **Boward, Jefferson, Midlands, Orange, Polk, and Seminole**.

The last evaluation run achieved **98.08% accuracy** on 1,614 test images across all six counties.

---

## How It Works

1. Scrape mugshot images from county jail websites
2. Split images into training and test sets
3. Train a CNN model on the labeled images
4. Evaluate the model and generate per-class accuracy reports and Grad-CAM saliency maps

---

## Prerequisites

- Python **3.9–3.12** (TensorFlow does not support Python 3.13+ yet — if your system Python is newer, install 3.11 separately and use `py -3.11` below)
- Google Chrome (for Selenium-based scrapers)
- pip

### Install dependencies

```bash
py -3.11 -m venv venv        # use Python 3.11 explicitly
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install tensorflow scikit-learn opencv-python pymupdf selenium webdriver-manager requests matplotlib Pillow
```

---

## Step 1 — Configure Paths

Open [config.py](config.py) and verify the paths match your setup. Key settings:

| Variable | Default | Description |
|---|---|---|
| `CLASS_NAMES` | `['Boward', 'Jefferson', ...]` | County names (must match folder names) |
| `CONFIDENCE_THRESHOLD` | `0.60` | Predictions below this are marked "uncategorized" |
| `MODEL_PATH` | `mugshot_classifier4.keras` | Where the trained model is saved/loaded |
| `TRAINING_DIR` | `TrainingData/` | Created by `prepare_data.py` |
| `TEST_DIR` | `TestData/` | Created by `prepare_data.py` |

> **Note:** After the recent repo restructure, update `DATA_ROOT` in `config.py` to point to the project root:
> ```python
> DATA_ROOT = PROJECT_ROOT
> ```

---

## Step 2 — Collect Images

There are two collection methods depending on the county.

### Method A — Automated Scrapers (Jefferson, Midlands, Orange)

Use `download.py` to scrape images directly from county websites.

```bash
# Download recent bookings (new arrivals only)
python download.py --county jefferson --mode recent
python download.py --county midlands --mode recent
python download.py --county orange --mode recent

# Download all historical bookings
python download.py --county orange --mode all --workers 4

# Download all three counties at once
python download.py --county all --mode recent
```

| Flag | Options | Default | Description |
|---|---|---|---|
| `--county` | `jefferson`, `midlands`, `orange`, `all` | required | Which county to scrape |
| `--mode` | `recent`, `all` | `recent` | `recent` = new bookings only; `all` = full history |
| `--output` | any path | auto | Override output directory |
| `--workers` | integer | `3` | Parallel Chrome instances (Orange County only) |

Images land in `newImages/` (recent mode) or `BlankSlate/` (all mode) by default.

---

### Method B — Facebook Scraper (Boward, Polk, Seminole, PalmBeach)

These counties post mugshots to Facebook. Use the browser console script to harvest image URLs, then download them.

**Step 1 — Collect URLs from Facebook**

1. Open the county's Facebook mugshot page in Chrome
2. Open DevTools → Console (`F12`)
3. Paste the contents of [scrapeFacebook.js](scrapeFacebook.js) and press Enter
4. Scroll down slowly through the page — the script collects image URLs every 2 seconds
5. When done, type `stopCollect()` in the console — URLs are copied to your clipboard
6. Paste the clipboard into a text file named after the county, e.g. `Polk.txt` or `Boward.txt`

**Step 2 — Download the images**

```bash
python scrapers/polk.py        # reads Polk.txt, saves to Polk/
python scrapers/boward.py      # reads Boward.txt, saves to Boward/
python scrapers/Seminole.py    # reads Seminole.txt, saves to Seminole/
python scrapers/palm_beach.py  # reads PalmBeach.txt, saves to PalmBeach/
```

---

## Step 3 — Organize Images into County Folders

If images were downloaded to `BlankSlate/` (bulk mode) and have county-prefixed filenames, `label.py` will sort them automatically:

```bash
python label.py
```

This reads filenames like `ORANGE_...`, `JEFFERSON_...`, `MIDLANDS_...` and moves each image into its matching county subfolder.

For other counties (Boward, Polk, etc.), the scrapers in Method B already place images directly into named folders.

At the end of this step you should have populated county folders at the project root:

```
FlordiaMugshots/
├── Boward/
├── Jefferson/
├── Midlands/
├── Orange/
├── Polk/
└── Seminole/
```

---

## Step 4 — Prepare Training and Test Data

Split each county's images 80% training / 20% test:

```bash
python prepare_data.py
```

This creates:
- `TrainingData/<County>/` — 80% of each county's images
- `TestData/` — 20% of each county's images (flat, mixed)

Re-running is safe — already-copied files are skipped and the split never changes (fixed random seed).

---

## Step 5 — Train the Model

```bash
python ml/train.py
```

This trains a CNN with early stopping and learning rate reduction. Training runs up to 16 epochs and saves the best model to the path set in `config.py` (`MODEL_PATH`).

A `training_history.png` chart (accuracy and loss curves) is saved alongside the model file.

---

## Step 6 — Evaluate the Model

```bash
# Evaluate on the held-out test set
python ml/evaluate.py --folder TestData

# Evaluate on newly downloaded images
python ml/evaluate.py --folder newImages

# Use a different model or threshold
python ml/evaluate.py --folder TestData --model my_model.keras --threshold 0.75
```

| Flag | Default | Description |
|---|---|---|
| `--folder` | `newImages/` | Folder of images to classify |
| `--model` | `MODEL_PATH` from config | Path to `.keras` or `.h5` model file |
| `--threshold` | `0.60` | Confidence cutoff; below this → "uncategorized" |

**Output:**
- A timestamped report in `Results/evaluation_YYYY-MM-DD_HH-MM-SS.txt` with accuracy, per-class MCC, and a full classification report
- Misclassified images copied to `wrongPredictions/`
- Averaged Grad-CAM saliency maps saved to `saliency_maps/<County>/`

---

## Step 7 (Optional) — Generate Saliency Maps Manually

Grad-CAM maps are generated automatically during evaluation. To run them standalone for a specific class:

```bash
python ml/saliency.py --class-name orange --image-dir Orange/ --output-dir saliency_maps/
```

---

## Project Structure

```
FlordiaMugshots/
├── config.py              # Paths and model settings
├── download.py            # CLI scraper for Jefferson, Midlands, Orange
├── label.py               # Sorts BlankSlate images into county folders
├── prepare_data.py        # 80/20 train/test split
├── scrapeFacebook.js      # Browser console script for Facebook-hosted mugshots
├── ml/
│   ├── train.py           # Model training
│   ├── evaluate.py        # Evaluation, reports, wrong-prediction logging
│   └── saliency.py        # Grad-CAM heatmap generation
└── scrapers/
    ├── jefferson.py
    ├── midlands.py
    ├── orange_county.py
    ├── polk.py
    ├── boward.py
    ├── Seminole.py
    ├── palm_beach.py
    └── manifest.py        # Download manifest (tracks already-downloaded images)
```

---

## Full Workflow Summary

```
collect images          download.py / scrapeFacebook.js + county scraper
       ↓
organize into folders   label.py  (or scrapers do this automatically)
       ↓
split train/test        prepare_data.py
       ↓
train model             ml/train.py
       ↓
evaluate & report       ml/evaluate.py
```
