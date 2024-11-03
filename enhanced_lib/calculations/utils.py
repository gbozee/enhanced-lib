from typing import Iterable, List, Optional, Tuple, TypeVar
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
