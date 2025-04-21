import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from datetime import datetime
import json

# --- Streamlit App Setup ---
st.set_page_config(page_title="Market Intelligence Platform", layout="wide")
st.title("📊 Indian Stock Portfolio & Market Intelligence Hub")

# --- Session State for Trades ---
if 'manual_entries' not in st.session_state:
    st.session_state.manual_entries = pd.DataFrame(columns=["client","stock","action","qty","price","date"])

# --- CSV Upload ---
st.sidebar.header("Import Trades")
uploaded_file = st.sidebar.file_uploader("Upload trade CSV", type=["csv"])
if uploaded_file:
    df_csv = pd.read_csv(uploaded_file)
else:
    df_csv = pd.DataFrame(columns=["client","stock","action","qty","price","date"])

# --- Manual Trade Form ---
st.sidebar.header("Add Trade Manually")
with st.sidebar.form("manual_trade_form"):
    client = st.text_input("Client Name")
    stock = st.text_input("Stock Symbol (e.g., TCS)")
    action = st.selectbox("Action", ["buy","sell"])
    qty = st.number_input("Quantity", min_value=1)
    price = st.number_input("Price/share", min_value=0.0, format="%.2f")
    date = st.date_input("Trade Date")
    submitted = st.form_submit_button("Add Trade")
    if submitted:
        entry = pd.DataFrame([{"client":client.strip(),"stock":stock.strip().upper(),"action":action,"qty":qty,"price":price,"date":date}])
        st.session_state.manual_entries = pd.concat([st.session_state.manual_entries, entry], ignore_index=True)
        st.success("Trade added.")

# --- Combine Trades ---
all_trades = pd.concat([df_csv, st.session_state.manual_entries], ignore_index=True)
if all_trades.empty:
    st.info("No trades. Upload CSV or add manually.")
    st.stop()

# --- Client Selection ---
clients = all_trades['client'].unique().tolist()
selected_client = st.selectbox("Select Client", clients)
client_df = all_trades[all_trades['client']==selected_client]

# --- Compute Portfolio Summary ---
summary = {}
for _, row in client_df.iterrows():
    sym = row['stock']
    key = sym + ".NS"
    qty, price, act = row['qty'], row['price'], row['action']
    summary.setdefault(sym, {'qty':0,'invested':0})
    if act == 'buy': summary[sym]['qty'] += qty; summary[sym]['invested'] += qty*price
    else: summary[sym]['qty'] -= qty; summary[sym]['invested'] -= qty*price

# --- Build Holdings Table & identify large caps ---
threshold = 500 * 1e7  # ₹500 Cr
df_hold = []
large_names = []
for sym, info in summary.items():
    if info['qty']==0: continue
    ticker = yf.Ticker(sym+".NS")
    data = ticker.info
    live = data.get('currentPrice',0)
    mcap = data.get('marketCap',0)
    mv = live * info['qty']
    gain = mv - info['invested']
    long_name = data.get('longName','')
    if mcap>threshold and long_name:
        large_names.append(long_name)
    df_hold.append({
        'Stock':sym,'Qty':info['qty'],'Invested ₹':round(info['invested'],2),
        'CMP ₹':round(live,2),'Market Value ₹':round(mv,2),'Gain/Loss ₹':round(gain,2),
        'P/E':data.get('trailingPE','N/A'),'Market Cap':mcap,'OPM%':f"{round(data.get('operatingMargins',0)*100,2)}%",
        'Debt/Equity':data.get('debtToEquity','N/A')
    })

st.subheader(f"Portfolio Summary for {selected_client}")
df_summary = pd.DataFrame(df_hold)
st.dataframe(df_summary, use_container_width=True)

# --- Stock Details ---
st.subheader("🔍 Stock Details & Quality Tags")
sel = st.selectbox("Choose Stock", df_summary['Stock'])
if sel:
    row = df_summary[df_summary['Stock']==sel].iloc[0]
    st.write(row.to_dict())
    # Basic sentiment tag
    tag = 'Neutral'
    if row['Gain/Loss ₹']>0: tag='Bullish'
    if row['Gain/Loss ₹']<0: tag='Bearish'
    st.markdown(f"**Sentiment Tag:** {tag}")

# --- SEBI Actions for Large Caps ---
st.subheader("📢 SEBI Actions for Large Caps (>₹500Cr)")
def fetch_sebi():
    url="https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=3"
    res=requests.get(url)
    soup=BeautifulSoup(res.text,'html.parser')
    items=soup.select('.list li')
    acts=[]
    for it in items:
        title=it.get_text(strip=True)
        link="https://www.sebi.gov.in"+it.find('a')['href']
        for name in large_names:
            if name.lower() in title.lower(): acts.append((title,link))
    return acts
acts = fetch_sebi()
if acts:
    for t,l in acts: st.markdown(f"- [{t}]({l})")
else:
    st.write("No recent SEBI actions for large-cap holdings.")

# --- Market Report PDF Generator ---
st.subheader("📄 Market Insights Report")
if st.button("Generate Market Insights PDF"):
    # Scrape social & news
    subs=['IndianStockMarket','stocks','economy']
    social=[]
    for sub in subs:
        h=requests.get(f'https://www.reddit.com/r/{sub}/hot.json?limit=3',headers={'User-Agent':'Mozilla/5.0'})
        for p in h.json().get('data',{}).get('children',[]): social.append(p['data']['title'])
    # News RSS
    feeds=[('MoneyControl','https://www.moneycontrol.com/rss/latestnews.xml'),
           ('ET','https://economictimes.indiatimes.com/rssfeedstopstories.cms')]
    news=[]
    import feedparser
    for name,url in feeds:
        d=feedparser.parse(url)
        for e in d.entries[:3]: news.append(f"[{name}] {e.title}")
    # PDF creation
    now=datetime.now().strftime('%d-%B-%Y')
    fname=f"Market-Insights-{now}.pdf"
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial","B",16)
    pdf.cell(0,10,f"Market Insights Report - {now}",ln=True,align='C')
    pdf.ln(10); pdf.set_font("Arial","B",14); pdf.cell(0,8,"Social Media Trends",ln=True)
    pdf.set_font("Arial","",12)
    for s in social: pdf.multi_cell(0,6,f"- {s}")
    pdf.ln(5); pdf.set_font("Arial","B",14); pdf.cell(0,8,"News Headlines",ln=True)
    pdf.set_font("Arial","",12)
    for n in news: pdf.multi_cell(0,6,f"- {n}")
    pdf.ln(5); pdf.set_font("Arial","B",14); pdf.cell(0,8,"SEBI Actions",ln=True)
    pdf.set_font("Arial","",12)
    for t,l in acts: pdf.multi_cell(0,6,f"- {t} (Link: {l})")
    out_path=f"reports/{fname}"
    pdf.output(out_path)
    st.success(f"PDF generated: {fname}")
    with open(out_path,'rb') as f: st.download_button("Download PDF", f, file_name=fname)

# --- End of App ---
