from typing import Iterable, List, Optional, Tuple, TypeVar, TypedDict, Literal
import math
import typing
import datetime

T = TypeVar("T")


def get_current_time():
    _now = datetime.datetime.now()
    to_timestamp = _now.timestamp()
    return str(to_timestamp)


def determine_amount_to_sell(
    entry: float,
    quantity: float,
    sell_price: float,
    pnl: float,
    places="%.3f",
    _kind=None,
):
    kind = _kind
    if not kind:
        kind = "short" if sell_price > entry else "long"
    result = determine_new_amount_to_sell(
        entry=entry,
        quantity=quantity,
        sell_price=sell_price,
        expected_profit=pnl,
        kind=kind,
        places=places,
    )
    return result


def determine_new_amount_to_sell(
    entry: float,
    quantity: float,
    sell_price: float,
    expected_profit: float,
    kind="long",
    places="%.3f",
):
    expected_loss = determine_pnl(
        entry,
        sell_price,
        abs(quantity),
        kind=kind,
    )
    ratio = to_f(expected_profit / abs(expected_loss), "%.2f")
    new_quantity = abs(quantity) * ratio
    return to_f(new_quantity, places)


def to_f(value, places="%.1f"):
    v = value
    if isinstance(v, str):
        v = float(value)
    return float(places % v)


def determine_stop_and_size(entry: float, pnl: float, take_profit: float, kind="long"):
    if kind == "long":
        difference = take_profit - entry
    else:
        difference = entry - take_profit
    quantity = pnl / difference
    return abs(quantity)


def determine_close_price(
    entry,
    pnl,
    quantity,
    leverage=1,
    kind="long",
):
    dollar_value = entry / leverage
    position = dollar_value * quantity
    if position:
        percent = pnl / position
        difference = (position * percent) / quantity
        if kind == "long":
            result = difference + entry
        else:
            result = entry - difference
        return result
    return 0


def determine_amount_to_buy(
    ideal_entry: float,
    ideal_quantity: float,
    current_price: float,
    current_quantity: float,
    places="%.1f",
    with_quantity=None,
):
    evaluation = ideal_entry * ideal_quantity
    remaining_quantity = abs(ideal_quantity - current_quantity)
    left_side = evaluation - (current_price * current_quantity)
    price_to_buy = to_f(left_side / remaining_quantity, places)
    if with_quantity:
        return {
            "price": price_to_buy,
            "quantity": remaining_quantity,
        }
    return price_to_buy


def determine_quantity(
    entry,
    pnl,
    close_price,
    leverage=1,
    kind="long",
):
    """
    Calculate the quantity of a position given the entry price, PnL, and close price.

    Args:
        entry (float): Entry price of the position
        pnl (float): Profit/Loss amount
        close_price (float): Close/Exit price of the position
        leverage (float): Leverage multiplier, defaults to 1
        kind (str): Type of position - "long" or "short"

    Returns:
        float: Quantity of the position
    """
    if entry <= 0 or close_price <= 0:
        return 0

    # Calculate price difference based on position type
    if kind == "long":
        price_difference = close_price - entry
    else:
        price_difference = entry - close_price

    if price_difference == 0:
        return 0

    # Dollar value per unit
    dollar_value = entry / leverage

    # Derive quantity from the relationship between PnL and price difference
    # PnL = position_size * (price_difference/entry)
    # position_size = dollar_value * quantity
    # Therefore: PnL = (dollar_value * quantity) * (price_difference/entry)
    # Solving for quantity:
    quantity = (pnl * entry) / (dollar_value * price_difference)

    return quantity


def determine_position_size(
    entry: float,
    stop: Optional[float] = None,
    budget: Optional[float] = None,
    percent=None,
    min_size=None,
    as_coin=True,
    places="%.3f",
):
    if stop:
        stop_percent = abs(entry - stop) / entry
    else:
        stop_percent = percent
    if stop_percent and budget:
        size = budget / stop_percent
        if as_coin:
            size = size / entry
            if min_size and min_size == 1:
                return to_f(round(size), places)
        return to_f(size, places)


def determine_pnl(
    entry: float,
    close_price: float,
    quantity: float,
    kind: typing.Literal["long", "short"] = "long",
    contract_size=None,
):
    # dollar_value = entry / leverage
    # position = dollar_value * quantity
    if contract_size:
        direction = 1 if kind == "long" else -1
        return quantity * contract_size * direction * (1 / entry - 1 / close_price)
    if kind == "long":
        difference = close_price - entry
    else:
        difference = entry - close_price
    return difference * quantity


