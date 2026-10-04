"""Streamlit decision app for the market-entry model."""

import streamlit as st

from marketselect.ingest import load_demo, load_statista_xls
from marketselect.optimize import pareto, solve

st.set_page_config(page_title="MarketSelect", layout="wide")
st.title("MarketSelect")
st.caption("Which markets to enter, and how to split a fixed budget. Demo panel is illustrative; swap in a Statista export without changing the model.")

uploaded = st.sidebar.file_uploader("Statista export or cleaned CSV", type=["csv", "xls", "xlsx"])
if uploaded is None:
    markets = load_demo()
    st.sidebar.info("Using the bundled illustrative EV-charging panel.")
else:
    markets = load_statista_xls(uploaded)

budget = st.sidebar.slider("Budget ($M)", 40, 400, 180, 10)
max_markets = st.sidebar.slider("Max markets", 1, 12, 6)
risk_limit = st.sidebar.slider("Risk limit", 10, 200, 70, 5)
scenario = st.sidebar.selectbox("CAGR scenario", ["downside", "base", "upside"], index=1)

result = solve(markets, budget, max_markets, risk_limit, scenario)
entered = result.plan[result.plan["enter"] == 1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Expected contribution", f"${result.objective_musd:,.1f}M")
c2.metric("Markets entered", int(entered.shape[0]))
c3.metric("Spend", f"${entered['spend_musd'].sum():,.1f}M")
c4.metric("Solver", result.solver)

st.subheader("Allocation")
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
]
st.dataframe(show, use_container_width=True, hide_index=True)

st.subheader("Return vs risk")
curve = pareto(markets, budget, max_markets, scenario)
st.line_chart(curve.set_index("risk_limit")["objective_musd"])
st.caption(f"Status {result.status}. Risk limit is the cap on sum of risk weight times spend.")

with st.expander("Formulation"):
    st.markdown(
        r"""
Maximize \(\sum_i (r_i x_i - f_i y_i)\)

subject to \(\sum_i x_i \le B\), \(\sum_i y_i \le K\), \(\sum_i \rho_i x_i \le R\),
and \(L_i y_i \le x_i \le U_i y_i\), with \(y_i\) binary.

\(r_i\) is an illustrative contribution per dollar from scenario-scaled CAGR and competition. Market size caps spend. It is not a Statista field. Replace the demo CSV with your own cited export before treating a plan as research.
"""
    )
