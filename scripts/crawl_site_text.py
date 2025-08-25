#!/usr/bin/env python3
"""
Fast crawl commbank.com.au key sections and save cleaned page text under data/site_text.
- Aggressive crawling with minimal delays
- Saves each page's main visible text to a .txt file
- Writes manifest.csv with URL -> filename mapping

Run:
  python scripts/crawl_site_text.py
"""
import os
import re
import csv
import time
import hashlib
import logging
from urllib.parse import urlparse, urljoin
from collections import deque

import requests
from bs4 import BeautifulSoup

ROOT_DOMAIN = "commbank.com.au"
SEED_PAGES = [
	"https://www.commbank.com.au/personal.html",
	"https://www.commbank.com.au/personal/accounts.html",
	"https://www.commbank.com.au/personal/credit-cards.html",
	"https://www.commbank.com.au/personal/insurance.html",
	"https://www.commbank.com.au/personal/home-loans.html",
	"https://www.commbank.com.au/personal/investing.html",
	"https://www.commbank.com.au/business.html",
	"https://www.commbank.com.au/business/accounts.html",
	"https://www.commbank.com.au/business/merchant-services.html",
	"https://www.commbank.com.au/business/loans-and-finance.html",
]
SAVE_DIR = "cba-chatbot/data/site_text"
MANIFEST = os.path.join(SAVE_DIR, "manifest.csv")
MAX_PAGES = 500  # Reduced for speed
REQUEST_TIMEOUT = 10  # Reduced timeout
POLITE_DELAY = 0.1  # Minimal delay for speed
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
session = requests.Session()
session.headers.update({
	"User-Agent": USER_AGENT,
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Connection": "keep-alive",
})


def ensure_dirs():
	os.makedirs(SAVE_DIR, exist_ok=True)


def sha256_hex(s: str) -> str:
	return hashlib.sha256(s.encode()).hexdigest()


def clean_text(html: str) -> str:
	soup = BeautifulSoup(html, "html.parser")
	# Remove scripts/styles/navs/footers
	for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
		tag.decompose()
	text = soup.get_text("\n")
	text = re.sub(r"\n\s*\n+", "\n\n", text)
	text = text.strip()
	return text


def save_page_text(url: str, text: str) -> str:
	file_id = sha256_hex(url)[:16]
	filename = f"{file_id}.txt"
	path = os.path.join(SAVE_DIR, filename)
	with open(path, "w", encoding="utf-8", errors="ignore") as f:
		# Write URL on first line for traceability
		f.write(url + "\n\n" + text)
	return filename


def append_manifest(url: str, filename: str):
	write_header = not os.path.exists(MANIFEST)
	with open(MANIFEST, "a", encoding="utf-8", newline="", errors="ignore") as f:
		writer = csv.DictWriter(f, fieldnames=["url", "filename"]) 
		if write_header:
			writer.writeheader()
		writer.writerow({"url": url, "filename": filename})


def should_follow(url: str) -> bool:
	p = urlparse(url)
	if not p.scheme.startswith("http"):
		return False
	if not (p.hostname and p.hostname.endswith(ROOT_DOMAIN)):
		return False
	# Focus on main product pages only
	good = ["/personal", "/business", "/content/dam", "/important-info"]
	if not any(p in p.path.lower() for p in good):
		return False
	# Avoid obvious non-content paths
	bad = ["/privacy", "/careers", "/security", "/about-us", "/newsroom", "/site-map", "/legal", "/contact"]
	if any(b in p.path.lower() for b in bad):
		return False
	return True


def crawl():
	ensure_dirs()
	visited = set()
	q = deque(SEED_PAGES)
	count = 0
	
	print("Starting fast crawl...")
	
	while q and count < MAX_PAGES:
		url = q.popleft()
		if url in visited:
			continue
		visited.add(url)
		
		try:
			time.sleep(POLITE_DELAY)
			resp = session.get(url, timeout=REQUEST_TIMEOUT)
			
			if resp.status_code != 200:
				continue
			if "text/html" not in resp.headers.get("Content-Type", ""):
				continue
				
			text = clean_text(resp.text)
			if len(text) < 100:  # Reduced minimum text length
				continue
				
			filename = save_page_text(url, text)
			append_manifest(url, filename)
			count += 1
			
			print(f"[{count}] Saved: {url}")
			
			# Enqueue links (limited for speed)
			if count < MAX_PAGES:
				soup = BeautifulSoup(resp.text, "html.parser")
				links_added = 0
				for a in soup.find_all("a", href=True):
					if links_added >= 20:  # Limit links per page
						break
					href = a["href"].strip()
					next_url = urljoin(url, href)
					if should_follow(next_url) and next_url not in visited and next_url not in q:
						q.append(next_url)
						links_added += 1
						
		except Exception as e:
			print(f"Error crawling {url}: {e}")
			continue
			
	logging.info("Saved %d pages to %s", count, SAVE_DIR)
	print(f"✅ Crawl complete. {count} pages saved.")
	print(f"Data stored in: {SAVE_DIR}/")


if __name__ == "__main__":
	crawl()
