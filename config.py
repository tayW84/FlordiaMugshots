import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = PROJECT_ROOT

CLASS_NAMES = ['Boward', 'Jefferson', 'Midlands', 'Orange', 'Polk', 'Seminole']
IMG_SIZE = (224, 224)

# Softmax probability below this → image reported as "uncategorized".
# Note: softmax is overconfident by nature; true OOD detection would require
# an explicit "unknown" training class or a calibration step.
CONFIDENCE_THRESHOLD = 0.60

# Input paths (data / model)
MODEL_PATH      = os.path.join(DATA_ROOT, 'mugshot_classifier.keras')
TRAINING_DIR    = os.path.join(PROJECT_ROOT, 'TrainingData')
TEST_DIR        = os.path.join(PROJECT_ROOT, 'TestData')
NEW_IMAGES_DIR  = os.path.join(DATA_ROOT, 'TestData')
IMAGES_DIR      = os.path.join(PROJECT_ROOT, 'Images')
LOCAL_PDF_PATH  = os.path.join(DATA_ROOT, 'new-bookings.pdf')

# Output paths (reports, saliency maps, misclassified images) — all written
# to the refactored project folder so outputs stay with the code, not the data.
RESULTS_DIR     = os.path.join(PROJECT_ROOT, 'Results')
WRONG_PREDS_DIR = os.path.join(PROJECT_ROOT, 'wrongPredictions')
SALIENCY_DIR    = os.path.join(PROJECT_ROOT, 'saliency_maps')