fib_ranges = [0, 0.236, 0.382, 0.5, 0.618, 0.789, 1, 1.272, 1.414, 1.618]


def fibonacci_analysis(
    support: float, resistance: float, kind="long", trend="long", places="%.1f"
):
    swing_high = resistance if trend == "long" else support
    swing_low = support if trend == "long" else resistance
    fib_calc = lambda p, h, l: (p * (h - l)) + l
    ranges = fib_ranges
    fib_values = [fib_calc(x, swing_high, swing_low) for x in ranges]
    fib_values = [to_f(r, places) for r in fib_values]
    if kind == "short":
        return list(reversed(fib_values)) if trend == "long" else fib_values
    return list(reversed(fib_values)) if trend == "short" else fib_values
    return fib_values


class OrderType(typing.TypedDict):
    price: float
    quantity: float


def determine_avg(orders: typing.List[OrderType], places="%.3f", price_places="%.1f"):
    sum_values = sum([x["price"] * x["quantity"] for x in orders])
    total_quantity = sum([x["quantity"] for x in orders])
    avg_value = to_f(sum_values / total_quantity, price_places) if total_quantity else 0
    return {"price": avg_value, "quantity": to_f(total_quantity, places)}


def group_into_pairs(arr: typing.List[typing.Any], size: int):
    return [arr[i : i + size] for i in range(0, len(arr), size)]


def group_into_pairs_with_sum_less_than(
    arr: typing.List[typing.Any], targetSum: float, key="quantity"
):
    result = []
    currentSum = 0
    currentGroup = []
    for i in range(0, len(arr)):
        currentGroup.append(arr[i])
        currentSum += arr[i][key]
        if currentSum >= targetSum:
            result.append(currentGroup)
            currentGroup = []
            currentSum = 0
    if not result:
        return [currentGroup]
    return result


class ProfitableTrade(typing.TypedDict):
    close_price: float
    quantity: float
    pnl: float


class LoosingTrade(typing.TypedDict):
    price: float
    quantity: float


def determine_expected_loss(
    profitable_trade: ProfitableTrade,
    loosing_trade: LoosingTrade,
    base_fee=0.0006,
    kind="long",
    decimal_places="%.3f",
    spread_factor=1.00001,
    price_places="%.1f",
):
    fee_cost = base_fee
    close_price = profitable_trade["close_price"]
    trade_quantity = profitable_trade["quantity"]
    pnl = profitable_trade["pnl"]

    profit_fee_cost = close_price * abs(trade_quantity) * fee_cost
    loss_fee_cost = close_price * abs(loosing_trade["quantity"]) * fee_cost
    expected_loss = determine_pnl(
        loosing_trade["price"],
        close_price,
        abs(loosing_trade["quantity"]),
        kind=kind,
    )
    ratio = to_f((pnl - (profit_fee_cost + loss_fee_cost)) / abs(expected_loss), "%.2f")
    new_quantity = to_f(loosing_trade["quantity"] * ratio, decimal_places)
    new_loss = to_f(
        determine_pnl(
            loosing_trade["price"],
            close_price,
            new_quantity,
            kind=kind,
        ),
        "%.2f",
    )
    spread = spread_factor
    if kind == "short":
        spread = 1 / spread
    return {
        "fees": to_f(profit_fee_cost + loss_fee_cost, "%.2f"),
        "ratio": ratio,
        "full_loss": expected_loss,
        "expected_loss": new_loss,
        "quantity": abs(new_quantity),
        "price": close_price,
        "kind": kind,
        "side": "sell" if kind == "long" else "buy",
        "stop": to_f(
            close_price * spread,
            price_places,
        ),
    }


def get_decimal_places(number_string: str) -> int:
    parts = number_string.split(".")
    if len(parts) == 2:
        return len(parts[1])
    else:
        return 0


def extend_fibonacci(
    support: float,
    resistance: float,
    focus=None,
    kind="long",
    trend="long",
    places="%.1f",
    high=1,
    low=0,
):
    _focus = focus or resistance
    values = fibonacci_analysis(
        support, resistance, kind=kind, trend=trend, places=places
    )
    remaining_buy_zones = [i for i in values if i <= _focus]
    remaining_sell_zones = [i for i in values if i >= _focus]
    pairs = [
        {"fib": high, "value": min(remaining_sell_zones)},
        {"fib": low, "value": min(remaining_buy_zones)},
    ]
    return determine_fib_support(pairs, places=places)


