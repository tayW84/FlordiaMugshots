import os
import re
import base64
import threading
import requests
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from .manifest import load_manifest, save_manifest

_JAIL_URL = "https://netapps.ocfl.net/BestJail/Home/Inmates#"
_PDF_URL  = "https://netapps.ocfl.net/BestJail/PDF/bookings.pdf"
_WAIT_S   = 10


def _setup_driver(driver_path):
    opts = webdriver.ChromeOptions()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--log-level=3')
    opts.add_argument('--disable-logging')
    opts.add_argument('--disable-gpu')
    opts.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(driver_path, log_path=os.devnull)
    return webdriver.Chrome(service=service, options=opts)


def _safe_filename(name):
    return "ORANGE_" + re.sub(r'[^\w]', '_', name).strip('_') + ".png"


def _save_images(driver, name, output_dir, downloaded, lock):
    """Save every base64 mugshot image on the page. Thread-safe via lock."""
    for img in driver.find_elements(By.TAG_NAME, "img"):
        src = img.get_attribute("src") or ""
        if not src.startswith("data:image/png;base64,"):
            continue
        filename = _safe_filename(name)
        with lock:
            if filename in downloaded:
                continue
            data = base64.b64decode(src.split(",")[1])
            with open(os.path.join(output_dir, filename), "wb") as f:
                f.write(data)
            downloaded.add(filename)
        print(f"Saved: {filename}")


def _collect_inmate_names(driver):
    """Extract inmate link texts via a single atomic JS call.

    Matches only ALL-CAPS LASTNAME, FIRSTNAME patterns to exclude nav links
    and avoid the 'Water, Garbage' sentinel breaking early if it appears
    before the results list in the DOM.
    """
    raw = driver.execute_script("""
        var re = /^[A-Z][A-Z\s]+,\s+[A-Z]/;
        var names = [];
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim();
            if (re.test(t)) names.push(t);
        }
        return names;
    """)
    return raw or []


def _js_click_link(driver, name):
    """Click a link by exact text in one atomic JS call."""
    return driver.execute_script("""
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            if (links[i].textContent.trim() === arguments[0]) {
                links[i].click();
                return true;
            }
        }
        return false;
    """, name)


def _has_inmate_links(driver):
    """Return True if the page shows at least one ALL-CAPS inmate result link."""
    return bool(driver.execute_script("""
        var re = /^[A-Z][A-Z\s]+,\s+[A-Z]/;
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            if (re.test(links[i].textContent.trim())) return true;
        }
        return false;
    """))


def _wait_for_results(driver, wait):
    """Wait until actual inmate result links appear (not just nav links)."""
    try:
        wait.until(lambda d: _has_inmate_links(d))
        return True
    except TimeoutException:
        return False


def _js_submit(driver, query):
    """Fill the search box and submit via JS — works even if button is obscured."""
    driver.execute_script("""
        var box = document.getElementById('inmate');
        if (box) { box.value = arguments[0]; }
        var btn = document.querySelector("button[type='submit']");
        if (btn) { btn.click(); }
    """, query)


def _submit_search(driver, wait, query):
    """Submit a search and wait for inmate result links to appear.

    Retries once on cold page load where the first attempt may fire before
    the SPA has fully initialised.
    """
    wait.until(EC.presence_of_element_located((By.ID, "inmate")))
    _js_submit(driver, query)
    if not _wait_for_results(driver, wait):
        # Retry — first search on a fresh page sometimes races the SPA init.
        _js_submit(driver, query)
        return _wait_for_results(driver, wait)
    return True


def _restore_results(driver, wait, query):
    """Re-submit the search to restore the results list after modal/navigation."""
    try:
        wait.until(EC.presence_of_element_located((By.ID, "inmate")))
        _js_submit(driver, query)
        _wait_for_results(driver, wait)
    except TimeoutException:
        driver.get(_JAIL_URL)
        wait.until(EC.presence_of_element_located((By.ID, "inmate")))
        _submit_search(driver, wait, query)


def _close_modal(wait):
    try:
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close")))
        btn.click()
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "button.close")))
    except TimeoutException:
        pass


def _next_page(driver, wait):
    """Click the Next page link if one exists; return True if navigated."""
    clicked = driver.execute_script("""
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().toLowerCase();
            if (t === 'next' || t === '>' || t === '>>' || t === 'next page') {
                links[i].click();
                return true;
            }
        }
        return false;
    """)
    if clicked:
        return _wait_for_results(driver, wait)
    return False


