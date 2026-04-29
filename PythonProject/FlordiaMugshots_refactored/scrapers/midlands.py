import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .manifest import load_manifest, save_manifest

_SOURCE_URL = "https://www.abccolumbia.com/news/mugshots/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def _get_mugshot_links(mode):
    response = requests.get(_SOURCE_URL, headers=_HEADERS)
    if response.status_code != 200:
        print("Failed to fetch the Midlands listing page.")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        if "Midlands Mugshots" in a.text:
            links.append(urljoin(_SOURCE_URL, a["href"]))
            if mode == 'recent':
                break  # only the latest post
    return links


def _download_images_from_page(page_url, output_dir, downloaded):
    response = requests.get(page_url, headers=_HEADERS)
    if response.status_code != 200:
        print(f"Failed to access {page_url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "")
        if not src or not src.lower().endswith(".jpg"):
            continue
        full_url = urljoin(page_url, src)
        img_name = f"MIDLANDS_{os.path.basename(full_url)}"

        if img_name in downloaded:
            print(f"Skipping {img_name}, already downloaded.")
            continue

        try:
            img_data = requests.get(full_url, headers=_HEADERS).content
            with open(os.path.join(output_dir, img_name), "wb") as f:
                f.write(img_data)
            print(f"Downloaded: {img_name}")
            downloaded.add(img_name)
        except Exception as e:
            print(f"Failed to download {full_url}: {e}")


def download(output_dir, mode='recent'):
    """Download Midlands (SC) mugshots.

    mode='recent'  — latest post only
    mode='all'     — every Midlands Mugshots post on the listing page
    """
    os.makedirs(output_dir, exist_ok=True)
    manifest_path = os.path.join(output_dir, 'manifest_midlands.json')
    downloaded = load_manifest(manifest_path)

    for link in _get_mugshot_links(mode):
        _download_images_from_page(link, output_dir, downloaded)

    save_manifest(manifest_path, downloaded)
    print(f"Midlands download complete. Total in manifest: {len(downloaded)}")
