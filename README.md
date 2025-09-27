# 📊 Smart Business Insights Dashboard

**Live demo:** _[Render URL](https://smart-business-insights.onrender.com/)_  

Team: **Aya El Hajj • Batoul Hachem • Joud Senan**

---

## 💡 Problem & Goal
Retail teams collect lots of sales data but struggle to quickly see:
- What drove revenue/profit this month  
- Which products are winners vs. laggards  
- How branches/regions compare  
- What to stock/discount next month

**Smart Business Insights** ingests a CSV and instantly returns **KPIs, top/low products, and concrete next-month actions**. A built-in chat assistant answers business questions.

---

## 🗂️ Dataset & Expected Columns
Upload a CSV with these headers (synonyms are auto-mapped, e.g. `sales→revenue`, `qty→quantity`, `date→order_date`):

- `order_id`, `order_date`, `store_id`, `region`, `sales_channel`  
- `product_id`, `category`, `subcategory`, `product_name`  
- `unit_price`, `quantity`, `discount_rate`, `revenue`, `cost`, `profit`  
- `payment_method`, `customer_id`, `customer_segment`, `promo_code`  
- `is_return`, `return_date`  
- *(optional)* `inventory`

> Don’t have data? Generate a sample via `tools/make_sample_csv.py` (see below).

---

## 🧱 Approach & Architecture
**Backend (FastAPI):**
- `POST /analyze` (multipart): parses CSV, normalizes headers, computes KPIs, top/low products, simple trends, and **recommendations**.
- `POST /chat` (JSON): Mistral LLM if `MISTRAL_API_KEY` is set; otherwise a deterministic business fallback.
- `GET /health`: healthcheck.
- `GET /`: serves the same-origin web UI.

**Frontend (no framework):**  
Static HTML/CSS/JS served by FastAPI. Upload CSV → render KPIs & tables → ask the assistant. Same-origin avoids CORS issues.

**Resilience & Data Cleaning:**  
- Flexible header synonyms and robust numeric parsing (`$1,234.50`, `1.234,56`, `(123.45)`), flexible dates, boolean returns.  
- Sensible fallbacks when columns are missing.

---

## 🚀 Run Locally (Python)
```bash
# 1) Env & deps
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install fastapi uvicorn pydantic requests pandas numpy python-multipart

# 2) (Optional) set your Mistral key for chat
# PowerShell:
$env:MISTRAL_API_KEY="sk-..." 
# macOS/Linux:
# export MISTRAL_API_KEY=sk-...

# 3) Start
uvicorn app:app --reload --port 8000
# Open http://127.0.0.1:8000  (docs at /docs)
```

> **Tip:** Open the UI from FastAPI (`:8000`), not from Live Server (`:5500`).  
> If you insist on Live Server, set `const API = "http://127.0.0.1:8000"` in `static/app.js`.

---

## 🐳 Run with Docker
**Option A – Single container**
```bash
# .env (next to Dockerfile)
# MISTRAL_API_KEY=sk-...   # optional
# PORT=8000

docker build -t smart-insights .
docker run --rm -p 8000:8000 --env-file .env smart-insights
# http://localhost:8000
```

**Option B – Docker Compose**
```yaml
# compose.yml
services:
  app:
    build: .
    ports:
      - "${PORT:-8000}:8000"
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - PORT=8000
    restart: unless-stopped
```
```bash
docker compose up --build
```

---

## 🌐 Online Deployment (Render)
1. Push this repo to GitHub (include `Dockerfile` at the root).  
2. Render → **New → Web Service** → **Environment: Docker** → select your repo/branch.  
3. **Env vars:** `PORT=8000`, optional `MISTRAL_API_KEY=sk-...` (no quotes).  
4. Create/Deploy. When status is **Live**, open your URL.  
   - Health: `/health` → `{"status":"ok","version":"1.6.0"}`
   - Docs: `/docs`  
   - UI: `/`

Add your Render URL to the top of this README.

---

## 🔌 API Reference (quick)
**Analyze**
```bash
curl -s -F "file=@sample_sales.csv" https://YOUR-URL/analyze | jq .
```

**Chat**
```bash
curl -s -X POST -H "Content-Type: application/json"   -d '{"question":"Which SKUs should we restock next month?"}'   https://YOUR-URL/chat | jq .
```

**Health**
```bash
curl -s https://YOUR-URL/health
```

---

## 📈 Output Overview
- **KPIs:** total_revenue, total_profit, gross_margin, orders, customers, avg_order_value  
- **Top/Low Products:** by profit and by quantity (top 5 each)  
- **Recommendations:** restock fast movers, discount/bundle tails, manage excess inventory, adjust purchasing to 30-day demand trend

*(Charts are optional; the UI focuses on KPIs & tables for speed.)*

---

## 🧪 Sample Data Generator
```bash
python tools/make_sample_csv.py
# Produces sample_sales.csv (≈500 rows) to upload in the UI
```

---

## 🧷 Project Structure
```
smart-business-insights/
├─ app.py
├─ requirements.txt
├─ Dockerfile
├─ compose.yml
├─ .env.example
├─ README.md
├─ static/
│  ├─ index.html
│  ├─ styles.css
│  └─ app.js
└─ tools/
   └─ make_sample_csv.py
```

---

## 🔐 Security & Notes
- Never hardcode API keys; use environment variables or cloud secrets.
- CORS is open for dev; same-origin UI means no CORS in deployment.
- The app provides helpful business guidance; it avoids medical/legal advice by design.

---

## 🧩 Submission Checklist
- [x] **Dockerized** (Dockerfile, optional compose)  
- [x] **API** serving core logic (`/analyze`, `/chat`, `/health`)  
- [x] **UI** (same-origin web)  
- [x] **Online Deployment** (Render URL)  
- [x] **Public GitHub Repo** with clean README and commented code

---

## 📝 License
MIT — feel free to use and adapt with attribution.