def determine_fib_support(value_with_fibs: typing.List[dict], places="%.1f"):
    import numpy as np

    A = []
    Y = []
    for i in value_with_fibs:
        A.append([i["fib"], (1 - i["fib"])])
        Y.append(i["value"])
    res = res = np.linalg.inv(A).dot(Y)
    return {
        "support": to_f(np.min(res), places),
        "resistance": to_f(np.max(res), places),
    }


# def solve_simulaneous_equation(arr:list,)


def determine_stop_and_tp(entry: float, size: float, pnl: float, kind="long"):
    stop = entry - (entry * (pnl / (size * entry)))
    tp = determine_close_price(entry, pnl, size, kind=kind)
    return {"stop": to_f(stop, "%.1f"), "tp": to_f(tp, "%.1f")}


def create_gap_pairs(
    arr: List[T], gap: int, item: Optional[T] = None
) -> List[Tuple[T, T]]:
    """
    Creates pairs of elements from an array based on a specified gap.

    Args:
        arr: Input list of elements
        gap: The gap between elements to create pairs
        item: Optional item to filter pairs by

    Returns:
        List of tuples containing paired elements
    """
    if len(arr) == 0:
        return []
    result: List[Tuple[T, T]] = []
    first_element = arr[0]

    for i in range(len(arr) - 1, -1, -1):
        current = arr[i]
        gap_index = i - gap
        paired_element = first_element if gap_index < 0 else arr[gap_index]

        if current != paired_element:
            result.append((current, paired_element))

    if item is not None:
        # Find the first pair where the first element matches the item
        matching_pair = next((pair for pair in result if pair[0] == item), None)
        return [matching_pair] if matching_pair else []

    return result


def determine_percent_change(
    low: float, high: float, iterations: int = 20, places="%.3f"
):
    """
    Calculate the percent change factor (x) for a given low, high, and number of iterations.

    Args:
        low (float): The lowest value.
        high (float): The highest value.
        iterations (int): The number of iterations.

    Returns:
        float: The percent change factor (x).
    """
    # Compute the percent change factor
    x = (high / low) ** (1 / iterations) - 1
    return to_f(x, places)


def get_lowest_and_highest(candlestick_list: list):
    """
    Determine the lowest and highest values from candlestick candlestick_list.

    Args:
        candlestick_list (list of lists): The candlestick candlestick_list where each sublist represents a candlestick.

    Returns:
        tuple: (lowest_value, highest_value)
    """
    # Extract the low prices (index 3) and high prices (index 2) from the candlestick_list
    lows = [float(candle[3]) for candle in candlestick_list]  # Low prices
    highs = [float(candle[2]) for candle in candlestick_list]  # High prices

    # Find the minimum of the lows and maximum of the highs
    lowest_value = min(lows)
    highest_value = max(highs)

    return {"low": lowest_value, "high": highest_value}


def determine_trade_zone_split(
    entry: float,
    stop: float,
    quantity: float,
    existing_quantity=0,
    kind="long",
    places="%.3f",
    price_places="%.8f",
    split=4,
):
    _entry = max(entry, stop) if kind == "long" else min(entry, stop)
    _stop = min(entry, stop) if kind == "long" else max(entry, stop)
    amount_to_buy = determine_amount_to_buy(
        _stop,
        quantity,
        _entry,
        existing_quantity,
        with_quantity=True,
        places=price_places,
    )
    target_price = amount_to_buy["price"]
    target_quantity = amount_to_buy["quantity"]
    print("amount_to_buy", amount_to_buy)
    # if target_price > stop:
    #     return []
    new_stop = target_price
    percent_change = determine_percent_change(target_price, stop, iterations=split)
    values = [target_price * (1 + percent_change) ** (x - 1) for x in range(split + 1)]
    maximum = sum([x for x in range(1, split + 1)])
    values_with_quantities = [
        {
            "price": x,
            "quantity": to_f(target_quantity * ((split - i) / maximum), places=places),
        }
        for i, x in enumerate(values)
    ]
    # breakpoint()
    return [x for x in values_with_quantities if x["quantity"]]


def get_quantity_to_sell(entry, close_price, quantity, amount, kind="long"):
    current_pnl = determine_pnl(entry, close_price, quantity, kind=kind)
    current_pnl = abs(current_pnl)
    ratio = amount / current_pnl
    return ratio * quantity


