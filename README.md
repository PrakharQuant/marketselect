# MarketSelect

Decide which European markets to enter for public EV charging, and how to split a fixed budget. The decision is a mixed-integer program. Gurobi is used when a license is present. CBC is the default, including on Render.

The bundled panel covers nine countries. Revenue and CAGR come from Statista Mobility Market Insights. The competition index comes from an IEA series published on Statista. Spend bounds and FX rates are assumptions. Sources and conversions are in `data/citations.csv`.

## Decision

Enter market \(i\) or not (\(y_i \in \{0,1\}\)). Choose spend \(x_i\), in million USD.

\[
\max \sum_i (r_i x_i - f_i y_i)
\]

\[
\sum_i x_i \le B, \quad \sum_i y_i \le K, \quad \sum_i \rho_i x_i \le R, \quad L_i y_i \le x_i \le U_i y_i
\]

\(r_i = 0.18 \times (1 + g_i s) / c_i\). \(g_i\) is the Statista CAGR, \(s\) is the scenario multiplier (0.6 downside, 1.0 base, 1.4 upside), and \(c_i\) is the competition index. Market size does not multiply the rate. It sets the spend bounds. The 0.18 margin is a modeling choice in `marketselect/optimize.py`, not a published statistic.

At the default \(B = 180\), \(K = 6\), and \(R = 70\), the base case enters the United Kingdom and Germany. Raising the risk limit brings in the smaller markets.

## Data

Forecast public-charging revenue, converted to million USD:

| Country | Forecast | CAGR window | Statista id |
| --- | --- | --- | --- |
| Germany | 2028 | 2023–2028 | 1484167 |
| United Kingdom | 2029 | 2023–2029 | 1411503 |
| Norway | 2029 | 2023–2029 | 1413409 |
| Denmark | 2029 | 2023–2029 | 1553215 |
| Spain | 2028 | 2022–2028 | 1441469 |
| Finland | 2029 | 2023–2029 | 1477322 |
| Iceland | 2029 | 2023–2029 | 1553214 |
| Estonia | 2029 | 2023–2029 | 1499736 |
| Latvia | 2029 | 2023–2029 | 1499740 |

FX assumptions, not Statista rates: 1 EUR = 1.08 USD, 1 GBP = 1.27 USD. Norway is already in USD. Estonia and Latvia were in thousand euros.

Competition index is EVs per public charger in 2024 (statistic 1312911, source IEA) divided by 40.6, the highest value in that file. The United Kingdom, Norway, and Germany are in the file. The other six use the file median, 20.5, and are marked as imputed in `data/ev_charging_markets.csv`. Charger counts by country (statistic 571564) are stored for citation and are not in the objective.

Spend bounds are assumptions. Minimum entry is 2% of forecast revenue, floored at $2M and capped at $40M, and never more than 40% of the market. Maximum spend is 12% of forecast revenue, capped at $80M. That cap is what lets a $180M budget enter Germany without assigning it the whole portfolio.

## Run

```bash
pip install -r requirements.txt
pytest
streamlit run app.py
```

The app loads `data/ev_charging_markets.csv`. Upload a CSV or XLSX with the same columns to replace it. `gurobipy` is not in `requirements.txt`. Install it locally if you want the solver label to switch to Gurobi. A named-user academic license stays on your machine. It is not used on Render.

## Deploy

`render.yaml` is a Render Blueprint. In the Render dashboard, choose New, then Blueprint, then this repo and `main`. Leave the `GRB_` variables empty. The free service solves with CBC and sleeps after a period with no visits.

## Layout

```text
app.py                         Streamlit UI
marketselect/ingest.py         panel load and upload validation
marketselect/optimize.py       MIP, Gurobi then CBC
data/ev_charging_markets.csv   nine-country panel used by the app
data/marketselect_countries.xlsx  formula workbook for the panel
data/statista_evse_by_country_2024.xlsx
data/statista_evs_per_charger_2024.xlsx
data/citations.csv
render.yaml                    Render web service
```
