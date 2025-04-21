import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
from fpdf import FPDF
import os
import re

# ------------------ Data Storage ------------------

if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = []

# ------------------ Helper Functions ------------------

def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "name": info.get("shortName", symbol),
            "price": info.get("currentPrice", 0),
            "pe_ratio": info.get("trailingPE", None),
            "market_cap": info.get("marketCap", None),
            "opm": info.get("operatingMargins", None),
        }
    except:
        return None

def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', ' ', text)

def generate_pdf_report():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Market Insights Report - {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')

    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Twitter/Reddit News:", ln=True)

    social = []
    try:
        h = requests.get("https://www.reddit.com/r/IndianStockMarket/top.json?limit=5", headers={"User-agent": "Mozilla"})
        for p in h.json().get('data', {}).get('children', []):
            social.append(p['data']['title'])
    except:
        social.append("Unable to fetch Reddit headlines.")

    try:
        t = requests.get("https://api.thenewsapi.com/v1/news/all?api_token=demo&language=en&limit=5")
        for article in t.json().get("data", []):
            social.append(article["title"])
    except:
        social.append("Unable to fetch Twitter/news headlines.")

    for headline in social:
        pdf.multi_cell(0, 8, txt=f"- {clean_text(headline)}")

    filename = f"global_market_report.pdf"
    pdf.output(filename)
    return filename

# ------------------ UI ------------------

st.title("📊 Custom Portfolio Tracker for Indian Stocks")

with st.sidebar:
    st.header("Add a Stock")
    name = st.text_input("Stock Symbol (e.g., RELIANCE.NS)")
    buy_price = st.number_input("Buy Price", min_value=0.0, step=0.1)
    quantity = st.number_input("Quantity", min_value=1, step=1)
    if st.button("Add Stock") and name:
        st.session_state.portfolio.append({
            "symbol": name.upper(),
            "buy_price": buy_price,
            "quantity": quantity
        })

    st.markdown("---")
    csv_upload = st.file_uploader("Or Upload CSV", type=["csv"])
    if csv_upload:
        df = pd.read_csv(csv_upload)
        for _, row in df.iterrows():
            st.session_state.portfolio.append({
                "symbol": row['symbol'].upper(),
                "buy_price": row['buy_price'],
                "quantity": row['quantity']
            })

# ------------------ Display Portfolio ------------------

portfolio_data = []
for entry in st.session_state.portfolio:
    stock_info = fetch_stock_data(entry["symbol"])
    if stock_info:
        invested = entry["buy_price"] * entry["quantity"]
        market_value = stock_info["price"] * entry["quantity"]
        portfolio_data.append({
            "Symbol": entry["symbol"],
            "Name": stock_info["name"],
            "Buy Price": entry["buy_price"],
            "Current Price": stock_info["price"],
            "Quantity": entry["quantity"],
            "Invested": invested,
            "Market Value": market_value,
            "P/E Ratio": stock_info["pe_ratio"],
            "Market Cap": stock_info["market_cap"],
            "OPM%": stock_info["opm"]
        })

df = pd.DataFrame(portfolio_data)

if not df.empty:
    st.subheader("📁 Portfolio Overview")
    st.dataframe(df)

    total_invested = df["Invested"].sum()
    total_market = df["Market Value"].sum()
    st.metric("Total Invested", f"₹{total_invested:,.2f}")
    st.metric("Current Market Value", f"₹{total_market:,.2f}")

# ------------------ Report Generation ------------------

if st.button("📄 Generate Daily Market PDF Report"):
    pdf_path = generate_pdf_report()
    with open(pdf_path, "rb") as f:
        st.download_button("Download PDF Report", data=f, file_name=pdf_path, mime="application/pdf")