def determine_entry_and_size(stop, take_profit, risk, pnl):
    from sympy import symbols, Eq, solve

    # Define symbols for Entry Price and Position Size
    entry_price = symbols("entry_price", positive=True)
    position_size = risk / (entry_price - stop)  # Position Size Formula

    # PnL Equation
    pnl_eq = Eq(pnl, position_size * (take_profit - entry_price))

    # Solve for Entry Price
    entry_price_solution = solve(pnl_eq, entry_price)
    calculated_entry_price = entry_price_solution[0]  # Using the positive solution
    position_size = risk / (calculated_entry_price - stop)
    return {
        "entry": calculated_entry_price,
        "size": position_size,
    }


class TradePayload(TypedDict):
    entry: float
    kind: str
    risk: float
    stop_percent: float
    fee_percent: float
    sentiment: str
    early: bool


def get_next_trade(entry, percent_change, power=0, kind="long"):
    if kind == "long":
        stop = entry * (1 + percent_change) ** power
    else:
        stop = entry * (1 + percent_change) ** -power
    return stop


def get_avg_entry(entry, quantity, minimum_pnl, kind="long"):
    difference = minimum_pnl / quantity
    if kind == "long":
        return entry - difference
    return entry + difference


def simple_trade_generation(
    payload: "TradePayload", price_place="%.1f", decimal_places="%.3f"
):
    percent_change = payload["stop_percent"] / 100
    fee = payload["fee_percent"] / 100
    entry = payload["entry"]
    kind = payload["kind"]
    risk = payload["risk"]
    stop = to_f(
        get_next_trade(entry, percent_change, power=-1, kind=kind), places=price_place
    )
    quantity = to_f(risk / abs(entry - stop), decimal_places)
    minimum_pnl = to_f(entry * quantity * fee * 3, decimal_places)
    opposite_kind = "long" if kind == "short" else "short"
    opposite_avg_entry = to_f(
        get_avg_entry(entry, quantity, minimum_pnl, kind=opposite_kind), price_place
    )
    half_quantity = to_f(quantity / 2, decimal_places)
    remainder = to_f(quantity - (half_quantity * 2),decimal_places)
    first_half = half_quantity
    if remainder:
        first_half += remainder
    first_opposite_entry = to_f(
        get_next_trade(entry, percent_change, power=0.5, kind=opposite_kind),
        places=price_place,
    )
    second_opposite_entry = to_f(
        ((opposite_avg_entry * quantity) - (first_opposite_entry * first_half))
        / half_quantity,
        price_place,
    )
    opposite_pnl = to_f(
        determine_pnl(first_opposite_entry, stop, first_half, kind=opposite_kind),
        decimal_places,
    )
    loss = to_f(abs(risk - opposite_pnl), decimal_places) + minimum_pnl
    opposite_loss = to_f(
        determine_pnl(
            opposite_avg_entry, second_opposite_entry, quantity, kind=opposite_kind
        ),
        decimal_places,
    )
    max_pnl = to_f(
        determine_pnl(entry, second_opposite_entry, quantity, kind=kind), decimal_places
    )

    def get_side(_kind):
        return "buy" if _kind == "long" else "sell"

    return {
        "entry": [
            {
                "price": first_opposite_entry,
                "entry": first_opposite_entry,
                "quantity": first_half,
                "side": get_side(opposite_kind),
                "kind": opposite_kind,
            },
            {
                "entry": second_opposite_entry,
                "price": second_opposite_entry,
                "quantity": half_quantity,
                "side": get_side(opposite_kind),
                "kind": opposite_kind,
            },
            {
                "entry": entry,
                "price": entry,
                "quantity": quantity,
                "side": get_side(kind),
                "kind": kind,
                'early': payload.get('early'),
            },
        ],
        "stop": [
            {
                "price": second_opposite_entry,
                "quantity": quantity,
                "side": "buy" if get_side(opposite_kind) == "sell" else "sell",
                "stop": second_opposite_entry,
                "kind": opposite_kind,
                "is_market": True,
            },
            {
                "price": stop,
                "quantity": quantity,
                "side": "buy" if get_side(kind) == "sell" else "sell",
                "stop": stop,
                "kind": kind,
                "loss": to_f(loss, decimal_places),
                "is_market": True,
            },
        ],
        "take_profit": [
            {
                "take_profit": stop,
                "min_pnl": opposite_pnl,
                "side": "buy" if get_side(opposite_kind) == "sell" else "sell",
                "sell_price": stop,
                "quantity": first_half,
                "kind": opposite_kind,
            },
            {
                "take_profit": second_opposite_entry,
                "min_pnl": minimum_pnl,
                "max_pnl": max_pnl,
                "side": "buy" if get_side(kind) == "sell" else "sell",
                "sell_price": second_opposite_entry,
                "quantity": quantity,
                "kind": kind,
            },
        ],
    }


