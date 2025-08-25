#!/usr/bin/env python3
"""
download_all_cba_pdfs_v2.py

1) Downloads a curated list of CommBank PDF documents (product brochures, PDS, TMDs, fees).
2) Crawls seed pages to discover additional PDF links.
3) Saves files to data/cba_pdfs/ and writes data/cba_pdfs/manifest.csv.

Run:
  python download_pdfs.py
"""
import os
import time
import csv
import hashlib
import logging
from urllib.parse import urlparse, urljoin
from collections import deque

import requests
from bs4 import BeautifulSoup

# ---------- Config ----------
ROOT_DOMAIN = "commbank.com.au"
SAVE_DIR = "cba-chatbot/data/cba_pdfs"
MANIFEST = os.path.join(SAVE_DIR, "manifest.csv")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
TIMEOUT = 30
RETRIES = 2
POLITE_DELAY = 1.0
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB safety
MAX_CRAWL_PAGES = 200
MAX_PDFS = 500

# Working, publicly accessible CBA PDFs (verified)
WORKING_PDFS = [
    # Product brochures and fees
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/smart-access-account-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/everyday-account-brochure.pdf", 
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/student-options-account-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/netbank-saver-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/saver-account-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/goal-saver-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/term-deposits-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/transaction-savings-fees-charges.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/credit-card-fees-charges.pdf",
    
    # Additional working URLs
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/streamline-basic-account-brochure.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/streamline-basic-account-fees-charges.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/banking/2023-10/streamline-basic-account-terms-conditions.pdf",
    
    # Insurance documents
    "https://www.commbank.com.au/content/dam/commbank-assets/insurance/docs/car-insurance-premium-excess-discount-guide.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/insurance/docs/home-insurance-premium-excess-discount-guide.pdf",
    
    # Investment documents  
    "https://www.commbank.com.au/content/dam/commbank-assets/investing/geared-investments/gi-loan-product-disclosure-statement.pdf",
    "https://www.commbank.com.au/content/dam/commbank-assets/investing/geared-investments/gi-loan-terms-conditions.pdf",
]

# Seed pages for crawling (focus on working sections)
SEED_PAGES = [
    "https://www.commbank.com.au/personal/accounts.html",
    "https://www.commbank.com.au/personal/credit-cards.html", 
    "https://www.commbank.com.au/personal/insurance.html",
    "https://www.commbank.com.au/personal/home-loans.html",
    "https://www.commbank.com.au/personal/investing.html",
    "https://www.commbank.com.au/business/accounts.html",
    "https://www.commbank.com.au/business/credit-cards.html",
    "https://www.commbank.com.au/business/insurance.html",
]

# ----------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})


def ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name or not name.lower().endswith('.pdf'):
        name = sha256_bytes(url.encode())[:8] + ".pdf"
    return name.split("?")[0].split("#")[0]


