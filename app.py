import streamlit as st

# MUST BE THE ABSOLUTE FIRST STREAMLIT CALL IN THE MAIN SCRIPT FILE
st.set_page_config(
    page_title="High Yield & Fixed Income ETF Monitor",
    page_layout="wide",
    initial_sidebar_state="expanded"
)

# Heavy third-party imports placed AFTER set_page_config
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==============================================================================
# APP HEADER
# ==============================================================================
st.title("📊 High Yield & Fixed Income ETF Monitor")
st.caption("Real-time pricing, total returns, and risk metrics across short-duration & high-yield ETFs.")

# ==============================================================================
# SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.header("Monitor Settings")

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

days_map = {"1M": 30, "3M": 90, "6M": 180, "YTD": 275, "1Y": 365, "2Y": 730, "Max": 1825}
start_date = datetime.now() - timedelta(days=days_map[timeframe])

# ==============================================================================
# DATA FETCHING & CACHING
# ==============================================================================
@st.cache_data(ttl=900)
def fetch_etf_data(tickers, start):
    hist_dict = {}
    info_list = []
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start)
            if not hist.empty:
                hist_dict[ticker] = hist
            
            inf = t.info or {}
            trailing_yield = inf.get("trailingAnnualDividendYield")
            expense_ratio = inf.get("netExpenseRatio")
            
            latest_price = (
                inf.get("regularMarketPrice") 
                or inf.get("previousClose") 
                or (hist["Close"].iloc[-1] if not hist.empty else "N/A")
            )

            info_list.append({
                "Ticker": ticker,
                "Name": inf.get("shortName", ticker),
                "Price ($)": f"${latest_price:.2f}" if isinstance(latest_price, (int, float)) else latest_price,
                "Trailing Yield (%)": f"{round(trailing_yield * 100, 2)}%" if trailing_yield is not None else "N/A",
                "Expense Ratio (%)": f"{round(expense_ratio * 100, 2)}%" if expense_ratio is not None else "N/A",
                "52W High": f"${inf.get('fiftyTwoWeekHigh'):.2f}" if inf.get('fiftyTwoWeekHigh') else "N/A",
                "52W Low": f"${inf.get('fiftyTwoWeekLow'):.2f}" if inf.get('fiftyTwoWeekLow') else "N/A"
            })
        except Exception:
            pass

    return hist_dict, pd.DataFrame(info_list)

if not selected_tickers:
    st.warning("Please select at least one ETF from the sidebar.")
    st.stop()

with st.spinner("Fetching market data..."):
    hist_data, summary_df = fetch_etf_data(tuple(selected_tickers), start_date)

# ==============================================================================
# MARKET OVERVIEW & CHARTS
# ==============================================================================
st.subheader("Current Market Overview")
if not summary_df.empty:
    st.dataframe(summary_df.set_index("Ticker"), use_container_width=True)

st.markdown("---")
st.subheader("Price Performance vs. Normalized Growth")

tab1, tab2 = st.tabs(["Normalized Return (% Base 100)", "Absolute Close Prices ($)"])

with tab1:
    norm_df = pd.DataFrame()
    for ticker in selected_tickers:
        if ticker in hist_data and not hist_data[ticker].empty:
            close_prices = hist_data[ticker]["Close"]
            norm_df[ticker] = (close_prices / close_prices.iloc[0]) * 100
            
    if not norm_df.empty:
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
    price_df = pd.DataFrame({t: hist_data[t]["Close"] for t in selected_tickers if t in hist_data and not hist_data[t].empty})
    if not price_df.empty:
        fig_price = px.line(
            price_df,
            x=price_df.index,
            y=price_df.columns,
            title="Absolute Share Price Movement ($)",
            labels={"value": "Price ($)", "variable": "ETF Ticker", "Date": "Date"}
        )
        fig_price.update_layout(hovermode="x unified")
        st.plotly_chart(fig_price, use_container_width=True)

# ==============================================================================
# RISK & DRAWDOWN ANALYSIS
# ==============================================================================
st.markdown("---")
st.subheader("Risk & Volatility Analysis")

focus_ticker = st.selectbox("Select Focus Ticker for Risk Metrics:", options=selected_tickers)

if focus_ticker in hist_data and not hist_data[focus_ticker].empty:
    focus_df = hist_data[focus_ticker].copy()
    
    focus_df["Rolling Max"] = focus_df["Close"].cummax()
    focus_df["Drawdown"] = (focus_df["Close"] - focus_df["Rolling Max"]) / focus_df["Rolling Max"] * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${focus_df['Close'].iloc[-1]:.2f}")
    col2.metric("Max Drawdown (Period)", f"{focus_df['Drawdown'].min():.2f}%")
    col3.metric("Volume (Latest)", f"{int(focus_df['Volume'].iloc[-1]):,}")
    
    fig_dd = px.area(
        focus_df, 
        x=focus_df.index, 
        y="Drawdown",
        title=f"{focus_ticker} Historical Drawdown (%)",
        labels={"Drawdown": "Drawdown %", "Date": "Date"},
        color_discrete_sequence=["#EF553B"]
    )
    st.plotly_chart(fig_dd, use_container_width=True)