def _process_results(driver, wait, query, output_dir, downloaded, lock, tag):
    """Process all pages of results for a query, clicking each inmate."""
    page = 1
    while True:
        names = _collect_inmate_names(driver)
        print(f"[{tag}] '{query}' page {page}: {len(names)} results")

        for name in names:
            with lock:
                if _safe_filename(name) in downloaded:
                    continue
            try:
                if not _js_click_link(driver, name):
                    continue
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
                _save_images(driver, name, output_dir, downloaded, lock)
                _close_modal(wait)
                # Modal close (or navigation) may clear the results list —
                # always re-submit to restore it before the next iteration.
                _restore_results(driver, wait, query)
            except Exception as e:
                print(f"[{tag}] Error on '{name}': {e}")
                try:
                    _restore_results(driver, wait, query)
                except Exception:
                    pass

        if not _next_page(driver, wait):
            break
        page += 1


def _worker(queries, output_dir, downloaded, lock, driver_path, tag):
    driver = _setup_driver(driver_path)
    wait = WebDriverWait(driver, _WAIT_S)
    print(f"[{tag}] Browser started ({len(queries)} queries).")

    try:
        driver.get(_JAIL_URL)
        wait.until(EC.element_to_be_clickable((By.ID, "inmate")))

        for query in queries:
            try:
                if _submit_search(driver, wait, query):
                    _process_results(driver, wait, query, output_dir, downloaded, lock, tag)
                else:
                    print(f"[{tag}] No results for '{query}'")
            except Exception as e:
                print(f"[{tag}] Error on '{query}': {e}")
                try:
                    driver.get(_JAIL_URL)
                    wait.until(EC.element_to_be_clickable((By.ID, "inmate")))
                except Exception:
                    break
    finally:
        driver.quit()
        print(f"[{tag}] Done.")


def _fetch_recent_names(local_pdf_path):
    """Download the bookings PDF if updated; return deduplicated inmate names."""
    try:
        resp = requests.head(_PDF_URL, timeout=10)
    except requests.RequestException as e:
        print(f"Could not reach PDF: {e}")
        return []

    online_ts = None
    if 'Last-Modified' in resp.headers:
        online_ts = datetime.strptime(resp.headers['Last-Modified'], "%a, %d %b %Y %H:%M:%S GMT")

    local_ts = (datetime.utcfromtimestamp(os.path.getmtime(local_pdf_path))
                if os.path.exists(local_pdf_path) else None)

    if not (online_ts and (local_ts is None or online_ts > local_ts)):
        print("PDF is up-to-date. No new bookings.")
        return []

    print("Newer PDF found. Downloading...")
    r = requests.get(_PDF_URL, stream=True, timeout=30)
    with open(local_pdf_path, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    pdf = fitz.open(local_pdf_path)
    text = "".join(pdf.load_page(i).get_text("text") for i in range(pdf.page_count))
    pdf.close()

    text = re.sub(r'\b[A-Za-z ]+,\s*FL\b', '', text)
    text = re.sub(r'\s+', ' ', text)
    names = re.findall(r'\b([A-Z]+,\s+[A-Z]+(?:\s+[A-Z]+)?)\b', text)
    return list(dict.fromkeys(names))


def _chunk(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def download(output_dir, mode='recent', local_pdf_path=None, workers=3):
    """Download Orange County (FL) mugshots via parallel Selenium browsers.

    mode='recent'  -- parse the new-bookings PDF for names, search each one
    mode='all'     -- search A-Z and collect every result per letter
    workers        -- number of parallel browser instances (default 3)
    """
    if local_pdf_path is None:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from config import LOCAL_PDF_PATH
        local_pdf_path = LOCAL_PDF_PATH

    os.makedirs(output_dir, exist_ok=True)
    manifest_path = os.path.join(output_dir, 'manifest_orange.json')
    downloaded = load_manifest(manifest_path)
    lock = threading.Lock()

    if mode == 'recent':
        queries = _fetch_recent_names(local_pdf_path)
        if not queries:
            return
    else:
        queries = [chr(i) for i in range(ord('A'), ord('Z') + 1)]

    driver_path = ChromeDriverManager().install()
    n = min(workers, len(queries))
    chunks = _chunk(queries, n)
    print(f"Starting {n} browser(s) for {len(queries)} queries...")

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [
            pool.submit(_worker, chunk, output_dir, downloaded, lock,
                        driver_path, f"W{i + 1}")
            for i, chunk in enumerate(chunks)
        ]
        for f in futures:
            f.result()

    save_manifest(manifest_path, downloaded)
    print(f"Orange County download complete. Total in manifest: {len(downloaded)}")
