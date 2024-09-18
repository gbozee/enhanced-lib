import pytest
from enhanced_lib.calculations.shared import build_config, AppConfig, ParamType
from enhanced_lib.calculations.trade_signal import Signal as TradeSignal


@pytest.fixture
def app_config():
    return AppConfig(
        fee=0.08,
        risk_per_trade=1.325,
        risk_reward=35,
        focus=67629.3,
        budget=2000.0,
        support=65858.0,
        resistance=70495.0,
        percent_change=0.027906543465628042,
        tradeSplit=1.0,
        take_profit=None,
        kind="long",
        entry=67800.0,
        stop=67600.0,
        min_size=0.004,
        minimum_size=None,
        price_places="%.1f",
        decimal_places="%.3f",
        strategy="quantity",
        as_array=False,
        raw=False,
    )


@pytest.fixture
def param_type():
    return ParamType(
        take_profit=None,
        entry=67800.0,
        risk=None,
        stop=67600.0,
        risk_reward=None,
        raw_instance=False,
        kind="long",
        no_of_trades=None,
        increase=False,
    )


def test_build_config(app_config, param_type):
    result = build_config(app_config, param_type)

    # Define the expected output based on the logic of the function
    expected_output = [
        67703.1,
        67705.9,
        67708.8,
        67711.6,
        67714.5,
        67717.3,
        67720.2,
        67723.0,
        67725.9,
        67728.7,
        67731.6,
        67734.4,
        67737.3,
        67740.1,
        67743.0,
        67745.8,
        67748.7,
        67751.5,
        67754.4,
        67757.2,
        67760.1,
        67762.9,
        67765.8,
        67768.6,
        67771.5,
        67774.3,
        67777.2,
        67780.1,
        67782.9,
        67785.7,
        67788.6,
        67791.4,
        67794.3,
        67797.2,
        67800.0,
    ]

    assert [x['avg_entry'] for x in result] == expected_output
