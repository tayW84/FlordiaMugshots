import os
import sys
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _last_conv_idx(model):
    """Return the index of the last Conv2D layer in model.layers."""
    for i, layer in enumerate(reversed(model.layers)):
        if isinstance(layer, tf.keras.layers.Conv2D):
            return len(model.layers) - 1 - i
    raise ValueError("No Conv2D layer found in model.")


def generate_gradcam(model, img_array, class_index):
    """Grad-CAM heatmap (H x W) for the given class index.

    Walks layers manually to avoid the Sequential-model restriction that
    individual layer.output tensors are undefined until the model is used
    inside a Functional API graph.
    """
    conv_idx = _last_conv_idx(model)
    layers = model.layers
    img_tensor = tf.cast(img_array, tf.float32)

    # Forward pass up to (and including) the last conv layer.
    x = img_tensor
    for layer in layers[:conv_idx + 1]:
        x = layer(x, training=False)
    conv_output = x  # shape: (1, h, w, filters)

    # Gradient of class score w.r.t. conv feature maps.
    with tf.GradientTape() as tape:
        tape.watch(conv_output)
        x = conv_output
        for layer in layers[conv_idx + 1:]:
            x = layer(x, training=False)
        loss = x[:, class_index]

    grads = tape.gradient(loss, conv_output)              # (1, h, w, filters)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))  # (filters,)
    heatmap = conv_output[0] @ pooled_grads[..., tf.newaxis]  # (h, w, 1)
    heatmap = tf.squeeze(heatmap).numpy()
    heatmap = np.maximum(heatmap, 0)
    if heatmap.max() > 0:
        heatmap /= heatmap.max()
    return heatmap


def overlay_gradcam(original_img_array, heatmap, img_size):
    """Return an RGB overlay of the heatmap on the original image."""
    heatmap_resized = cv2.resize(heatmap, (img_size[1], img_size[0]))
    heatmap_uint8 = np.uint8(255 * heatmap_resized)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    orig = np.uint8(255 * original_img_array.squeeze())
    return cv2.addWeighted(orig, 0.6, heatmap_color, 0.4, 0)


def plot_gradcam(overlay, output_path, title):
    plt.figure(figsize=(5, 5))
    plt.imshow(overlay)
    plt.title(title)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()


def save_averaged_gradcam(heatmap_sum, count, img_size, output_path, class_name):
    """Normalise the accumulated heatmap sum and save as a standalone map."""
    avg = heatmap_sum / count
    avg = cv2.resize(avg, (img_size[1], img_size[0]))
    avg /= avg.max() if avg.max() > 0 else 1.0
    plt.figure(figsize=(5, 5))
    plt.imshow(avg, cmap='jet')
    plt.title(f'Averaged Grad-CAM — {class_name}')
    plt.colorbar(fraction=0.046, pad=0.04)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"Averaged Grad-CAM saved: {output_path} ({count} images)")


if __name__ == "__main__":
    import argparse
    from PIL import Image
    from tensorflow.keras.models import load_model
    from config import CLASS_NAMES, IMG_SIZE, MODEL_PATH, SALIENCY_DIR

    parser = argparse.ArgumentParser(description="Generate Grad-CAM maps for a class folder.")
    parser.add_argument('--class-name', required=True,
                        choices=[c.lower() for c in CLASS_NAMES])
    parser.add_argument('--image-dir', required=True)
    parser.add_argument('--output-dir', default=SALIENCY_DIR)
    parser.add_argument('--model', default=MODEL_PATH)
    args = parser.parse_args()

    model = load_model(args.model)
    class_index = [c.lower() for c in CLASS_NAMES].index(args.class_name)
    output_dir = os.path.join(args.output_dir, args.class_name.capitalize())
    os.makedirs(output_dir, exist_ok=True)

    heatmap_sum = None
    count = 0

    for image_file in sorted(os.listdir(args.image_dir)):
        if not image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        image_path = os.path.join(args.image_dir, image_file)
        try:
            img = Image.open(image_path).convert('RGB')
            img_array = np.expand_dims(
                np.array(img.resize((IMG_SIZE[1], IMG_SIZE[0]))) / 255.0, 0
            )
            heatmap = generate_gradcam(model, img_array, class_index)
            overlay = overlay_gradcam(img_array, heatmap, IMG_SIZE)
            out_path = os.path.join(output_dir, f"gradcam_{image_file}")
            plot_gradcam(overlay, out_path, f'Grad-CAM — {args.class_name.capitalize()}')

            resized = cv2.resize(heatmap, IMG_SIZE)
            heatmap_sum = resized if heatmap_sum is None else heatmap_sum + resized
            count += 1
            print(f"Processed: {image_file}")
        except Exception as e:
            print(f"Error processing {image_file}: {e}")

    if count:
        avg_path = os.path.join(output_dir, "averaged_gradcam.png")
        save_averaged_gradcam(heatmap_sum, count, IMG_SIZE, avg_path, args.class_name.capitalize())
