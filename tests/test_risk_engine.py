from src.models import Portfolio, Holding
from src.risk_engine import evaluate_exposures, score_severity


def test_evaluate_exposures_and_score_severity():
    holdings = [
        Holding(issuer="A", asset_type="Equity", sector="Energy", geography="US", market_value=100.0, weight_pct=9.0),
        Holding(issuer="B", asset_type="Equity", sector="Energy", geography="US", market_value=100.0, weight_pct=10.0),
    ]
    portfolio = Portfolio(portfolio_id="P1", fund="Fund 1", holdings=holdings)
    exposures = evaluate_exposures(portfolio)

    assert exposures["issuer_concentration"]
    assert exposures["issuer_concentration"][0]["status"] == "BREACH"
    assert score_severity(exposures)["severity"] == "CRITICAL"
