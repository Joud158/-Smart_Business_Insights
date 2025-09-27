import csv, random, datetime as dt
from pathlib import Path

random.seed(7)
N = 500
stores = ["Store-1","Store-2","Store-3"]
regions = ["North","Central","South"]
cats = [("Electronics","Phones"),("Electronics","Audio"),
        ("Home","Kitchen"),("Home","Decor"),
        ("Sports","Fitness")]
channels = ["Online","Retail"]
pay = ["Card","Cash","Wallet"]
cust_segments = ["Consumer","Corporate","Small Business"]

start = dt.date.today() - dt.timedelta(days=120)

out = Path("sample_sales.csv")
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["order_id","order_date","store_id","region","sales_channel",
                "product_id","category","subcategory","product_name",
                "unit_price","quantity","discount_rate","revenue","cost","profit",
                "payment_method","customer_id","customer_segment","promo_code",
                "is_return","return_date","inventory"])
    for i in range(1, N+1):
        date = start + dt.timedelta(days=random.randint(0,119))
        store = random.choice(stores)
        region = random.choice(regions)
        channel = random.choice(channels)
        cat, sub = random.choice(cats)
        pid = f"P{random.randint(100,199)}"
        pname = f"{sub} {random.randint(1,20)}"
        price = round(random.uniform(5,200),2)
        qty = random.randint(1,5)
        disc = round(random.choice([0,0,0.05,0.1,0.15]),2)
        revenue = round(price*qty*(1-disc),2)
        cost = round(revenue*random.uniform(0.6,0.9),2)
        profit = round(revenue - cost, 2)
        paym = random.choice(pay)
        cid = f"C{random.randint(1000,1200)}"
        seg = random.choice(cust_segments)
        promo = random.choice(["","WINTER10","VIP5","NEW20",""])
        is_ret = random.choice([False, False, False, True])
        rdate = (date + dt.timedelta(days=random.randint(1,10))).isoformat() if is_ret else ""
        inv = random.randint(0,50)
        w.writerow([i,date.isoformat(),store,region,channel,
                    pid,cat,sub,pname,
                    price,qty,disc,revenue,cost,profit,
                    paym,cid,seg,promo,
                    "true" if is_ret else "false", rdate, inv])

print(f"Written {out.resolve()}")
