import pytest
from enhanced_lib.calculations.shared import AppConfig, build_config


@pytest.fixture
def app_config():
    return AppConfig(
        fee=0.06,
        risk_per_trade=4,
        risk_reward=4,
        focus=29200.0,
        budget=2000.0,
        support=45000.0,
        resistance=66660.0,
        percent_change=0.0,
        tradeSplit=8,
        take_profit=None,
        kind="short",
        entry=69040.0,
        stop=64280.0,
        min_size=0.003,
        minimum_size=None,
        price_places="%.1f",
        decimal_places="%.3f",
        strategy="quantity",
        as_array=None,
        raw=None,
    )


def test_build_config(app_config: AppConfig):
    param_type = {
        "take_profit": app_config.entry,
        "entry": app_config.entry,
        "risk": None,
        "stop": app_config.stop,
        "risk_reward": 30,
        "raw_instance": False,
        "kind": app_config.kind,
        "no_of_trades": 30,
        "increase": True,
        "price_places": app_config.price_places,
        "decimal_places": app_config.decimal_places,
        "support": None,
        "resistance": None,
    }

    result = build_config(app_config, param_type)
    assert result == [
        {
            "avg_entry": 74160.9,
            "avg_size": 0.001,
            "entry": 74160.9,
            "fee": 0.044,
            "incurred": 5.101,
            "incurred_sell": 69059.9,
            "neg.pnl": -0.183,
            "net": 9.407,
            "pnl": 9.881,
            "quantity": 0.001,
            "risk": 0.133,
            "rr": 30,
            "sell_price": 64280.0,
            "start_entry": 69040.0,
            "stop": 74344.0,
            "stop_percent": 0.002,
        },
    ]
