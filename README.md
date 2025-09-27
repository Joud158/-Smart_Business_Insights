# 📊 Smart Business Insights Dashboard

## 💡 Idea
The Smart Business Insights Dashboard is an interactive tool designed to help retail managers and business analysts understand their sales data and make data-driven decisions. It provides clear visualizations of key metrics, trends, and patterns while also forecasting next-month sales to support strategic planning.

---

## 🗂️ Dataset
The dashboard accepts a CSV dataset uploaded by the user, containing detailed sales information. The key columns include:

- order_id  
- order_date  
- store_id  
- region  
- sales_channel (online or in-store)  
- product_id  
- category  
- subcategory  
- product_name  
- unit_price  
- quantity  
- discount  

This dataset captures both transactional details and general information about products and stores, which helps to have a meaningful analysis and comparisons across regions, categories, and time periods.

---

## ⚙️ Approach
1. Data Loading – The CSV file is uploaded by the user and read into the system for analysis.  
2. Preprocessing – Cleaning, parsing dates, and structuring the data to ensure consistency.  
3. Key Performance Indicators (KPIs) – Computation of business metrics such as:  
   - Total sales  
   - Total quantities sold  
   - Revenue per store  
   - Performance by region  
   - Product category analysis  
4. Recommendations – Providing AI-powered suggestions (via the Mistral LLM API) to help businesses optimize strategies, identify growth opportunities, and lower unnecessary purchases.  

---

## 🚀 Running and Testing it
Make sure that all the requirements are installed properly:  

```bash
pip install fastapi uvicorn pydantic requests pandas numpy python-multipart
```

1. Start backend:  
```bash
uvicorn app:app --reload --port 8000
```

2. Open the UI from FastAPI:  
```
http://127.0.0.1:8000/
```
> Note: Do not open with Live Server at :5500.  

3. Set in the PowerShell the API key:  
```powershell
$env:MISTRAL_API_KEY="sk-..."
```

---

