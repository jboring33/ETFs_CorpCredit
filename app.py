import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Page Configuration
st.set_page_config(
    page_title="High Yield & Fixed Income ETF Monitor",
    page_layout="wide",
    initial_sidebar_state="expanded"
)

st.title(" High Yield & Fixed Income ETF Monitor")
st.caption("Real-time pricing, total returns, and risk metrics across short-duration & high-yield ETFs.")

# 2. Sidebar Controls
st.sidebar.header("Monitor Settings")

# Default ticker list focused on SCYB and peers
DEFAULT_TICKERS = ["SCYB", "HYG", "USHY", "JAAA", "JPST", "SGOV"]
selected_tickers = st.sidebar.multiselect(
    "Select ETFs to Compare:",
    options=["SCYB", "HYG", "USHY", "JAAA", "JPST", "JBBB", "SGOV", "USFR"],
    default=DEFAULT_TICKERS
)

timeframe = st.sidebar.selectbox(
    "Select Lookback Period:",
    options=["1M", "3M", "6M", "YTD", "1Y", "2Y", "Max"],
    index=4
)

# Convert timeframe string to date delta
days_map = {"1M": 30, "3M": 90, "6M": 180, "YTD": 275, "1Y": 365, "2Y": 730, "Max": 1825}
start_date = datetime.now() - timedelta(days=days_map[timeframe])

# 3. Data Fetching Functions
@st.cache_data(ttl=900)  # Cache data for 15 minutes
def fetch_etf_data(tickers, start):
    data = {}
    info_list = []
    
    for ticker in tickers:
        t = yf.Ticker(ticker)
        # Fetch historical price data
        hist = t.history(start=start)
        data[ticker] = hist
        
        # Fetch fundamental info
        inf = t.info
        info_list.append({
            "Ticker": ticker,
            "Name": inf.get("shortName", ticker),
            "Price ($)": inf.get("regularMarketPrice") or inf.get("previousClose"),
            "Trailing Yield (%)": round(inf.get("trailingAnnualDividendYield", 0) * 100, 2) if inf.get("trailingAnnualDividendYield") else "N/A",
            "Expense Ratio (%)": round(inf.get("netExpenseRatio", 0) * 100, 2) if inf.get("netExpenseRatio") else "N/A",
            "52W High": inf.get("fiftyTwoWeekHigh"),
            "52W Low": inf.get("fiftyTwoWeekLow")
        })
        
    return data, pd.DataFrame(info_list)

if not selected_tickers:
    st.warning("Please select at least one ETF from the sidebar.")
    st.stop()

with st.spinner("Fetching ETF market data..."):
    hist_data, summary_df = fetch_etf_data(selected_tickers, start_date)

# 4. Top Key Metrics Row
st.subheader("Current Market Overview")
st.dataframe(summary_df.set_index("Ticker"), use_container_width=True)

# 5. Comparative Performance Chart
st.markdown("---")
st.subheader("Price Performance vs. Normalized Growth")

tab1, tab2 = st.tabs(["Normalized Return (% Base 100)", "Absolute Close Prices ($)"])

with tab1:
    # Normalize price series to start at 100
    norm_df = pd.DataFrame()
    for ticker in selected_tickers:
        if not hist_data[ticker].empty:
            close_prices = hist_data[ticker]["Close"]
            norm_df[ticker] = (close_prices / close_prices.iloc[0]) * 100
            
    fig_norm = px.line(
        norm_df, 
        x=norm_df.index, 
        y=norm_df.columns,
        title=f"Normalized Growth Comparison (Starting Base = 100) — Past {timeframe}",
        labels={"value": "Indexed Performance", "variable": "ETF Ticker", "Date": "Date"}
    )
    fig_norm.update_layout(hovermode="x unified", legend_title_text="ETF")
    st.plotly_chart(fig_norm, use_container_width=True)

with tab2:
    price_df = pd.DataFrame({t: hist_data[t]["Close"] for t in selected_tickers if not hist_data[t].empty})
    fig_price = px.line(
        price_df,
        x=price_df.index,
        y=price_df.columns,
        title="Absolute Share Price Movement ($)",
        labels={"value": "Price ($)", "variable": "ETF Ticker", "Date": "Date"}
    )
    fig_price.update_layout(hovermode="x unified")
    st.plotly_chart(fig_price, use_container_width=True)

# 6. Deep Dive: Selected ETF Volatility & Drawdown Analysis
st.markdown("---")
st.subheader("Risk & Volatility Analysis")

focus_ticker = st.selectbox("Select Focus Ticker for Risk Metrics:", options=selected_tickers)

if focus_ticker in hist_data and not hist_data[focus_ticker].empty:
    focus_df = hist_data[focus_ticker].copy()
    
    # Calculate Max Drawdown
    focus_df["Rolling Max"] = focus_df["Close"].cummax()
    focus_df["Drawdown"] = (focus_df["Close"] - focus_df["Rolling Max"]) / focus_df["Rolling Max"] * 100
    
    col1, col2, col3 = st.st.columns(3)
    col1.metric("Current Price", f"${focus_df['Close'].iloc[-1]:.2f}")
    col2.metric("Max Drawdown (Period)", f"{focus_df['Drawdown'].min():.2f}%")
    col3.metric("Volume (Latest)", f"{int(focus_df['Volume'].iloc[-1]):,}")
    
    # Plot Drawdown Chart
    fig_dd = px.area(
        focus_df, 
        x=focus_df.index, 
        y="Drawdown",
        title=f"{focus_ticker} Historical Drawdown (%)",
        labels={"Drawdown": "Drawdown %", "Date": "Date"},
        color_discrete_sequence=["#EF553B"]
    )
    st.plotly_chart(fig_dd, use_container_width=True)
