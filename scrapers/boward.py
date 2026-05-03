import requests
import os

with open('Boward.txt', 'r') as f:
    urls = f.read().splitlines()

os.makedirs(os.path.join('Images', 'Boward'), exist_ok=True)

for i, url in enumerate(urls):
    try:
        img_data = requests.get(url).content
        with open(os.path.join('Images', 'Boward', f"image_{i}.jpg"), 'wb') as f:
            f.write(img_data)
        if i % 10 == 0:
            print(f"Downloaded {i} images...")
    except:
        print(f"Failed to download image {i}")