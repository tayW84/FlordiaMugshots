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

Open [config.py](config.py) and verify the settings match your setup:

| Variable | Default | Description |
|---|---|---|
| `CLASS_NAMES` | `['Boward', 'Jefferson', ...]` | County names — must match subfolder names inside `Images/` |
| `CONFIDENCE_THRESHOLD` | `0.60` | Predictions below this are marked "uncategorized" |
| `MODEL_PATH` | `mugshot_classifier.keras` | Where the trained model is saved and loaded from |
| `IMAGES_DIR` | `Images/` | Root folder for all downloaded training images |
| `NEW_IMAGES_DIR` | `TestData/` | Where recent bookings are downloaded for evaluation |
| `TRAINING_DIR` | `TrainingData/` | Created by `prepare_data.py` |
| `TEST_DIR` | `TestData/` | Created by `prepare_data.py` |

---

## Step 2 — Collect Images

All downloaded images land in `Images/<County>/` and are ignored by git (images are not stored in this repo — each user builds their own dataset).

There are two collection methods depending on the county.

### Method A — Automated Scrapers (Jefferson, Midlands, Orange)

Use `download.py` to scrape images directly from county websites.

```bash
# Download all historical bookings (use this to build your training dataset)
python download.py --county jefferson --mode all
python download.py --county midlands --mode all
python download.py --county orange --mode all --workers 4

# Download all three counties at once
python download.py --county all --mode all

# Download recent bookings only (new arrivals — goes to TestData/ for evaluation)
python download.py --county jefferson --mode recent
```

| Flag | Options | Default | Description |
|---|---|---|---|
| `--county` | `jefferson`, `midlands`, `orange`, `all` | required | Which county to scrape |
| `--mode` | `recent`, `all` | `recent` | `all` = full history → `Images/<County>/`; `recent` = new bookings → `TestData/` |
| `--output` | any path | auto | Override the output directory |
| `--workers` | integer | `3` | Parallel Chrome instances (Orange County only) |

---

### Method B — Facebook Scraper (Boward, Polk, Seminole, PalmBeach)

These counties post mugshots to Facebook. The process uses a browser console script to collect image URLs, which are then downloaded in bulk.

#### Step B1 — Open the county's Facebook mugshot page in Chrome

Navigate to the county jail's Facebook page or album where mugshots are posted.

#### Step B2 — Open the browser console

Press `F12` and click the **Console** tab.

#### Step B3 — Paste and run the script

Open [scrapeFacebook.js](scrapeFacebook.js), copy the entire contents, paste into the console, and press Enter. You'll see:

```
Collector started! Scroll down slowly. Type 'stopCollect()' to stop and see the final list.
```

#### Step B4 — Scroll slowly through the page

Scroll down at a slow, steady pace. Every 2 seconds the script scans for new images and logs a running total:

```
Total unique images collected: 24
Total unique images collected: 31
...
```

Give each batch of images time to load before scrolling further. Go all the way to the bottom of the album or post.

#### Step B5 — Stop the collector

When done scrolling, type in the console:

```
stopCollect()
```

This stops the scan, prints the final count, and **automatically copies all URLs to your clipboard**.

#### Step B6 — Save the URLs to a text file

Paste your clipboard into a plain text file named after the county and save it in the project root:

- `Polk.txt`
- `Boward.txt`
- `Seminole.txt`
- `PalmBeach.txt`

One URL per line.

#### Step B7 — Review and clean the list (important)

The script collects **all** Facebook CDN images on the page — not just mugshots. The top of the list will typically contain non-mugshot images such as:

- The page's cover photo or header banner
- Profile pictures
- Album thumbnails or preview images

Open the `.txt` file and **delete the first 5 or so URLs**, then spot-check the rest. You can paste any URL directly into your browser to preview it. Remove anything that isn't a plain mugshot headshot.

#### Step B8 — Run the downloader

```bash
python scrapers/polk.py        # reads Polk.txt,      saves to Images/Polk/
python scrapers/boward.py      # reads Boward.txt,    saves to Images/Boward/
python scrapers/Seminole.py    # reads Seminole.txt,  saves to Images/Seminole/
python scrapers/palm_beach.py  # automated with captcha, saves to Images/PalmBeach/
```

