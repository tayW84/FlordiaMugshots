import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import datetime
import shutil
import numpy as np
import tensorflow as tf
from sklearn.metrics import matthews_corrcoef, classification_report

from config import (CLASS_NAMES, IMG_SIZE, MODEL_PATH, NEW_IMAGES_DIR,
                    RESULTS_DIR, WRONG_PREDS_DIR, SALIENCY_DIR, CONFIDENCE_THRESHOLD)
from ml.saliency import generate_gradcam, save_averaged_gradcam

# Cap saliency accumulation per class to limit memory use on large datasets.
_MAX_SALIENCY_SAMPLES = 200


def _load_image(img_path):
    raw = tf.io.read_file(img_path)
    img = tf.image.decode_image(raw, channels=3, expand_animations=False)
    img = tf.image.resize(img, IMG_SIZE) / 255.0
    return img.numpy(), tf.expand_dims(img, 0).numpy()


def _true_label_index(img_name):
    """Infer ground-truth class index from filename prefix; None if unrecognised."""
    lower = img_name.lower()
    for i, cls in enumerate(CLASS_NAMES):
        if cls.lower() in lower:
            return i
    return None


def _save_report(text, results_dir):
    os.makedirs(results_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(results_dir, f"evaluation_{stamp}.txt")
    with open(path, 'w') as f:
        f.write(text)
    print(f"\nReport saved -> {path}")


def _build_report(folder_path, confidence_threshold, total, correct,
                  unknown_count, y_true, y_pred, mismatches, unknowns):
    lines = [
        "=" * 64,
        "MUGSHOT CLASSIFIER - EVALUATION REPORT",
        f"Date      : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Folder    : {folder_path}",
        f"Threshold : {confidence_threshold:.0%}",
        "=" * 64,
        "",
        "SUMMARY",
        f"  Images evaluated       : {total + unknown_count}",
        f"  Categorized            : {total}",
        f"  Uncategorized (< {confidence_threshold:.0%}) : {unknown_count}",
        f"  Correct predictions    : {correct}",
        f"  Incorrect predictions  : {total - correct}",
        f"  Accuracy               : {correct / total * 100:.2f}%" if total else "  Accuracy               : N/A",
        "",
    ]

    if y_true and y_pred:
        lines += ["MATTHEWS CORRELATION COEFFICIENT (per class)"]
        for i, name in enumerate(CLASS_NAMES):
            bt = [1 if y == i else 0 for y in y_true]
            bp = [1 if y == i else 0 for y in y_pred]
            lines.append(f"  {name:<12}: {matthews_corrcoef(bt, bp):.4f}")
        lines += [
            "",
            "CLASSIFICATION REPORT",
            classification_report(
                y_true, y_pred,
                labels=list(range(len(CLASS_NAMES))),
                target_names=CLASS_NAMES,
                digits=4,
                zero_division=0,
            ),
        ]

    if mismatches:
        lines += [f"MISMATCHES ({len(mismatches)})", ""]
        lines += [f"  {m}" for m in mismatches]
        lines.append("")

    if unknowns:
        lines += [f"UNCATEGORIZED - below {confidence_threshold:.0%} threshold ({len(unknowns)})", ""]
        lines += [f"  {u}" for u in unknowns]
        lines.append("")

    return "\n".join(lines)


def evaluate(model, folder_path, results_dir=RESULTS_DIR, wrong_preds_dir=WRONG_PREDS_DIR,
             saliency_dir=SALIENCY_DIR, confidence_threshold=CONFIDENCE_THRESHOLD):
    # Running sums for averaged Grad-CAM per predicted class (memory-efficient).
    heatmap_sums = {cls: None for cls in CLASS_NAMES}
    heatmap_counts = {cls: 0 for cls in CLASS_NAMES}

    correct = 0
    total = 0
    unknown_count = 0
    mismatches = []
    unknowns = []
    y_true, y_pred = [], []

    image_files = sorted(
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    )

    for img_name in image_files:
        img_path = os.path.join(folder_path, img_name)
        try:
            img_np, img_array = _load_image(img_path)
        except Exception as e:
            print(f"Could not load {img_name}: {e}")
            continue

        prediction = model.predict(img_array, verbose=0)
        pred_idx = int(np.argmax(prediction, axis=1)[0])
        confidence = float(prediction[0][pred_idx])
        pred_name = CLASS_NAMES[pred_idx]

        if confidence < confidence_threshold:
            unknown_count += 1
            unknowns.append(
                f"{img_name} | Best guess: {pred_name} ({confidence * 100:.1f}%) - below threshold"
            )
            continue

        true_label = _true_label_index(img_name)

        # Accumulate Grad-CAM for this predicted class (capped per class).
        if heatmap_counts[pred_name] < _MAX_SALIENCY_SAMPLES:
            try:
                heatmap = generate_gradcam(model, img_array, pred_idx)
                if heatmap_sums[pred_name] is None:
                    heatmap_sums[pred_name] = heatmap.astype(np.float64)
                else:
                    heatmap_sums[pred_name] += heatmap.astype(np.float64)
                heatmap_counts[pred_name] += 1
            except Exception as e:
                print(f"Grad-CAM failed for {img_name}: {e}")

        if true_label is None:
            # No ground-truth available (unlabelled image) — still counted.
            total += 1
            continue

        y_true.append(true_label)
        y_pred.append(pred_idx)
        total += 1

        if true_label == pred_idx:
            correct += 1
        else:
            true_name = CLASS_NAMES[true_label]
            mismatches.append(
                f"{img_name} | True: {true_name} | Predicted: {pred_name} ({confidence * 100:.1f}%)"
            )
            os.makedirs(wrong_preds_dir, exist_ok=True)
            shutil.copy(img_path, os.path.join(wrong_preds_dir, img_name))

    # Save one averaged Grad-CAM per class.
    for cls_name in CLASS_NAMES:
        count = heatmap_counts[cls_name]
        if count == 0:
            continue
        cls_saliency_dir = os.path.join(saliency_dir, cls_name)
        os.makedirs(cls_saliency_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        avg_path = os.path.join(cls_saliency_dir, f"averaged_gradcam_{stamp}.png")
        save_averaged_gradcam(heatmap_sums[cls_name], count, IMG_SIZE, avg_path, cls_name)

    report = _build_report(folder_path, confidence_threshold, total, correct,
                           unknown_count, y_true, y_pred, mismatches, unknowns)
    print(report)
    _save_report(report, results_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the mugshot classifier.")
    parser.add_argument('--folder', default=NEW_IMAGES_DIR,
                        help='Folder of images to evaluate')
    parser.add_argument('--model', default=MODEL_PATH,
                        help='Path to .keras / .h5 model file')
    parser.add_argument('--threshold', type=float, default=CONFIDENCE_THRESHOLD,
                        help='Confidence threshold; below this -> uncategorized')
    args = parser.parse_args()

    loaded_model = tf.keras.models.load_model(args.model)
    evaluate(loaded_model, args.folder, confidence_threshold=args.threshold)
