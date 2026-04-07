# 📧 Email Tracker — Newsletter Open Tracking System

A lightweight backend system to track email opens from newsletters sent via **Beehiiv**, storing data in **Google Sheets** and sending events to **Google Analytics 4 (GA4)**.

---

## 🎯 What This Project Does

Every time a subscriber opens your newsletter, this system:

- ✅ Captures the open event via a **tracking pixel**
- ✅ Saves the data in **Google Sheets** in real time
- ✅ Sends an `email_open` event to **Google Analytics GA4**
- ✅ Generates a **unique ID** per open for accurate user counting

---

## 🗺️ How It Works

```
Beehiiv Email
     ↓
Subscriber opens email
     ↓
Tracking pixel fires (1x1 invisible image)
     ↓
Backend server receives the request
     ↓
     ├── Saves row to Google Sheets
     └── Sends event to GA4
```

---

## 🧩 Tech Stack

| What | Tool |
|---|---|
| Language | Python 3 |
| Framework | FastAPI |
| Deployment | Vercel |
| Database | Google Sheets API |
| Analytics | Google Analytics 4 (Measurement Protocol) |
| Email Platform | Beehiiv |

---

## 📦 Project Structure

```
email-tracker/
├── main.py              # FastAPI app — main server logic
├── requirements.txt     # Python dependencies
├── vercel.json          # Vercel deployment configuration
├── .env.example         # Example environment variables
└── README.md            # This file
```

---

## 🚀 Getting Started

### 1 — Clone the Repository

```bash
git clone https://github.com/HudsonSilverio/email-tracker
cd email-tracker
```

### 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

### 3 — Set Up Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```
SHEET_ID=your-google-sheet-id
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=your-ga4-api-secret
ENVIRONMENT=development
```

### 4 — Add Google Credentials

Place your `credentials.json` file (Google Service Account) in the project root.

> ⚠️ Never commit this file to GitHub — it's already in `.gitignore`

### 5 — Run Locally

```bash
uvicorn main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

---

## 🔗 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check — returns `{"status": "ok"}` |
| `/track` | GET | Tracking pixel — saves open event |
| `/test-sheets` | GET | Tests Google Sheets connection |

---

## 🧪 Test the Tracking Pixel

Visit in your browser:

```
http://127.0.0.1:8000/track
```

Check your Google Sheet — a new row should appear with:

| Date | Time | UUID | User Agent |
|---|---|---|---|
| 2026-03-31 | 14:32:01 | a1b2c3d4-... | Mozilla/5.0... |

---

## 📧 Beehiiv Integration

Add this HTML Snippet block inside your Beehiiv email:

```html
<img src="https://your-domain.vercel.app/track" width="1" height="1" style="display:block;" />
```

> Replace `your-domain` with your actual Vercel deployment URL.

---

## ☁️ Deploy to Vercel

### Environment Variables to Add in Vercel Dashboard

| Variable | Description |
|---|---|
| `SHEET_ID` | Google Sheet ID from the URL |
| `GA4_MEASUREMENT_ID` | GA4 Measurement ID (G-XXXXXXXXXX) |
| `GA4_API_SECRET` | GA4 Measurement Protocol API Secret |
| `GOOGLE_CREDENTIALS_B64` | Base64-encoded contents of credentials.json |
| `ENVIRONMENT` | Set to `production` on Vercel |

### Generate GOOGLE_CREDENTIALS_B64

```python
import base64
with open('credentials.json', 'rb') as f:
    print(base64.b64encode(f.read()).decode('utf-8'))
```

---

## 🔒 Security

- `credentials.json` is in `.gitignore` — never pushed to GitHub
- `.env` is in `.gitignore` — never pushed to GitHub
- All secrets are stored as environment variables
- `ENVIRONMENT=development` disables GA4 events locally

---

## 📊 Google Sheets Setup

1. Create a new Google Sheet with these headers:

| Date | Time | UUID | User Agent |
|---|---|---|---|

2. Create a Google Cloud Service Account
3. Enable Google Sheets API
4. Share the sheet with the service account email (Editor access)
5. Download `credentials.json`

---

## 🌱 Environment Modes

| Mode | GA4 Events | Google Sheets |
|---|---|---|
| `development` | ❌ Disabled | ✅ Always saved |
| `production` | ✅ Enabled | ✅ Always saved |

---

## 📈 Future Improvements

- [ ] Add subscriber email tracking when Beehiiv supports merge tags in HTML
- [ ] Add campaign ID parameter per newsletter
- [ ] Add dashboard for open rate visualization
- [ ] Add webhook support for real-time alerts

---

## 👨‍💻 Author

Built by **Hudson Silverio**

---

## 📄 License

MIT License — feel free to use and modify this project.