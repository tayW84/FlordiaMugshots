import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta
from .manifest import load_manifest, save_manifest

_BASE_URL = "https://sheriff.jccal.org/NewWorld.InmateInquiry/AL0010000"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def _sanitize_filename(raw):
    return "JEFFERSON_" + re.sub(r'[^a-zA-Z0-9_.-]', '_', raw) + ".jpg"


def _page_url(from_date, page):
    formatted = from_date.strftime("%m%%2F%d%%2F%Y")
    return (f"{_BASE_URL}?Name=&SubjectNumber=&BookingNumber="
            f"&BookingFromDate={formatted}&BookingToDate=&Facility=&page={page}")


def _process_page(page_url, output_dir, downloaded):
    response = requests.get(page_url, headers=_HEADERS)
    if response.status_code != 200:
        print(f"Failed page {page_url} ({response.status_code})")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        full_url = src if src.startswith("http") else "https://sheriff.jccal.org" + src
        full_url = full_url.replace("=Search", "=Full")

        filename = _sanitize_filename(full_url.split("/")[-1])
        if filename in downloaded:
            print(f"Skipping {filename}, already downloaded.")
            continue

        try:
            img_data = requests.get(full_url, headers=_HEADERS).content
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_data)
            print(f"Downloaded: {filepath}")
            downloaded.add(filename)
        except Exception as e:
            print(f"Error downloading {full_url}: {e}")


def download(output_dir, mode='recent'):
    """Download Jefferson County (AL) mugshots.

    mode='recent'  — last 1 day, page 1 only
    mode='all'     — last 365 days, pages 1-30
    """
    os.makedirs(output_dir, exist_ok=True)
    manifest_path = os.path.join(output_dir, 'manifest_jefferson.json')
    downloaded = load_manifest(manifest_path)

    days_back = 1 if mode == 'recent' else 365
    pages = 1 if mode == 'recent' else 30
    from_date = datetime.now() - timedelta(days=days_back)

    for page in range(1, pages + 1):
        url = _page_url(from_date, page)
        print(f"Processing page {page}: {url}")
        _process_page(url, output_dir, downloaded)

    save_manifest(manifest_path, downloaded)
    print(f"Jefferson download complete. Total in manifest: {len(downloaded)}")
