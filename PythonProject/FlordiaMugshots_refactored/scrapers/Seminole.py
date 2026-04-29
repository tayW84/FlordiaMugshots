import requests
import os

with open('Seminole.txt', 'r') as f:
    urls = f.read().splitlines()

os.makedirs('Seminole', exist_ok=True)

for i, url in enumerate(urls):
    try:
        img_data = requests.get(url).content
        with open(f"Seminole/image_{i}.jpg", 'wb') as f:
            f.write(img_data)
        if i % 10 == 0:
            print(f"Downloaded {i} images...")
    except:
        print(f"Failed to download image {i}")