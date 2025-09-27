const API = location.origin; // same-origin backend

const $ = (id) => document.getElementById(id);
const fmt = (n, d=2) => (n==null || isNaN(n)) ? "—" :
  Number(n).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});

function toast(msg, ms=2200){
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  setTimeout(()=>t.classList.remove("show"), ms);
}

function setKPIs(k) {
  $("k_revenue").textContent  = fmt(k?.total_revenue);
  $("k_profit").textContent   = fmt(k?.total_profit);
  $("k_margin").textContent   = (k?.gross_margin != null) ? `${(k.gross_margin*100).toFixed(1)}%` : "—";
  $("k_orders").textContent   = (k?.orders ?? "—");
  $("k_customers").textContent= (k?.customers ?? "—");
  $("k_aov").textContent      = fmt(k?.avg_order_value);
}

function fillTable(id, rows, order = ["product_id","product_name","profit","revenue","qty","avg_price","orders"]) {
  const tbody = document.querySelector(`#${id} tbody`);
  tbody.innerHTML = "";
  if (!rows || !rows.length) {
    const tr = document.createElement("tr"); const td = document.createElement("td");
    td.colSpan = order.length; td.textContent = "No data"; tr.appendChild(td); tbody.appendChild(tr); return;
  }
  rows.forEach(r => {
    const tr = document.createElement("tr");
    order.forEach(col => {
      const td = document.createElement("td"); let v = r[col];
      if (["profit","revenue","avg_price"].includes(col)) v = fmt(v);
      td.textContent = (v ?? "");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

$("analyze").onclick = async () => {
  const fileInput = $("csv"); const branch = $("branch").value.trim();
  if (!fileInput.files.length) { toast("Pick a CSV file"); return; }
  const fd = new FormData(); fd.append("file", fileInput.files[0], fileInput.files[0].name);
  const url = branch ? `${API}/analyze?branch=${encodeURIComponent(branch)}` : `${API}/analyze`;
  $("analyze").disabled = true; $("analyze").textContent = "Analyzing…";
  try {
    const res = await fetch(url, { method: "POST", body: fd });
    if(!res.ok){
      let errText = await res.text().catch(()=>res.statusText);
      throw new Error(errText || res.statusText);
    }
    const data = await res.json();
    setKPIs(data.kpis || {});
    fillTable("tbl_top_profit", data.top_bottom?.by_profit_top);
    fillTable("tbl_low_profit", data.top_bottom?.by_profit_low);
    fillTable("tbl_top_qty",    data.top_bottom?.by_qty_top,  ["product_id","product_name","qty","profit","revenue","avg_price","orders"]);
    fillTable("tbl_low_qty",    data.top_bottom?.by_qty_low,  ["product_id","product_name","qty","profit","revenue","avg_price","orders"]);
    const miss = (data?.meta?.missing_required_columns || []);
    $("meta").textContent = `Rows: ${data?.meta?.rows ?? "—"}${data?.meta?.branch ? " • branch=" + data.meta.branch : ""}${miss.length ? " • missing: " + miss.join(", ") : ""}`;
    toast(`Loaded ${data?.meta?.rows ?? "—"} rows`);
  } catch (e) {
    console.error(e);
    toast("Analyze failed");
    alert("Analyze failed:\n" + (e?.message || e));
  } finally {
    $("analyze").disabled = false; $("analyze").textContent = "Analyze";
  }
};

$("ask").onclick = async () => {
  const q = $("chatQ").value.trim();
  if (!q) { toast("Type a question"); return; }
  $("ask").disabled = true; $("ask").textContent = "Thinking…";
  try {
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q })
    });
    if(!res.ok){
      let errText = await res.text().catch(()=>res.statusText);
      throw new Error(errText || res.statusText);
    }
    const data = await res.json();
    $("chatReply").textContent = data.reply || "(no reply)";
  } catch (e) {
    console.error(e);
    $("chatReply").textContent = "Chat failed: " + (e?.message || e);
    toast("Chat failed");
  } finally {
    $("ask").disabled = false; $("ask").textContent = "Ask";
  }
};
