#!/usr/bin/env python3
"""
NSW Planning Portal – File Downloader  (Flask Backend)
=======================================================
Serves the frontend and acts as a CORS-bypass proxy for
the NSW Planning Portal website.

Routes:
  GET  /            -> index.html (frontend UI)
  GET  /health      -> {"status":"ok","version":"4.0"}
  POST /fetch-page  -> fetch remote HTML page server-side
  POST /fetch-file  -> fetch remote binary file, return base64

Deploy: push to GitHub, connect to Render.com (free tier).
"""

import os, base64, re
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings (we disable verification to handle edge-case cert issues)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)
CORS(app)  # Allow all origins — needed for local dev if frontend is served separately

# ── Browser-like headers sent with every outbound request ────────────────────
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language":   "en-AU,en-GB;q=0.9,en;q=0.8",
    "Accept-Encoding":   "identity",   # plain text — avoids decompression complexity
    "Cache-Control":     "no-cache",
    "Pragma":            "no-cache",
    "Sec-Fetch-Dest":    "document",
    "Sec-Fetch-Mode":    "navigate",
    "Sec-Fetch-Site":    "none",
    "Upgrade-Insecure-Requests": "1",
}

FILE_HEADERS = {
    **BROWSER_HEADERS,
    "Accept":     "application/pdf,application/octet-stream,*/*;q=0.8",
    "Referer":    "https://www.planningportal.nsw.gov.au/",
    "Sec-Fetch-Dest": "document",
}


# ── Frontend ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "4.0"})


# ── Fetch page ────────────────────────────────────────────────────────────────
@app.route("/fetch-page", methods=["POST", "OPTIONS"])
def fetch_page():
    if request.method == "OPTIONS":
        return _preflight()

    data = request.get_json(force=True, silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing 'url' field"}), 400

    print(f"[FETCH-PAGE]  {url}")
    try:
        resp = requests.get(
            url,
            headers=BROWSER_HEADERS,
            timeout=30,
            verify=False,
            allow_redirects=True,
        )
        # Detect encoding — requests uses apparent_encoding as fallback
        encoding = resp.encoding or resp.apparent_encoding or "utf-8"
        try:
            text = resp.content.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            text = resp.content.decode("utf-8", errors="replace")

        print(f"  OK  {len(text):,} chars  status={resp.status_code}  enc={encoding}")
        return jsonify({"html": text, "url": str(resp.url)})

    except Exception as e:
        print(f"  ERROR  {e}")
        return jsonify({"error": str(e)}), 500


# ── Fetch file ────────────────────────────────────────────────────────────────
@app.route("/fetch-file", methods=["POST", "OPTIONS"])
def fetch_file():
    if request.method == "OPTIONS":
        return _preflight()

    data = request.get_json(force=True, silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing 'url' field"}), 400

    print(f"[FETCH-FILE]  {url}")
    try:
        resp = requests.get(
            url,
            headers=FILE_HEADERS,
            timeout=60,
            verify=False,
            allow_redirects=True,
            stream=True,
        )
        raw = resp.content

        # Extract filename from Content-Disposition header
        cd       = resp.headers.get("Content-Disposition", "")
        filename = None
        m = re.search(r'filename\*?=["']?(?:UTF-8'')?([^"'
;]+)', cd, re.I)
        if m:
            from urllib.parse import unquote
            filename = unquote(m.group(1).strip().strip('"''))

        if not filename:
            from urllib.parse import urlparse, unquote
            path     = urlparse(str(resp.url)).path
            filename = unquote(path.split("/")[-1]) or "document.pdf"

        print(f"  OK  {len(raw):,} bytes  →  {filename}")
        return jsonify({
            "data":     base64.b64encode(raw).decode("ascii"),
            "filename": filename,
            "size":     len(raw),
        })

    except Exception as e:
        print(f"  ERROR  {e}")
        return jsonify({"error": str(e)}), 500


# ── CORS preflight helper ─────────────────────────────────────────────────────
def _preflight():
    from flask import Response
    r = Response()
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r, 204


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("\n" + "═"*56)
    print("  NSW Planning Portal – File Downloader  v4.0")
    print("═"*56)
    print(f"  URL:  http://0.0.0.0:{port}")
    print("  Stop: Ctrl+C")
    print("═"*56 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
