import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import os
import openai
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="Portfolio & Market Intelligence", layout="wide")
st.title("📊 Indian Stock Portfolio Tracker & Market Intelligence Hub")

# Load OpenAI Key (add to Streamlit Secrets as OPENAI_API_KEY)
openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# Ensure PDF directory exists
PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# --- Session State for Manual Entries ---
if 'manual_entries' not in st.session_state:
    st.session_state.manual_entries = pd.DataFrame(
        columns=["client", "stock", "action", "qty", "price", "date"]
    )

# --- Trade Data Input ---
st.subheader("1. Import Trade History")
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload CSV of trades", type="csv")
    if uploaded_file:
        df_csv = pd.read_csv(uploaded_file)
    else:
        df_csv = pd.DataFrame(columns=["client", "stock", "action", "qty", "price", "date"])
with col2:
    st.write("**Or enter trades manually**")
    with st.form("manual_trade_form", clear_on_submit=True):
        client = st.text_input("Client Name")
        stock = st.text_input("Stock Symbol (e.g., INFY)")
        action = st.selectbox("Action", ["buy", "sell"])
        qty = st.number_input("Quantity", min_value=1, step=1)
        price = st.number_input("Price per Share", min_value=0.0, step=0.01)
        date = st.date_input("Trade Date")
        submitted = st.form_submit_button("Add Trade")
        if submitted:
            new = pd.DataFrame([{"client": client.strip(), "stock": stock.strip().upper(),
                                  "action": action, "qty": qty, "price": price, "date": date}])
            st.session_state.manual_entries = pd.concat(
                [st.session_state.manual_entries, new], ignore_index=True
            )
            st.success("Trade added!")

# Combine CSV and manual entries
df_all = pd.concat([df_csv, st.session_state.manual_entries], ignore_index=True)
if df_all.empty:
    st.warning("No trade data. Upload CSV or add trades.")
    st.stop()

# --- Portfolio View ---
st.subheader("2. Portfolio Overview")
clients = df_all['client'].unique().tolist()
selected_client = st.selectbox("Select Client", clients)
client_df = df_all[df_all['client'] == selected_client]

# Summarize holdings
summary = {}
for _, r in client_df.iterrows():
    sym = r['stock']
    qty = r['qty']
    cost = r['price']
    act = r['action'].lower()
    if sym not in summary:
        summary[sym] = {'qty': 0, 'invested': 0}
    if act == 'buy': summary[sym]['qty'] += qty; summary[sym]['invested'] += qty * cost
    else: summary[sym]['qty'] -= qty; summary[sym]['invested'] -= qty * cost

# Build DataFrame
data = []
for sym, info in summary.items():
    ticker = yf.Ticker(sym + ".NS")
    info_data = ticker.info
    live = info_data.get('regularMarketPrice', 0)
    pe = info_data.get('trailingPE', 'N/A')
    mc = info_data.get('marketCap', 'N/A')
    opm = info_data.get('operatingMargins', 'N/A')
    de = info_data.get('debtToEquity', 'N/A')

    mv = info['qty'] * live
    pnl = mv - info['invested']

    data.append({
        'Stock': sym,
        'Qty': info['qty'],
        'Invested ₹': round(info['invested'],2),
        'CMP ₹': round(live,2),
        'Market Cap ₹': mc,
        'P/E': pe,
        'OPM%': f"{round(opm*100,2)}%" if isinstance(opm,float) else opm,
        'D/E': de,
        'Market Value ₹': round(mv,2),
        'Gain/Loss ₹': round(pnl,2)
    })

df_port = pd.DataFrame(data)
st.dataframe(df_port, use_container_width=True)

# --- Detailed View ---
st.subheader("3. Stock Deep Dive")
stock_sel = st.selectbox("Select Stock for Details", df_port['Stock'])
if stock_sel:
    info = yf.Ticker(stock_sel + ".NS").info
    st.json({k: info.get(k) for k in ['longName','sector','industry','regularMarketPrice',
                                       'trailingPE','marketCap','operatingMargins','debtToEquity']})

# --- SEBI Tracker ---
st.subheader("4. SEBI Actions (>₹500 Cr Market Cap)")
def get_sebi_actions():
    url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&smid=0&cid=0"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content,'html.parser')
    items = soup.select(".listingInfo")
    out=[]
    for it in items:
        title=it.select_one('a').text.strip()
        link='https://www.sebi.gov.in'+it.select_one('a')['href']
        date=it.select_one('.date').text.strip()
        out.append(f"{date} - [{title}]({link})")
    return out

sebi_actions = get_sebi_actions()
for act in sebi_actions:
    st.markdown(act)

# --- Report Generator ---
st.subheader("5. Generate Market Insights PDF")

# Helpers for scraping news/social

def scrape_reddit():
    headers={'User-Agent':'Mozilla/5.0'}
    url='https://www.reddit.com/r/IndianStockMarket/hot.json?limit=5'
    try:
        r=requests.get(url, headers=headers)
        posts=r.json()['data']['children']
        return [p['data']['title'] for p in posts]
    except:
        return []

def scrape_moneycontrol():
    try:
        r=requests.get('https://www.moneycontrol.com/news/business', headers={'User-Agent':'Mozilla/5.0'})
        soup=BeautifulSoup(r.text,'html.parser')
        headlines=[h.text.strip() for h in soup.select('h2.headline')[:5]]
        return headlines
    except:
        return []

# PDF generation

def generate_report():
    date_str = datetime.now().strftime("%d-%b-%Y")
    title=f"Market-Insights-{date_str}.pdf"
    # Collect content
    reddit=scrape_reddit()
    mc=scrape_moneycontrol()
    sebi=sebi_actions[:5]
    content = f"Market Update - {date_str}\n\nTop Reddit Trends:\n" + "\n".join(reddit)
    content += "\n\nTop MoneyControl Headlines:\n" + "\n".join(mc)
    content += "\n\nRecent SEBI Actions:\n" + "\n".join(sebi)
    # Summarize via GPT
    prompt=(f"You are a market analyst. Summarize the following into key actionable insights.\n{content}")
    try:
        resp=openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role":"user","content":prompt}]
        )
        summary=resp.choices[0].message.content
    except:
        summary=content
    # Create PDF
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial",size=12)
    for line in summary.split("\n"):
        pdf.multi_cell(0,8,line)
    path=os.path.join(PDF_DIR,title)
    pdf.output(path)
    return title

# Manual trigger
if st.button("Generate Market Insights PDF Now"):
    with st.spinner("Generating report..."):
        fname=generate_report()
        st.success(f"Report saved as {fname}")
        st.markdown(f"[Download Report]({PDF_DIR}/{fname})")

```
