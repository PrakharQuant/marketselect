from pathlib import Path

from marketselect.ingest import load_demo
from marketselect.optimize import pareto, solve

ROOT = Path(__file__).resolve().parents[1]


def test_demo_loads():
    frame = load_demo()
    assert len(frame) == 18
    assert frame["country"].is_unique


def test_budget_and_market_caps_hold():
    result = solve(load_demo(), budget=120, max_markets=4, risk_limit=200)
    entered = result.plan[result.plan["enter"] == 1]
    assert result.status == "Optimal"
    assert entered.shape[0] <= 4
    assert entered["spend_musd"].sum() <= 120 + 1e-6
    assert (entered["spend_musd"] >= entered["min_spend_musd"] - 1e-6).all()


def test_tighter_risk_does_not_improve_objective():
    frame = load_demo()
    loose = solve(frame, budget=200, max_markets=6, risk_limit=200)
    tight = solve(frame, budget=200, max_markets=6, risk_limit=25)
    assert tight.objective_musd <= loose.objective_musd + 1e-6


def test_pareto_is_nondecreasing():
    curve = pareto(load_demo(), budget=180, max_markets=5, scenario="base", steps=5)
    values = curve["objective_musd"].tolist()
    assert values == sorted(values)
