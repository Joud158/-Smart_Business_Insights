# app.py
"""
Business Sales Insights API (v1.6)
Run:
  uvicorn app:app --reload --port 8000
Install:
  pip install fastapi uvicorn pydantic requests pandas numpy python-multipart
Env (optional):
  set MISTRAL_API_KEY=your_key   # Windows (cmd)
  export MISTRAL_API_KEY=your_key # macOS/Linux
"""
from __future__ import annotations

import io
import os
from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ------------------------
# App & CORS
# ------------------------
app = FastAPI(title="Business Sales Insights API", version="1.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-friendly; lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend from ./static
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def _index():
    index_path = "static/index.html"
    if not os.path.exists(index_path):
        return JSONResponse({"error": "static/index.html not found"}, status_code=404)
    return FileResponse(index_path)

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.6.0"}

# ------------------------
# Models (I/O)
# ------------------------
class MistralRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="(Ignored) API key is pinned on server")
    question: str = Field(..., description="User's question")

class ChatResponse(BaseModel):
    reply: str

class AnalyzeResponse(BaseModel):
    meta: Dict[str, Any]
    kpis: Dict[str, Any]
    top_bottom: Dict[str, Any]
    trends: Dict[str, Any]
    recommendations: List[str]

# ------------------------
# Prompt engineering (chat)
# ------------------------
ROLE = "You are a friendly, precise assistant for quick, factual guidance about business: sales, finance, marketing, operations, inventory, strategy, analytics."
TASK = (
    "Answer questions, give suggestions, and propose the best plan for the next month by analyzing previous sales when available. "
    "If the question is generic business (no data), rely on best practices and simple calculations the user can try."
)
CONSTRAINTS = "Do not fabricate references. If unsure, say so briefly. Avoid medical/legal advice. Keep answers under 500 words when possible."
STYLE = "Tone: warm, concise, non-patronizing. Prefer bullets. Define terms briefly if helpful."
OUTPUT_FORMAT = (
    "Answer using this structure:\n"
    "1) Direct answer (2-4 sentences)\n"
    "2) Optional bullets (max 5)\n"
    "3) One follow-up question on user intent"
)
SYSTEM_PROMPT = f"{ROLE}\n\nTask:\n{TASK}\n\nConstraints:\n{CONSTRAINTS}\n\nStyle:\n{STYLE}\n\nOutput format:\n{OUTPUT_FORMAT}\n\n"

memory = [
    "User prefers concise, technical explanations.",
    "User is comfortable with bullet points.",
]
history: deque[Dict[str, str]] = deque(maxlen=6)

BUSINESS_TERMS = set(map(str.lower, [
    "business","sales","profit","revenue","margin","gross margin","net income","marketing","pricing","discount",
    "inventory","logistics","supply chain","operations","budget","forecast","cash flow","accounts payable",
    "accounts receivable","balance sheet","income statement","p&l","roi","ltv","cac","retention","churn",
    "kpi","benchmark","promotion","campaign","market","segmentation","funnel","conversion","lead","crm",
    "ecommerce","omnichannel","store","branch","region","category","sku","product","unit price","quantity",
    "cost of goods sold","cogs","profitability","growth","demand","seasonality","time series","forecasting",
    "staffing","scheduling","utilization","capacity","procurement","supplier","purchase order","purchase",
    "invoice","payment","pricing strategy","bundling","markdown","clearance","assortment","planogram",
    "b2b","b2c","saas","subscription","renewal","arpu","mrr","retail","wholesale","channel","gross profit",
    "aov","average order value","customer segment","region mix","store mix","promotion code","promo",
]))
def is_business_topic(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in BUSINESS_TERMS)

def business_nudge(text: str) -> str:
    if is_business_topic(text):
        return ""
    return (
        "\n\nNote: If the question isn’t about business, politely steer toward sales, costs, pricing, marketing, operations, or finance."
    )

# ------------------------
# /chat (Mistral) — env key & robust fallback
# ------------------------
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-tiny"
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()

