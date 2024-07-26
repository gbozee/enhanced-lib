import pytest
from enhanced_lib.calculations.trade_signal import Signal as TradeSignal


@pytest.fixture
def trade_signal():
    return TradeSignal(
        percent_change=0.02,
        take_profit=None,
        support=59200,
        resistance=60000,
        increase_position=True,
        minimum_size=10.0,
        decimal_places=2,
        price_places=2,
        focus=50000,    
        budget=1000.0  # Add appropriate value for budget
    )

def test_trade_signal_initialization(trade_signal):
    assert trade_signal.percent_change == 0.02
    assert trade_signal.take_profit is None
    assert trade_signal.support == 59200
    assert trade_signal.resistance == 60000
    assert trade_signal.increase_position is True
    assert trade_signal.minimum_size == 10.0
    assert trade_signal.decimal_places == 2
    assert trade_signal.price_places == 2
    assert trade_signal.focus == 50000
    assert trade_signal.budget == 1000.0


@pytest.fixture
def n_trade_signal():
    return TradeSignal(
        focus=67629.3,
        budget=2000.0,
        percent_change=0.027906543465628042,
        price_places="%.1f",
        decimal_places="%.3f",
        fee=0.0006,
        support=65858.0,
        resistance=70495.0,
        take_profit=None,
        risk_per_trade=1.325,
        risk_reward=35,
        # additional_increase=0.0,
        split=None,
        minimum_size=0.004,
        increase_position=False,
        default=False,
        minimum_pnl=0.0,
        max_size=None,
        trade_size=None,
        increase_size=False,
        zone_risk=1,
    )


def test_signal_creation(n_trade_signal):
    signal = n_trade_signal
    assert signal.focus == 67629.3
    assert signal.budget == 2000.0
    assert signal.percent_change == 0.027906543465628042
    assert signal.price_places == "%.1f"
    assert signal.decimal_places == "%.3f"
    assert signal.zone_risk == 1
    assert signal.fee == 0.0006
    assert signal.support == 65858.0
    assert signal.risk_reward == 35
    assert signal.resistance == 70495.0
    assert signal.take_profit is None
    assert signal.risk_per_trade == 1.325
    assert signal.increase_size is False
    assert signal.additional_increase == 0.0
    assert signal.minimum_pnl == 0.0
    assert signal.split is None
    assert signal.max_size is None
    assert signal.trade_size is None
    assert signal.increase_position is False
    assert signal.default is False
    assert signal.minimum_size == 0.004
    assert signal.min_trades == 55
    assert signal.risk == pytest.approx(55.81308693125608)
    assert signal.min_price == 0.1

    # get_range tests
    expected_output = [
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0  ,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.1,
    ]
    result = signal.get_range(100.0, "long")
    assert result == expected_output

    expected_output = [
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        99.9,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.1,
        100.2,
    ]
    result = signal.get_range(100.0, "short")
    assert result == expected_output

    # get_margin_range tests
    margin_range = signal.get_margin_range(63629.2)
    assert margin_range is not None
    range_start, range_end = margin_range
    assert range_start == 62269.3
    assert range_end == 64007.0

    # get_future_range tests
    expected_output = (63628.1, 63659.7)
    result = signal.get_future_range(63629.2)
    assert result == expected_output

    # get_trade_range tests
    expected_output = (67732.2, 67767.1)
    result = signal.get_trade_range(67800.0, "long")
    assert result == expected_output

    # get_trade_zones test
    expected_output = [
        67766.5,
        67767.1,
        67767.7,
        67768.3,
        67768.9,
        67769.5,
        67770.1,
        67770.7,
        67771.3,
        67771.9,
        67772.5,
        67773.1,
        67773.7,
        67774.3,
        67774.9,
        67775.5,
        67776.1,
        67776.7,
        67777.3,
        67777.9,
        67778.5,
        67779.1,
        67779.7,
        67780.3,
        67780.9,
        67781.5,
        67782.1,
        67782.7,
        67783.3,
        67783.9,
        67784.5,
        67785.1,
        67785.7,
        67786.3,
        67786.9,
        67787.5,
        67788.1,
        67788.7,
        67789.3,
        67789.9,
        67790.5,
        67791.1,
        67791.7,
        67792.3,
        67792.9,
        67793.5,
        67794.1,
        67794.7,
        67795.3,
        67795.9,
        67796.5,
        67797.1,
        67797.7,
        67798.3,
        67798.9,
        67800.8,
    ]
    result = signal.get_trade_zones(67800.0, kind="long")
    assert result == expected_output

    # get_margin_zones test
    expected_output = [(67629.3, 69516.6), (65793.2, 67629.3)]
    result = signal.get_margin_zones(67800.0, "long")
    assert result == expected_output

    # get_future_zones test
    expected_output = [
        67845.2,
        67899.3,
        67953.5,
        68007.7,
        68061.9,
        68116.2,
        68170.5,
        68224.8,
        68279.2,
        68333.7,
        68388.1,
        68442.7,
        68497.2,
        68551.9,
        68606.5,
        68661.2,
        68716.0,
        68770.8,
        68825.6,
        68880.5,
        68935.4,
        68990.3,
        69045.4,
        69100.4,
        69155.5,
        69210.6,
        69265.8,
        69321.1,
        69376.3,
        69431.6,
        69487.0,
        69542.4,
        69597.9,
        69653.3,
        69708.9,
        69764.5,
    ]
    result = signal.get_future_zones(67800.0, kind="short")
    assert result == expected_output


