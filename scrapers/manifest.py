import json
import os
from datetime import datetime


def load_manifest(manifest_path):
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            data = json.load(f)
            # support both list-of-dicts and plain list of strings
            if data and isinstance(data[0], dict):
                return {entry['img_name'] for entry in data}
            return set(data)
    return set()


def save_manifest(manifest_path, image_names):
    data = [
        {'img_name': name, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        for name in sorted(image_names)
    ]
    with open(manifest_path, 'w') as f:
        json.dump(data, f, indent=4)