def _fallback_business_reply(q: str) -> str:
    base = (
        "1) Based on typical practice: prioritize high-margin fast movers and align purchasing to last-30-day demand.\n"
        "2) Actions:\n"
        "• Compute AOV, margin%, top/low SKUs by profit & quantity.\n"
        "• Order cover = lead-time demand + safety stock (≈1–2× demand stdev).\n"
        "• Discount/bundle tails; promote items with high stock and healthy margin.\n"
        "3) Want me to analyze your CSV now and give store-specific recommendations?"
    )
    return base + (business_nudge(q) or "")

@app.post("/chat", response_model=ChatResponse)
def chat_with_mistral(req: MistralRequest):
    user_q = (req.question or "").strip()
    if not user_q:
        return ChatResponse(reply="Please type a business question (e.g., “Which SKUs should we restock for next month?”).")

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT + business_nudge(user_q)},
    ]
    if memory:
        mem_text = "Conversation memory:\n-" + "\n-".join(memory)
        messages.append({"role": "system", "content": mem_text})
    messages.extend(list(history))
    messages.append({"role": "user", "content": user_q})

    if not MISTRAL_API_KEY:
        out = _fallback_business_reply(user_q)
        history.append({"role": "user", "content": user_q})
        history.append({"role": "assistant", "content": out})
        return ChatResponse(reply=out)

    data = {"model": DEFAULT_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 500}
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}

    last_err = None
    for _ in range(2):
        try:
            resp = requests.post(MISTRAL_CHAT_URL, headers=headers, json=data, timeout=30)
            if resp.status_code >= 400:
                last_err = f"{resp.status_code} {resp.text}"
                continue
            payload = resp.json()
            output = payload.get("choices", [{}])[0].get("message", {}).get("content")
            if output:
                history.append({"role": "user", "content": user_q})
                history.append({"role": "assistant", "content": output})
                return ChatResponse(reply=output)
            last_err = "Empty response from model"
        except requests.RequestException as e:
            last_err = str(e)

    out = _fallback_business_reply(user_q) + (f"\n\n(Note: model fallback used: {last_err})" if last_err else "")
    history.append({"role": "user", "content": user_q})
    history.append({"role": "assistant", "content": out})
    return ChatResponse(reply=out)

@app.get("/chat/debug")
def chat_debug():
    return {
        "history_len": len(history),
        "has_api_key": bool(MISTRAL_API_KEY),
        "model": DEFAULT_MODEL,
    }

# ------------------------
# CSV analysis helpers
# ------------------------
REQUIRED_COLUMNS = [
    "order_id","order_date","store_id","region","sales_channel","product_id","category","subcategory","product_name",
    "unit_price","quantity","discount_rate","revenue","cost","profit","payment_method","customer_id","customer_segment",
    "promo_code","is_return","return_date",
]
OPTIONAL_COLUMNS = ["inventory"]

def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    norm = {c: c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns}
    df = df.rename(columns=norm)
    synonyms = {
        "orderid":"order_id","order_number":"order_id",
        "store":"store_id","branch":"store_id","storeid":"store_id",
        "product":"product_name","product_title":"product_name",
        "sub_category":"subcategory",
        "orderdate":"order_date","order_dt":"order_date","date":"order_date",
        "returndate":"return_date",
        "sales":"revenue","sales_amount":"revenue","amount":"revenue",
        "qty":"quantity","qnt":"quantity","quantity_ordered":"quantity",
        "price":"unit_price","unitprice":"unit_price",
        "discount":"discount_rate","discount_pct":"discount_rate","discount_percent":"discount_rate",
        "customerid":"customer_id","cust_id":"customer_id",
        "segment":"customer_segment",
        "inv":"inventory","stock":"inventory",
    }
    for k, v in synonyms.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})
    return df

