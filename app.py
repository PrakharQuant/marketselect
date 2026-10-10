"""Streamlit decision app for public EV-charging market entry."""

import streamlit as st

from marketselect.ingest import load_demo
from marketselect.optimize import pareto, solve

st.set_page_config(
    page_title="MarketSelect · EV charging entry",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    .hero {border: 1px solid #e6e6e6; border-radius: 12px; padding: 1.1rem 1.25rem; background: #f8fafc; margin-bottom: 1rem;}
    .hero h1 {margin: 0 0 0.35rem 0; font-size: 1.8rem;}
    .hero p {margin: 0.25rem 0; color: #334155; line-height: 1.45;}
    .footer {margin-top: 2rem; padding-top: 0.8rem; border-top: 1px solid #e6e6e6; color: #475569; font-size: 0.92rem;}
    .footer a {color: #0f172a; text-decoration: none; margin-right: 1rem;}
    .footer a:hover {text-decoration: underline;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>MarketSelect</h1>
      <p><b>Which European countries should a public EV-charging business enter, and how should a fixed budget be split?</b></p>
      <p>The app uses Statista Mobility Market Insights revenue forecasts for nine countries, plus an IEA measure of EVs per public charger. A mixed-integer program then chooses the markets and the spend. Move the controls on the left to change the budget, the number of markets, the risk limit, and the growth scenario.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

markets = load_demo()

st.sidebar.header("Decision controls")
budget = st.sidebar.slider("Budget ($ million)", 40, 400, 180, 10)
max_markets = st.sidebar.slider("Maximum markets to enter", 1, 9, 6)
risk_limit = st.sidebar.slider("Risk limit", 10, 200, 70, 5)
scenario = st.sidebar.selectbox("Growth scenario", ["downside", "base", "upside"], index=1)
st.sidebar.caption("Risk limit caps the weighted spend. A tighter limit favors lower-risk markets.")

result = solve(markets, budget, max_markets, risk_limit, scenario)
entered = result.plan[result.plan["enter"] == 1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Expected contribution", f"${result.objective_musd:,.1f}M")
c2.metric("Markets entered", int(entered.shape[0]))
c3.metric("Spend used", f"${entered['spend_musd'].sum():,.1f}M")
c4.metric("Solver", result.solver)

st.subheader("Recommended allocation")
show = result.plan[
    [
        "country",
        "region",
        "enter",
        "spend_musd",
        "expected_contribution_musd",
        "risk_used",
        "market_size_musd",
        "cagr",
        "competition_index",
    ]
].rename(
    columns={
        "country": "Country",
        "region": "Region",
        "enter": "Enter",
        "spend_musd": "Spend ($M)",
        "expected_contribution_musd": "Expected contribution ($M)",
        "risk_used": "Risk used",
        "market_size_musd": "Forecast market ($M)",
        "cagr": "CAGR",
        "competition_index": "Competition index",
    }
)
st.dataframe(show, use_container_width=True, hide_index=True)
st.caption("Enter is 1 if the market is selected. Competition index is higher when there are more electric vehicles per public charger.")

st.subheader("Return versus risk")
curve = pareto(markets, budget, max_markets, scenario)
st.line_chart(curve.set_index("risk_limit")["objective_musd"])
st.caption(f"Status: {result.status}. The chart shows how the expected contribution changes as the risk limit is relaxed.")

with st.expander("How the decision is made"):
    st.markdown(
        r"""
The model maximizes expected contribution:

\[
\max \sum_i (r_i x_i - f_i y_i)
\]

subject to a budget, a maximum number of markets, a risk limit, and a spend range if a market is entered. \(y_i\) is 1 when market \(i\) is entered. \(x_i\) is the spend in that market.

\(r_i\) is an assumed contribution per dollar. It rises with the Statista growth rate and falls as the competition index rises. Market size does not multiply the rate. It only sets how much can be spent. The 18% margin used in that rate is a modeling choice, not a Statista figure.
"""
    )

st.markdown(
    """
    <div class="footer">
      Built by Prakhar
      &nbsp;&nbsp;
      <a href="mailto:bestofprakhar@gmail.com" title="Email">✉️ bestofprakhar@gmail.com</a>
      <a href="https://www.linkedin.com/in/prakhar-gupta-5b7250372/" target="_blank" title="LinkedIn">in LinkedIn</a>
      <a href="https://x.com/PrakharQuant" target="_blank" title="X">𝕏 @PrakharQuant</a>
    </div>
    """,
    unsafe_allow_html=True,
)