def reverse_simple_trader(
    payload: "TradePayload", price_place="%.1f", decimal_places="%.3f"
):
    percent_change = payload["stop_percent"] / 100
    entry = payload["entry"]
    kind = payload["kind"]

    actual_entry = to_f(
        get_next_trade(entry, percent_change, power=0.5, kind=kind), places=price_place
    )
    result = simple_trade_generation(
        {**payload, "entry": actual_entry},
        price_place=price_place,
        decimal_places=decimal_places,
    )
    return result


def create_trader(
    payload: TradePayload,
    price_place="%.1f",
    decimal_places="%.3f",
    trade_type: Literal[
        "long",
        "short",
        "bullish_short",
        "bearish_long",
    ] = "long",
):
    if trade_type in ["long", "short"]:
        payload["kind"] = trade_type
        return simple_trade_generation(
            payload,
            price_place=price_place,
            decimal_places=decimal_places,
        )
    else:
        options = {
            "bullish_short": "long",
            "bearish_long": "short",
        }
        payload["kind"] = options[trade_type]
        return reverse_simple_trader(
            payload,
            price_place=price_place,
            decimal_places=decimal_places,
        )


def determine_trader_risk(payload: TradePayload, decrement: float = 0.5) -> float:
    """
    Calculate the risk value that results in a loss lower than or equal to the risk in the payload.

    Args:
        payload (TradePayload): The trade payload containing the initial risk.
        decrement (float): The decrement value to adjust the risk, default is 0.5.

    Returns:
        float: The adjusted risk value.
    """
    current_risk = payload["risk"]
    while True:
        # Simulate a trade with the current risk
        trade_result = simple_trade_generation({**payload, "risk": current_risk})
        # Calculate the loss from the trade result
        loss = sum(stop.get("loss", 0) for stop in trade_result["stop"])
        # Check if the loss is within the acceptable range
        if loss <= payload["risk"]:
            return current_risk
        # Decrement the risk
        current_risk -= decrement
        if current_risk <= 0:
            break
    return 0


def determine_stop_percent(support: float, resistance: float):
    #     'resistance': {'99950.00': 2,
    #   '95300.00': 3,
    #   '95195.00': 2,
    #   '94537.70': 2,
    #   '93892.50': 2,
    #   '93728.80': 2},
    #  'support': {'93000.00': 8},
    #  'minimum_weekly': 92272.6}
    pass


class CompoundTradeParam(TypedDict):
    resistances: list
    supports: list
    support: float
    risk: float
    fee_percent: float


def build_compound_trades(params: CompoundTradeParam):
    resistances = params["resistances"]
    resistance = max(params["resistances"])
    support = params["support"]
    risk = params["risk"]
    if len(resistances) == 2:
        resistances = []
    _resistances = sorted([x for x in resistances if x != resistance])
    _supports = sorted([x for x in params["supports"]])

    def get_lower_resistance(i):
        # if i >= len(_resistances):
        #     return None
        # if i == 0:
        #     return _supports[-1]
        return _resistances[i + 1]

    def get_lower_support(i):
        if i == 0:
            return support 

        if len(_supports) > 1:
            return _supports[i - 1]
        return support

    actual_supports = []
    # only consider long trades when there are multiple supports
    if len(_supports) > 1:
        actual_supports = _supports
    combined = [
        {
            "entry": x,
            "stop_percent": to_f(((get_lower_resistance(i) / x) - 1) * 100, "%.3f"),
            "kind": "short",
        }
        for i, x in enumerate(_resistances)
        if i < len(_resistances) - 1
    ] + [
        {
            "entry": x,
            "stop_percent": to_f(((x / get_lower_support(i)) - 1) * 100, "%.3f"),
            "kind": "long",
        }
        for i, x in enumerate(actual_supports)
    ]
    min_risk = to_f(risk / len(combined), "%.2f")
    results = [
        {**x, "risk": min_risk, "fee_percent": params["fee_percent"]} for x in combined
    ]
    # breakpoint()
    # return sorted(results, key=lambda x: x["entry"])
    optimized_results = [{**x, "risk": determine_trader_risk(x)} for x in results if x['stop_percent'] > 0]
    return sorted(optimized_results, key=lambda x: x["entry"])