def _parse_dates_flex(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    if s.isna().all():
        s = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return s

def _clean_numeric_col(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    neg_mask = s.str.match(r"^\(.*\)$", na=False)
    s = s.str.replace(r"[()]", "", regex=True)
    s = s.str.replace(r"[^0-9,\.\-]", "", regex=True)
    eu_mask = s.str.contains(",", regex=False) & ~s.str.contains(r"\.", regex=True)
    s = s.where(~eu_mask, s.str.replace(",", ".", regex=False))
    s = s.str.replace(",", "", regex=False)
    out = pd.to_numeric(s, errors="coerce")
    out[neg_mask] = -out[neg_mask]
    return out

def _parse_csv_to_df(upload: UploadFile) -> pd.DataFrame:
    try:
        content = upload.file.read()
        return pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {e}")

def _coerce_types_and_fill(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_headers(df)

    for col in ["order_date","return_date"]:
        if col in df.columns:
            df[col] = _parse_dates_flex(df[col]).dt.tz_localize(None)

    for col in ["unit_price","quantity","discount_rate","revenue","cost","profit","inventory"]:
        if col in df.columns:
            df[col] = _clean_numeric_col(df[col])

    if "discount_rate" in df.columns:
        df["discount_rate"] = df["discount_rate"].fillna(0.0)

    if "revenue" not in df.columns and {"unit_price","quantity"}.issubset(df.columns):
        df["revenue"] = df["unit_price"].fillna(0) * df["quantity"].fillna(0) * (1 - df.get("discount_rate", 0))
    if "unit_price" not in df.columns and {"revenue","quantity"}.issubset(df.columns):
        with np.errstate(divide='ignore', invalid='ignore'):
            df["unit_price"] = (df["revenue"] / df["quantity"]).replace([np.inf,-np.inf], np.nan)
    if "profit" not in df.columns and {"revenue","cost"}.issubset(df.columns):
        df["profit"] = df["revenue"].fillna(0) - df["cost"].fillna(0)

    if "is_return" in df.columns:
        if df["is_return"].dtype == object:
            df["is_return"] = df["is_return"].astype(str).str.lower().isin(["1","true","yes","y"])
        else:
            df["is_return"] = df["is_return"].astype(bool)

    return df

def _validate_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]

def _safe_div(a: float, b: float) -> float:
    try:
        return float(a) / float(b) if (b not in (0, 0.0, None, np.nan) and pd.notna(b)) else 0.0
    except Exception:
        return 0.0

def _kpis(df: pd.DataFrame) -> Dict[str, Any]:
    total_revenue = float(df.get("revenue", pd.Series(dtype=float)).sum(skipna=True))
    total_profit  = float(df.get("profit",  pd.Series(dtype=float)).sum(skipna=True))
    total_orders  = int(df.get("order_id", pd.Series(dtype=object)).nunique()) if "order_id" in df.columns else int(df.shape[0])
    total_customers = int(df.get("customer_id", pd.Series(dtype=object)).nunique()) if "customer_id" in df.columns else 0
    gross_margin = _safe_div(total_profit, total_revenue)
    avg_order_value = _safe_div(total_revenue, total_orders)
    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "gross_margin": round(gross_margin, 4),
        "orders": total_orders,
        "customers": total_customers,
        "avg_order_value": round(avg_order_value, 2),
    }

def _top_bottom(df: pd.DataFrame) -> Dict[str, Any]:
    if not {"product_id","product_name"}.issubset(df.columns):
        if "product_name" in df.columns and "product_id" not in df.columns:
            df = df.copy()
            df["product_id"] = df["product_name"].factorize()[0]
        else:
            return {"by_profit_top": [], "by_profit_low": [], "by_qty_top": [], "by_qty_low": []}

    agg = (
        df.groupby(["product_id","product_name"], dropna=False)
          .agg(
              revenue=("revenue","sum"),
              profit=("profit","sum"),
              qty=("quantity","sum"),
              avg_price=("unit_price","mean"),
              orders=("order_id","nunique") if "order_id" in df.columns else ("product_id","size"),
          )
          .reset_index()
    )
    return {
        "by_profit_top": agg.sort_values("profit", ascending=False).head(5).to_dict(orient="records"),
        "by_profit_low": agg.sort_values("profit", ascending=True ).head(5).to_dict(orient="records"),
        "by_qty_top":    agg.sort_values("qty",    ascending=False).head(5).to_dict(orient="records"),
        "by_qty_low":    agg.sort_values("qty",    ascending=True ).head(5).to_dict(orient="records"),
    }

def _trends(_df: pd.DataFrame) -> Dict[str, Any]:
    # Placeholder (UI currently table-only; keep API stable)
    return {"daily": [], "monthly": []}

def _simple_forecast_and_actions(df: pd.DataFrame) -> List[str]:
    recs: List[str] = []

    if {"order_date","revenue"}.issubset(df.columns):
        tmp = df.dropna(subset=["order_date"]).copy()
        tmp["order_date"] = pd.to_datetime(tmp["order_date"], errors="coerce")
        tmp = tmp.dropna(subset=["order_date"]).sort_values("order_date")
        if not tmp.empty:
            end = tmp["order_date"].max().normalize()
            last_30 = tmp[tmp["order_date"] > end - pd.Timedelta(days=30)]["revenue"].sum()
            prev_30 = tmp[(tmp["order_date"] <= end - pd.Timedelta(days=30)) & (tmp["order_date"] > end - pd.Timedelta(days=60))]["revenue"].sum()
            growth = _safe_div(last_30 - prev_30, prev_30) if prev_30 else 0.0
            if growth > 0.1:
                recs.append("Demand rising (~>10% MoM). Prepare extra stock for top movers and ensure supplier lead times are covered.")
            elif growth < -0.1:
                recs.append("Demand softening (~>10% drop). Tighten purchasing; focus promotions on high-margin, high-inventory items.")
            else:
                recs.append("Stable demand. Keep base assortment, adjust only on clear winners/laggards.")

    if {"product_name","quantity","profit"}.issubset(df.columns):
        pid = df.get("product_id", df["product_name"])
        prod = (
            df.assign(product_id=pid)
              .groupby(["product_id","product_name"], dropna=False)
              .agg(qty=("quantity","sum"), profit=("profit","sum")).reset_index()
        )
        if not prod.empty:
            q_qty = prod["qty"].quantile(0.75)
            winners = prod[(prod["qty"] >= q_qty) & (prod["profit"] > 0)].head(10)
            if not winners.empty:
                recs.append(
                    "Keep/increase stock for fast-moving profitable items: " +
                    ", ".join(winners["product_name"].astype(str).head(5)) + "."
                )
            q_low = prod["qty"].quantile(0.10)
            lag = prod[(prod["qty"] <= q_low) | (prod["profit"] < 0)].head(10)
            if not lag.empty:
                recs.append(
                    "Discount, bundle, or retire slow/low-margin items: " +
                    ", ".join(lag["product_name"].astype(str).head(5)) + "."
                )

    if "inventory" in df.columns:
        inv = (
            df.groupby(["product_id","product_name"], dropna=False)
              .agg(inventory=("inventory","max"), qty=("quantity","sum")).reset_index()
        )
        over = inv[(inv["inventory"] > 0) & (inv["qty"] == 0)].head(10)
        if not over.empty:
            recs.append(
                "Excess stock with no recent sales: consider clearance or new channels for " +
                ", ".join(over["product_name"].astype(str).head(5)) + "."
            )

    if not recs:
        recs.append("Data insufficient for strong guidance; ensure order_date, revenue, quantity, and profit are populated.")
    return recs

# ------------------------
# /analyze
# ------------------------
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_csv(
    file: UploadFile = File(..., description="CSV with sales data"),
    branch: Optional[str] = Query(None, description="Filter by store_id value"),
):
    if not file or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    df = _parse_csv_to_df(file)
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty CSV")

    df = _coerce_types_and_fill(df)
    missing = _validate_columns(df)

    if branch and "store_id" in df.columns:
        df = df[df["store_id"].astype(str) == str(branch)]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No rows found for store_id={branch}")

    kpis = _kpis(df) if {"revenue","profit"}.issubset(df.columns) else {}
    tb = _top_bottom(df)
    tr = _trends(df)
    recs = _simple_forecast_and_actions(df)

    meta = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "missing_required_columns": missing,
        "branch": branch,
    }
    return AnalyzeResponse(meta=meta, kpis=kpis, top_bottom=tb, trends=tr, recommendations=recs)
