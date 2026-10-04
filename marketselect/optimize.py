"""Mixed-integer market-entry model.

Gurobi is used when gurobipy imports and a license is present. Otherwise the
same formulation is solved with CBC through PuLP so the app and tests run
without a solver license.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

MARGIN = 0.18


@dataclass
class SolveResult:
    status: str
    solver: str
    objective_musd: float
    plan: pd.DataFrame
    budget: float
    max_markets: int
    risk_limit: float
    scenario: str


def contribution_per_dollar(frame: pd.DataFrame, scenario: str) -> pd.Series:
    """Illustrative margin on a dollar of growth spend, not a Statista field.

    Market size does not multiply the rate. It sets the spend cap in the data,
    so a large market is not automatically a better dollar than a small one.
    """
    growth = {"downside": 0.6, "base": 1.0, "upside": 1.4}[scenario]
    return MARGIN * (1 + frame["cagr"] * growth) / frame["competition_index"]


def solve(
    frame: pd.DataFrame,
    budget: float = 200,
    max_markets: int = 6,
    risk_limit: float = 80,
    scenario: str = "base",
) -> SolveResult:
    if scenario not in {"downside", "base", "upside"}:
        raise ValueError("scenario must be downside, base, or upside")
    data = frame.copy()
    data["return_per_dollar"] = contribution_per_dollar(data, scenario)
    try:
        import gurobipy  # noqa: F401

        return _solve_gurobi(data, budget, max_markets, risk_limit, scenario)
    except Exception:
        return _solve_cbc(data, budget, max_markets, risk_limit, scenario)


def pareto(
    frame: pd.DataFrame,
    budget: float,
    max_markets: int,
    scenario: str,
    steps: int = 8,
) -> pd.DataFrame:
    risk_cap = float((frame["risk_weight"] * frame["max_spend_musd"]).sum())
    rows = []
    for step in range(1, steps + 1):
        limit = risk_cap * step / steps
        result = solve(frame, budget, max_markets, limit, scenario)
        entered = result.plan[result.plan["enter"] == 1]
        rows.append(
            {
                "risk_limit": round(limit, 2),
                "objective_musd": result.objective_musd,
                "spend_musd": float(entered["spend_musd"].sum()) if len(entered) else 0.0,
                "risk_used": float(entered["risk_used"].sum()) if len(entered) else 0.0,
                "markets": int(entered.shape[0]),
                "solver": result.solver,
                "status": result.status,
            }
        )
    return pd.DataFrame(rows)


def _pack(data: pd.DataFrame, enter: dict, spend: dict, status: str, solver: str, objective: float, budget: float, max_markets: int, risk_limit: float, scenario: str) -> SolveResult:
    plan = data.copy()
    plan["enter"] = [int(round(enter[i])) for i in plan.index]
    plan["spend_musd"] = [round(float(spend[i]), 2) for i in plan.index]
    plan["expected_contribution_musd"] = [
        round(float(plan.loc[i, "return_per_dollar"] * spend[i] - plan.loc[i, "fixed_cost_musd"] * enter[i]), 2)
        for i in plan.index
    ]
    plan["risk_used"] = [
        round(float(plan.loc[i, "risk_weight"] * spend[i]), 2) for i in plan.index
    ]
    plan = plan.sort_values(["enter", "expected_contribution_musd"], ascending=[False, False])
    return SolveResult(status, solver, round(objective, 2), plan, budget, max_markets, risk_limit, scenario)


def _solve_cbc(data, budget, max_markets, risk_limit, scenario) -> SolveResult:
    import pulp

    prob = pulp.LpProblem("marketselect", pulp.LpMaximize)
    enter = pulp.LpVariable.dicts("enter", data.index, cat="Binary")
    spend = pulp.LpVariable.dicts("spend", data.index, lowBound=0)
    prob += pulp.lpSum(
        data.loc[i, "return_per_dollar"] * spend[i] - data.loc[i, "fixed_cost_musd"] * enter[i]
        for i in data.index
    )
    prob += pulp.lpSum(spend[i] for i in data.index) <= budget
    prob += pulp.lpSum(enter[i] for i in data.index) <= max_markets
    prob += pulp.lpSum(data.loc[i, "risk_weight"] * spend[i] for i in data.index) <= risk_limit
    for i in data.index:
        prob += spend[i] >= data.loc[i, "min_spend_musd"] * enter[i]
        prob += spend[i] <= data.loc[i, "max_spend_musd"] * enter[i]
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    status_name = pulp.LpStatus[status]
    objective = pulp.value(prob.objective) or 0.0
    enter_v = {i: enter[i].value() or 0 for i in data.index}
    spend_v = {i: spend[i].value() or 0 for i in data.index}
    return _pack(data, enter_v, spend_v, status_name, "CBC", objective, budget, max_markets, risk_limit, scenario)


def _solve_gurobi(data, budget, max_markets, risk_limit, scenario) -> SolveResult:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("marketselect")
    model.Params.OutputFlag = 0
    enter = model.addVars(data.index, vtype=GRB.BINARY, name="enter")
    spend = model.addVars(data.index, lb=0, name="spend")
    model.setObjective(
        gp.quicksum(
            data.loc[i, "return_per_dollar"] * spend[i] - data.loc[i, "fixed_cost_musd"] * enter[i]
            for i in data.index
        ),
        GRB.MAXIMIZE,
    )
    model.addConstr(gp.quicksum(spend[i] for i in data.index) <= budget)
    model.addConstr(gp.quicksum(enter[i] for i in data.index) <= max_markets)
    model.addConstr(gp.quicksum(data.loc[i, "risk_weight"] * spend[i] for i in data.index) <= risk_limit)
    for i in data.index:
        model.addConstr(spend[i] >= data.loc[i, "min_spend_musd"] * enter[i])
        model.addConstr(spend[i] <= data.loc[i, "max_spend_musd"] * enter[i])
    model.optimize()
    status_name = {2: "Optimal", 3: "Infeasible"}.get(model.Status, str(model.Status))
    if model.SolCount == 0:
        enter_v = {i: 0 for i in data.index}
        spend_v = {i: 0 for i in data.index}
        objective = 0.0
    else:
        enter_v = {i: enter[i].X for i in data.index}
        spend_v = {i: spend[i].X for i in data.index}
        objective = model.ObjVal
    return _pack(data, enter_v, spend_v, status_name, "Gurobi", objective, budget, max_markets, risk_limit, scenario)
