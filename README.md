# ResumeIQ — AI Job Match Analyzer

AI-powered resume scorer and project improvement tool. Upload a resume + job description and get:

- **Overall match score** (0–100) with letter grade
- **5-dimension analysis** — Skills, Experience, Education, Keywords, Culture Fit
- **ATS score** + interview likelihood
- **Project-by-project rewrites** with before/after bullets, added keywords, and copy button
- **General resume tips** and missing project suggestions

Built with **Flask + Anthropic Claude**. Deploys to **Railway** in ~2 minutes.

---

## Quick Start (Local)

```bash
git clone https://github.com/YOUR_USERNAME/resumeiq.git
cd resumeiq
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...               # Windows: set ANTHROPIC_API_KEY=sk-ant-...
python app.py
```
Open http://localhost:5000

---

## Deploy to Railway

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/resumeiq.git
git push -u origin main
```

### Step 2 — Create Railway project
1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `resumeiq` repo

### Step 3 — Add environment variable
In Railway dashboard → your service → **Variables** tab:
```
ANTHROPIC_API_KEY = sk-ant-your-key-here
```

### Step 4 — Deploy
Railway auto-detects `Procfile` and deploys. Your app will be live at a `.up.railway.app` URL within ~60 seconds.

---

## Project Structure

```
resumeiq/
├── app.py                  # Flask backend — /analyze and /suggest endpoints
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command for Railway
├── railway.toml            # Railway deployment config
├── .gitignore
├── README.md
└── templates/
    └── index.html          # Full single-page UI (vanilla JS, no build step)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main UI |
| POST | `/analyze` | Resume vs JD match analysis |
| POST | `/suggest` | Project-by-project improvement suggestions |
| GET | `/health` | Health check for Railway |

Both POST endpoints accept `multipart/form-data` with:
- `resume_file` (PDF/DOCX/TXT) **or** `resume_text` (plain text)
- `job_file` (PDF/DOCX/TXT) **or** `job_text` (plain text)

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Your key from [console.anthropic.com](https://console.anthropic.com) |
| `PORT` | Auto | Set automatically by Railway |

---

## License

MIT