def test_get_bulk_trade_zones(n_trade_signal):
    signal = n_trade_signal
    expected_output = [
        67684.0,
        67737.9,
        67791.8,
        67845.7,
        67899.6,
        67953.5,
        68007.4,
        68061.3,
        68115.2,
        68169.1,
        68223.0,
        68276.9,
        68330.8,
        68384.7,
        68438.6,
        68492.5,
        68546.4,
        68600.3,
        68654.2,
        68708.1,
        68762.0,
        68815.9,
        68869.8,
        68923.7,
        68977.6,
        69031.5,
        69085.4,
        69139.3,
        69193.2,
        69247.1,
        69301.0,
        69354.9,
        69408.8,
        69462.7,
        69516.6,
    ]
    result = signal.get_bulk_trade_zones(67800.0, "long", False)
    expected_result = [item["entry"] for item in result]
    assert expected_result == expected_output

    result = signal.get_bulk_trade_zones(67800.0, "short", True)
    expected_result = [item["entry"] for item in result]
    assert expected_result == [
        69708.9,
        69653.3,
        69597.9,
        69542.4,
        69487.0,
        69431.6,
        69376.3,
        69321.1,
        69265.8,
        69210.6,
        69155.5,
        69100.4,
        69045.4,
        68990.3,
        68935.4,
        68880.5,
        68825.6,
        68770.8,
        68716.0,
        68661.2,
        68606.5,
        68551.9,
        68497.2,
        68442.7,
        68388.1,
        68333.7,
        68279.2,
        68224.8,
        68170.5,
        68116.2,
        68061.9,
        68007.7,
        67953.5,
        67899.3,
        67845.2,
    ]


def test_default_build_entry(n_trade_signal):
    signal = n_trade_signal
    entry_price = 67800.0
    stop_loss = 67600.0
    risk = 100.0
    pnl = 50.0
    kind = "long"
    stop_percent = 0.01
    no_of_trades = 5
    take_profit = 70000.0
    current_entry = None
    current_quantity = 0.0
    support = 67500.0
    resistance = 70500.0

    result = signal.default_build_entry(
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk=risk,
        pnl=pnl,
        kind=kind,
        stop_percent=stop_percent,
        no_of_trades=no_of_trades,
        take_profit=take_profit,
        current_entry=current_entry,
        current_quantity=current_quantity,
        support=support,
        resistance=resistance,
    )

    # Define the expected output based on the logic of the function
    expected_output = [
        67640.0,
        67680.0,
        67720.0,
        67760.0,
        67800.0,
        # Add more expected trades here based on the logic
    ]

    assert [x['entry'] for x in result] == expected_output
