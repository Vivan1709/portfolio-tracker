# portfolio_tracker.py

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import datetime
import os
from fpdf import FPDF
from bs4 import BeautifulSoup

# Create reports directory
if not os.path.exists("reports"):
    os.makedirs("reports")

# ---------------------------
# Helper: Fetch stock data
# ---------------------------
def get_stock_info(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    return {
        "Current Price": info.get("currentPrice"),
        "Market Cap": info.get("marketCap"),
        "PE Ratio": info.get("trailingPE"),
        "Profit Margin": info.get("profitMargins"),
        "Return on Equity": info.get("returnOnEquity"),
    }

# ---------------------------
# Helper: News Insights
# ---------------------------
def scrape_moneycontrol():
    try:
        url = "https://www.moneycontrol.com/news/business/markets/"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        headlines = [a.text.strip() for a in soup.select(".clearfix a") if a.text.strip() != ""]
        return headlines[:5]
    except:
        return ["Could not fetch Moneycontrol news"]

def scrape_etmarkets():
    try:
        url = "https://economictimes.indiatimes.com/markets"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        headlines = [a.text.strip() for a in soup.select("h3") if a.text.strip() != ""]
        return headlines[:5]
    except:
        return ["Could not fetch ETMarkets news"]

def scrape_sebi_press():
    try:
        url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=9&smid=0&cid=0&type=Listing"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        headlines = [a.text.strip() for a in soup.select(".col-sm-9 a") if a.text.strip() != ""]
        return headlines[:5]
    except:
        return ["Could not fetch SEBI updates"]

# ---------------------------
# PDF Generator
# ---------------------------
def generate_pdf_report():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    date_today = datetime.datetime.now().strftime("%Y-%m-%d")

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=f"Daily Market Report - {date_today}", ln=True, align='C')

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Moneycontrol Top Headlines:", ln=True)
    for headline in scrape_moneycontrol():
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=f"- {headline}")

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="ETMarkets Top Headlines:", ln=True)
    for headline in scrape_etmarkets():
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=f"- {headline}")

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="SEBI Press Releases:", ln=True)
    for headline in scrape_sebi_press():
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=f"- {headline}")

    filename = f"reports/Market_Report_{date_today}.pdf"
    pdf.output(filename)
    return filename

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Client Portfolio Tracker", layout="wide")
st.title("📊 Client Portfolio Tracker")

portfolio_data = []

with st.sidebar:
    st.header("Add New Stock")
    symbol = st.text_input("Stock Symbol (NSE)", value="RELIANCE.NS")
    purchase_price = st.number_input("Purchase Price", step=0.01)
    quantity = st.number_input("Quantity", step=1)
    if st.button("Add to Portfolio"):
        info = get_stock_info(symbol)
        total_value = quantity * info['Current Price'] if info['Current Price'] else 0
        portfolio_data.append({
            "Symbol": symbol,
            "Quantity": quantity,
            "Purchase Price": purchase_price,
            "Current Price": info['Current Price'],
            "Market Cap": info['Market Cap'],
            "PE Ratio": info['PE Ratio'],
            "Profit Margin": info['Profit Margin'],
            "ROE": info['Return on Equity'],
            "Total Value": total_value
        })

    st.markdown("---")
    uploaded_file = st.file_uploader("Or Upload Portfolio CSV", type=["csv"])
    if uploaded_file is not None:
        df_uploaded = pd.read_csv(uploaded_file)
        st.session_state['portfolio_df'] = df_uploaded

# Display portfolio
if 'portfolio_df' not in st.session_state:
    df = pd.DataFrame(portfolio_data)
else:
    df = st.session_state['portfolio_df']

if not df.empty:
    st.subheader("Portfolio Summary")
    st.dataframe(df)
    st.write(f"Total Portfolio Value: ₹{df['Total Value'].sum():,.2f}")

# Generate PDF
st.markdown("---")
if st.button("📄 Generate Daily Market Insights PDF"):
    pdf_path = generate_pdf_report()
    with open(pdf_path, "rb") as f:
        st.download_button("Download Market Report PDF", f, file_name=os.path.basename(pdf_path))
