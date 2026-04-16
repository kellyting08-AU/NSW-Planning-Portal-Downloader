# NSW Planning Portal – File Downloader

A hosted web tool that downloads all documents from any NSW Major Planning Portal
project page and packages them into a structured ZIP file — one subfolder per
document group, matching the portal layout exactly.

---

## 🚀 Deploy to Render (Free — 2 minutes, no credit card)

### Step 1 — Push to GitHub
Upload this entire folder to a new GitHub repository.

### Step 2 — Create a free Render account
Sign up at [render.com](https://render.com) — no credit card required.

### Step 3 — Deploy
1. In the Render Dashboard, click **New → Web Service**
2. Connect your GitHub account and select your repository
3. Render auto-detects settings from `render.yaml`
4. Click **Create Web Service**
5. Wait ~2 minutes for the build to complete
6. Your tool is live at `https://your-app-name.onrender.com` ✅

### Step 4 — Share with your team
Send everyone the URL. No setup, no install — just open and use.

---

## 💡 How It Works

```
Browser  →  POST /fetch-page  →  Flask  →  planningportal.nsw.gov.au
                                              (with browser headers)
Browser  ←  HTML with __NEXT_DATA__ JSON  ←  Flask

Browser parses document groups from JSON
Browser  →  POST /fetch-file  →  Flask  →  download each file
Browser  ←  base64 binary  ←  Flask

Browser builds ZIP with JSZip → FileSaver triggers download
```

The Flask server acts as a **CORS-bypass proxy** — it fetches NSW Planning Portal
pages with full browser-like headers, which bypasses the portal's Cloudflare
protection that blocks direct browser requests.

---

## 📦 Output ZIP Structure

```
320-badgerys-creek-road-warehouse-estate_documents.zip
└── 320-badgerys-creek-road-warehouse-estate/
    ├── Early Consultation/
    │   └── document.pdf
    └── Request for SEARs/
        ├── file1.pdf
        ├── file2.pdf
        └── file3.pdf
```

---

## 🛠 Local Development

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:10000
```

---

## 📁 File Structure

```
├── app.py              # Flask backend + proxy server
├── requirements.txt    # Python dependencies
├── Procfile            # Gunicorn start command for Render
├── render.yaml         # Render deployment config
├── templates/
│   └── index.html      # Frontend web UI
└── README.md
```

---

## ⚙️ Stack

| Component | Technology |
|-----------|-----------|
| Backend   | Python / Flask |
| Proxy     | requests (with browser headers) |
| Server    | Gunicorn |
| Frontend  | Vanilla JS + JSZip + FileSaver.js |
| Hosting   | Render.com (free tier) |

---

## ⚠️ Notes

- Only works with **publicly accessible** project pages on the NSW Planning Portal
- No login credentials are required, stored, or transmitted
- Render's free tier may have a ~1 min cold start after 15 mins of inactivity
  (upgrade to a paid tier for always-on performance)
- The tool reads only public data — no scraping of private or authenticated content