def manifest_has_sha(sha: str):
    if not os.path.exists(MANIFEST):
        return None
    try:
        with open(MANIFEST, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("sha256") == sha:
                    return r.get("saved_filename")
    except Exception:
        pass
    return None


def append_manifest_row(row: dict):
    write_header = not os.path.exists(MANIFEST)
    try:
        with open(MANIFEST, "a", encoding="utf-8", newline="") as f:
            fields = [
                "source_url", "pdf_url", "saved_filename", "filesize_bytes",
                "sha256", "http_status", "title_text", "timestamp",
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        logging.warning("Failed to write manifest: %s", e)


def download_pdf(url: str, source_page: str = "") -> bool:
    try:
        # Quick HEAD check
        head = session.head(url, allow_redirects=True, timeout=TIMEOUT)
        if head.status_code >= 400:
            logging.warning("HEAD returned %s for %s", head.status_code, url)
            return False
            
        content_length = head.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            logging.warning("Skipping %s due to size limit (%s)", url, content_length)
            return False
            
    except Exception as e:
        logging.debug("HEAD failed for %s: %s", url, e)
        # Continue with download attempt

    for attempt in range(1, RETRIES + 1):
        try:
            time.sleep(POLITE_DELAY)
            r = session.get(url, stream=True, timeout=TIMEOUT)
            if r.status_code != 200:
                logging.warning("GET returned %s for %s", r.status_code, url)
                return False
                
            # Stream download with size check
            chunks = []
            total = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > MAX_FILE_SIZE:
                        logging.warning("Aborting %s (size>%s)", url, MAX_FILE_SIZE)
                        return False
                        
            data = b"".join(chunks)
            sha = sha256_bytes(data)
            
            # Check if we already have this file
            existing = manifest_has_sha(sha)
            if existing:
                logging.info("Already have file (sha match): %s -> %s", url, existing)
                append_manifest_row({
                    "source_url": source_page, "pdf_url": url,
                    "saved_filename": existing, "filesize_bytes": len(data),
                    "sha256": sha, "http_status": r.status_code,
                    "title_text": "", "timestamp": int(time.time())
                })
                return True
                
            # Save new file
            filename = safe_filename_from_url(url)
            save_name = f"{sha[:8]}_{filename}"
            save_path = os.path.join(SAVE_DIR, save_name)
            
            with open(save_path, "wb") as f:
                f.write(data)
                
            logging.info("Saved %s (%d bytes)", save_name, len(data))
            
            append_manifest_row({
                "source_url": source_page, "pdf_url": url,
                "saved_filename": save_name, "filesize_bytes": len(data),
                "sha256": sha, "http_status": r.status_code,
                "title_text": "", "timestamp": int(time.time())
            })
            return True
            
        except Exception as e:
            logging.warning("Attempt %s failed for %s: %s", attempt, url, e)
            if attempt < RETRIES:
                time.sleep(2)
                
    logging.error("All attempts failed for %s", url)
    return False


def extract_pdf_links_from_html(base_url: str, html: str):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf") or "application/pdf" in (a.get("type") or ""):
            full = urljoin(base_url, href)
            if full.startswith("https://www.commbank.com.au"):
                links.add((full, (a.get_text() or "").strip()))
                
    return links


def crawl_seed_pages_and_collect(seed_pages):
    q = deque(seed_pages)
    visited = set()
    discovered = set()
    pages = 0
    
    while q and pages < MAX_CRAWL_PAGES and len(discovered) < MAX_PDFS:
        page = q.popleft()
        if page in visited:
            continue
            
        visited.add(page)
        pages += 1
        
        try:
            time.sleep(POLITE_DELAY)
            resp = session.get(page, timeout=TIMEOUT)
            
            if resp.status_code != 200:
                logging.warning("Skipping page %s (status %s)", page, resp.status_code)
                continue
                
            ct = resp.headers.get("Content-Type", "")
            if "text/html" not in ct:
                continue
                
            # Extract PDF links
            for link, text in extract_pdf_links_from_html(page, resp.text):
                if link not in discovered:
                    discovered.add((link, text, page))
                    
            # Find more pages to crawl (heuristic)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(page, a["href"].strip())
                parsed = urlparse(href)
                
                if (parsed.hostname and parsed.hostname.endswith(ROOT_DOMAIN) and
                    any(p in parsed.path.lower() for p in ["/personal", "/business", "/important-info", "/content/dam"])):
                    if href not in visited and href not in q:
                        q.append(href)
                        
        except Exception as e:
            logging.warning("Failed to fetch/crawl %s: %s", page, e)
            
    return list(discovered)


def main():
    ensure_save_dir()
    
    # Download working PDFs first
    logging.info("Starting downloads of %d working PDFs...", len(WORKING_PDFS))
    success_count = 0
    
    for url in WORKING_PDFS:
        if download_pdf(url, source_page="working_list"):
            success_count += 1
            
    logging.info("Downloaded %d/%d working PDFs", success_count, len(WORKING_PDFS))
    
    # Crawl for additional PDFs
    logging.info("Crawling seed pages for more PDFs...")
    found = crawl_seed_pages_and_collect(SEED_PAGES)
    logging.info("Found %d PDF links during crawl", len(found))
    
    crawl_success = 0
    for (link, text, page) in found:
        if download_pdf(link, source_page=page):
            crawl_success += 1
            
    logging.info("Downloaded %d/%d crawled PDFs", crawl_success, len(found))
    logging.info("Done. Total files: %d. See manifest: %s", success_count + crawl_success, MANIFEST)


if __name__ == "__main__":
    main()

