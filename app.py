#!/usr/bin/env python3
"""
NSW Planning Portal - File Downloader (Flask Backend v4.2)
Uses a requests Session with cookie warm-up to bypass bot detection.
"""

import os
import base64
import re
from urllib.parse import unquote, urlparse

from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

PORTAL_HOME = "https://www.planningportal.nsw.gov.au"

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
    "Accept-Language":           "en-AU,en-GB;q=0.9,en;q=0.8",
    "Accept-Encoding":           "identity",
    "Cache-Control":             "no-cache",
    "Pragma":                    "no-cache",
    "DNT":                       "1",
    "Connection":                "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":            "document",
    "Sec-Fetch-Mode":            "navigate",
    "Sec-Fetch-Site":            "none",
    "Sec-Fetch-User":            "?1",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile":          "?0",
    "sec-ch-ua-platform":        '"Windows"',
}

FILE_HEADERS = {
    **BROWSER_HEADERS,
    "Accept":         "application/pdf,application/octet-stream,*/*;q=0.8",
    "Referer":        "https://www.planningportal.nsw.gov.au/",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Dest": "document",
}


def make_session():
    """Create a session that visits the portal homepage first to get cookies."""
    session = requests.Session()
    session.verify = False
    try:
        print("  [session] warming up...")
        session.get(
            PORTAL_HOME,
            headers=BROWSER_HEADERS,
            timeout=15,
            allow_redirects=True,
        )
        print("  [session] warm-up done, cookies: " + str(dict(session.cookies)))
    except Exception as e:
        print("  [session] warm-up failed (continuing): " + str(e))
    return session


def is_cloudflare_block(html):
    """Return True if Cloudflare returned a challenge page instead of real content."""
    indicators = [
        "cf-browser-verification",
        "challenge-form",
        "Just a moment",
        "_cf_chl",
        "Checking your browser",
        "cf_clearance",
        "Please Wait... | Cloudflare",
        "cf-spinner",
    ]
    for indicator in indicators:
        if indicator in html:
            return True
    return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "4.2"})


@app.route("/fetch-page", methods=["POST", "OPTIONS"])
def fetch_page():
    if request.method == "OPTIONS":
        return _preflight()

    data = request.get_json(force=True, silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing url"}), 400

    print("[FETCH-PAGE] " + url)
    try:
        session = make_session()
        resp = session.get(
            url,
            headers=BROWSER_HEADERS,
            timeout=30,
            allow_redirects=True,
        )

        encoding = resp.encoding or resp.apparent_encoding or "utf-8"
        try:
            text = resp.content.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            text = resp.content.decode("utf-8", errors="replace")

        print("  OK " + str(len(text)) + " chars  status=" + str(resp.status_code))

        if is_cloudflare_block(text):
            return jsonify({
                "error": (
                    "The NSW Planning Portal blocked this request via Cloudflare. "
                    "Please try again in a few seconds."
                )
            }), 503

        return jsonify({"html": text, "url": str(resp.url)})

    except Exception as e:
        print("  ERROR " + str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/fetch-file", methods=["POST", "OPTIONS"])
def fetch_file():
    if request.method == "OPTIONS":
        return _preflight()

    data = request.get_json(force=True, silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing url"}), 400

    print("[FETCH-FILE] " + url)
    try:
        session = make_session()
        resp = session.get(
            url,
            headers=FILE_HEADERS,
            timeout=60,
            allow_redirects=True,
            stream=True,
        )
        raw = resp.content

        filename = None
        cd = resp.headers.get("Content-Disposition", "")
        m = re.search(r'filename[^;=\n]*=([^;\n]*)', cd, re.IGNORECASE)
        if m:
            filename = m.group(1).strip().strip('"\'')
            filename = unquote(filename)

        if not filename:
            path = urlparse(str(resp.url)).path
            filename = unquote(path.split("/")[-1])

        if not filename:
            filename = "document.pdf"

        print("  OK " + str(len(raw)) + " bytes -> " + filename)
        return jsonify({
            "data":     base64.b64encode(raw).decode("ascii"),
            "filename": filename,
            "size":     len(raw),
        })

    except Exception as e:
        print("  ERROR " + str(e))
        return jsonify({"error": str(e)}), 500


def _preflight():
    r = Response()
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r, 204


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("NSW Planning Portal - File Downloader v4.2")
    print("Running on port " + str(port))
    app.run(host="0.0.0.0", port=port, debug=False)