---

## Step 3 — Prepare Training and Test Data

Once you have images in `Images/<County>/` for each county, split them 80% training / 20% test:

```bash
python prepare_data.py
```

This creates:
- `TrainingData/<County>/` — 80% of each county's images, organized by class
- `TestData/` — 20% of each county's images, flat mixed folder

Re-running is safe — already-copied files are skipped and the split never changes (fixed random seed).

After this step your folder structure should look like:

```
Images/
├── Boward/       ← source images (all downloads land here)
├── Jefferson/
├── Midlands/
├── Orange/
├── Polk/
└── Seminole/
TrainingData/
├── Boward/       ← 80% split, used for training
├── Jefferson/
└── ...
TestData/         ← 20% split + recent downloads, used for evaluation
```

---

## Step 4 — Train the Model

```bash
python ml/train.py
```

This trains a CNN with early stopping and learning rate reduction. Training runs up to 16 epochs and saves the best model to `MODEL_PATH` set in `config.py`.

A `training_history.png` chart (accuracy and loss curves) is saved alongside the model file.

---

## Step 5 — Evaluate the Model

```bash
# Evaluate on the held-out test set
python ml/evaluate.py --folder TestData

# Use a different model or confidence threshold
python ml/evaluate.py --folder TestData --model my_model.keras --threshold 0.75
```

| Flag | Default | Description |
|---|---|---|
| `--folder` | `TestData/` | Folder of images to classify |
| `--model` | `MODEL_PATH` from config | Path to `.keras` or `.h5` model file |
| `--threshold` | `0.60` | Confidence cutoff; below this → "uncategorized" |

**Output:**
- A timestamped report in `Results/evaluation_YYYY-MM-DD_HH-MM-SS.txt` with accuracy, per-class MCC, and a full classification report
- Misclassified images copied to `wrongPredictions/`
- Averaged Grad-CAM saliency maps saved to `saliency_maps/<County>/`

---

## Step 6 (Optional) — Generate Saliency Maps Manually

Grad-CAM maps are generated automatically during evaluation. To run them standalone for a specific class:

```bash
python ml/saliency.py --class-name orange --image-dir Images/Orange/ --output-dir saliency_maps/
```

---

## Project Structure

```
FlordiaMugshots/
├── config.py              # Paths and model settings
├── download.py            # CLI scraper for Jefferson, Midlands, Orange
├── label.py               # Sorts flat image dumps into Images/<County>/ subfolders
├── prepare_data.py        # 80/20 train/test split from Images/ into TrainingData/ and TestData/
├── scrapeFacebook.js      # Browser console script for Facebook-hosted mugshots
├── Images/                # All downloaded training images (gitignored)
│   ├── Boward/
│   ├── Jefferson/
│   └── ...
├── ml/
│   ├── train.py           # Model training
│   ├── evaluate.py        # Evaluation, reports, wrong-prediction logging
│   └── saliency.py        # Grad-CAM heatmap generation
└── scrapers/
    ├── jefferson.py
    ├── midlands.py
    ├── orange_county.py
    ├── polk.py            # Reads Polk.txt, saves to Images/Polk/
    ├── boward.py          # Reads Boward.txt, saves to Images/Boward/
    ├── Seminole.py        # Reads Seminole.txt, saves to Images/Seminole/
    ├── palm_beach.py      # Selenium scraper with captcha, saves to Images/PalmBeach/
    └── manifest.py        # Tracks already-downloaded images to avoid duplicates
```

---

## Full Workflow Summary

```
collect images (--mode all)    download.py  /  scrapeFacebook.js + county scraper
         ↓
all images land in             Images/<County>/
         ↓
split train/test               prepare_data.py  →  TrainingData/  +  TestData/
         ↓
train model                    ml/train.py
         ↓
evaluate & report              ml/evaluate.py --folder TestData
         ↓
evaluate new bookings          download.py --mode recent  →  TestData/
                               ml/evaluate.py --folder TestData
```
