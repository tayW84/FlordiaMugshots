"""
Palm Beach County Sheriff's Office - Booking Blotter scraper.

The search page requires hCaptcha, so a visible browser is opened for the
user to solve the captcha.  Once the captcha is done the script handles all
pagination and downloads automatically.

Usage:
    python -m scrapers.palm_beach
    # or import and call:
    from scrapers.palm_beach import download
    download()
"""

import os
import re
import time
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

_SEARCH_URL = "https://www3.pbso.org/blotter/searchresults.cfm"
_BASE_URL    = "https://www3.pbso.org"
_PAGE_WAIT   = 15   # seconds to wait for results table
_CAPTCHA_WAIT = 300  # seconds the user has to solve the captcha
_DELAY       = 0.4  # polite pause between image downloads


# ---------------------------------------------------------------------------
# Browser helpers
# ---------------------------------------------------------------------------

def _setup_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def _set_date_field(driver, field_id, value):
    """Clear and type into a datepicker input via JS to bypass Cleave masking."""
    driver.execute_script(
        """
        var el = document.getElementById(arguments[0]);
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(el, arguments[1]);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        field_id,
        value,
    )


def _wait_for_results(driver, wait):
    """Return True when a results table or 'no records' message appears."""
    try:
        wait.until(lambda d: (
            d.find_elements(By.CSS_SELECTOR, "table.dataTable, #resultsTable, .dataTables_wrapper")
            or "did not match any records" in d.page_source.lower()
            or "no records" in d.page_source.lower()
        ))
        return True
    except TimeoutException:
        return False


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

def _extract_mugshot_urls(driver):
    """Return deduplicated absolute URLs of mugshot images on the current page."""
    seen = set()
    results = []
    for img in driver.find_elements(By.TAG_NAME, "img"):
        src = img.get_attribute("src") or ""
        if not src or src.startswith("data:"):
            continue
        # Skip tiny nav/logo images
        try:
            w = int(img.get_attribute("width") or 0)
            h = int(img.get_attribute("height") or 0)
            if 0 < w < 40 or 0 < h < 40:
                continue
        except (ValueError, TypeError):
            pass
        # Only take URLs that look like photos
        lower = src.lower()
        if any(ext in lower for ext in (".jpg", ".jpeg", ".png", ".gif", "photo", "image", "mugshot", "booking")):
            abs_url = src if src.startswith("http") else urljoin(_BASE_URL, src)
            if abs_url not in seen:
                seen.add(abs_url)
                results.append(abs_url)
    return results


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def _next_page_exists(driver):
    """Return the next-page element or None."""
    # DataTables pagination: look for enabled "Next" button
    for sel in (
        "a.paginate_button.next:not(.disabled)",
        "a#resultsTable_next:not(.disabled)",
        "li.next:not(.disabled) > a",
        "a[id$='_next']:not(.disabled)",
    ):
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            return els[0]

    # Generic text-based fallback
    for a in driver.find_elements(By.TAG_NAME, "a"):
        text = (a.text or "").strip().lower()
        if text in ("next", ">", ">>", "next »", "»"):
            classes = a.get_attribute("class") or ""
            if "disabled" not in classes:
                return a
    return None


def _click_next(driver, wait, btn):
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(1.5)
    _wait_for_results(driver, wait)


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _save_image(session, img_url, output_dir, counter):
    """Download one image; return True on success."""
    try:
        resp = session.get(img_url, timeout=20, stream=True)
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "")
        ext = ".jpg"
        if "png" in ct:
            ext = ".png"
        elif "gif" in ct:
            ext = ".gif"

        # Build a clean filename from the URL path
        raw_name = img_url.rsplit("/", 1)[-1].split("?")[0]
        slug = re.sub(r"[^\w.-]", "_", raw_name) if raw_name else ""
        if not slug:
            slug = f"image_{counter:05d}"
        if not any(slug.lower().endswith(x) for x in (".jpg", ".jpeg", ".png", ".gif")):
            slug += ext

        fpath = os.path.join(output_dir, slug)
        if os.path.exists(fpath):
            return True

        with open(fpath, "wb") as fh:
            for chunk in resp.iter_content(8192):
                fh.write(chunk)
        return True
    except Exception as exc:
        print(f"    [warn] {img_url}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def download(output_dir=os.path.join("Images", "PalmBeach"), days=30):
    """Open a browser, let the user solve hCaptcha, then download all mugshots."""
    os.makedirs(output_dir, exist_ok=True)

    end_date   = datetime.today()
    start_date = end_date - timedelta(days=days)
    end_str    = end_date.strftime("%m/%d/%Y")
    start_str  = start_date.strftime("%m/%d/%Y")

    print(f"Palm Beach blotter: {start_str}  →  {end_str}")
    print("Opening browser — please solve the hCaptcha when it appears, then click Search.")

    driver = _setup_driver()
    wait   = WebDriverWait(driver, _PAGE_WAIT)

    try:
        driver.get(_SEARCH_URL)

        # Fill in the date fields
        wait.until(EC.presence_of_element_located((By.ID, "start_date")))
        _set_date_field(driver, "start_date", start_str)
        _set_date_field(driver, "end_date",   end_str)
        print(f"  Dates filled: {start_str} → {end_str}")
        print(f"  Waiting up to {_CAPTCHA_WAIT}s for you to solve the captcha and click Search...")

        # Wait until results (or no-results message) appear — user submits manually
        submit_wait = WebDriverWait(driver, _CAPTCHA_WAIT)
        if not _wait_for_results(driver, submit_wait):
            print("  Timed out waiting for search results. Exiting.")
            return

        # Set up a requests session that shares the browser's cookies
        session = requests.Session()
        session.headers.update({
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": _SEARCH_URL,
        })
        for cookie in driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])

        total = 0
        page  = 1

        while True:
            img_urls = _extract_mugshot_urls(driver)
            print(f"  Page {page}: {len(img_urls)} image(s)")

            for url in img_urls:
                if _save_image(session, url, output_dir, total):
                    total += 1
                    if total % 25 == 0:
                        print(f"    {total} images downloaded so far...")
                time.sleep(_DELAY)

            btn = _next_page_exists(driver)
            if not btn:
                print("  No more pages.")
                break

            page += 1
            _click_next(driver, wait, btn)

            # Re-sync session cookies after navigation
            for cookie in driver.get_cookies():
                session.cookies.set(cookie["name"], cookie["value"])

    finally:
        driver.quit()

    print(f"\nDone. {total} image(s) saved to '{output_dir}/'.")


if __name__ == "__main__":
    download(output_dir=os.path.join("Images", "PalmBeach"), days=30)
