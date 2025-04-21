import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup

# App title
st.set_page_config(page_title="Portfolio Tracker", layout="wide")
st.title("📈 Multi-Client Stock Portfolio Tracker (India)")

# File uploader
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Show list of clients
    clients = df['client'].unique().tolist()
    selected_client = st.selectbox("Select a client", clients)

    # Filter for selected client
    client_df = df[df['client'] == selected_client]

    # Group transactions
    summary =
