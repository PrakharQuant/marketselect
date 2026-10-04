# MarketSelect

Decide which markets to enter and how to split a fixed budget. The decision is a mixed-integer program: Gurobi when a license is present, CBC otherwise. The bundled panel is built from Statista Mobility Market Insights revenue forecasts for nine European countries, plus an IEA EVs-per-charger series. Original workbooks are in data/. FX rates and spend bounds are assumptions, documented in data/citations.csv.

Live app target: Render (`render.yaml`). `gurobipy` is optional and is not in `requirements.txt`, so a free Render build succeeds. Install it locally (`pip install gurobipy`) or set `GRB_WLSACCESSID`, `GRB_WLSSECRET`, and `GRB_LICENSEID` on a host that has Gurobi. Without a license, the app solves with CBC.

## Decision

Enter market \(i\) or not (\(y_i \in \{0,1\}\)). Choose spend \(x_i\).

\[
\max \sum_i (r_i x_i - f_i y_i)
\]

\[
\sum_i x_i \le B, \quad \sum_i y_i \le K, \quad \sum_i \rho_i x_i \le R, \quad L_i y_i \le x_i \le U_i y_i
\]

\(r_i\) is an illustrative contribution per dollar from scenario-scaled CAGR and the competition index. Market size sets the spend cap, not the rate. Both market size and CAGR are the Statista fields once you replace the demo panel. The contribution formula is a modeling choice in `marketselect/optimize.py`, not a published statistic.

## Run

```bash
pip install -r requirements.txt
pytest
streamlit run app.py
```

## Swap in Statista data

Export XLS from Statista Professional. Do not commit the raw export. Map it onto the demo schema and load it in the app, or replace `data/ev_charging_markets.csv` locally.

Required columns: `country`, `region`, `market_size_musd`, `cagr`, `competition_index`, `fixed_cost_musd`, `min_spend_musd`, `max_spend_musd`, `risk_weight`.

Record statistic id, title, unit, and year in `data/citations.csv`. The demo file is not a Statista extract and must not be cited as one.

## Layout

```text
app.py                  Streamlit UI
marketselect/ingest.py  demo load and export validation
marketselect/optimize.py  MIP, Gurobi then CBC
data/                   illustrative panel and citation template
render.yaml             Render web service
```
