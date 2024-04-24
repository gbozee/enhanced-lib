from .maintenance_margin import (
    leverage_100,
    leverage_125,
    leverage_20,
    leverage_25,
    leverage_75,
    leverage_50,
    coin_leverage_100,
    coin_leverage_125,
    coin_leverage_75,
    coin_leverage_20,
    coin_leverage_50,
    coin_leverage_25,
    calc,
)


def get_maintenance_margin(position_size, max_leverage=125, coin_type=False, **kwargs):
    options = {
        125: leverage_125,
        100: leverage_100,
        75: leverage_75,
        50: leverage_50,
        25: leverage_25,
        20: leverage_20,
        # "coin_75": coin_leverage_75,
        # "coin_50": coin_leverage_50,
        # "coin_25": coin_leverage_25,
    }
    if coin_type:
        options = {
            125: coin_leverage_125,
            100: coin_leverage_100,
            75: coin_leverage_75,
            50: coin_leverage_50,
            25: coin_leverage_25,
            20: coin_leverage_20,
        }
    try:
        func = options[max_leverage]
    except IndexError as e:
        print(f"Failed maximum_leverage {max_leverage} with coin {coin_type}")
        func = coin_leverage_125
    result = func(position_size, **kwargs)
    value = result["value"]
    base_value = result["base_value"]
    minimum = result["minimum"]
    if position_size > minimum:
        previous = get_maintenance_margin(
            base_value, max_leverage=max_leverage, coin_type=coin_type, **kwargs
        )
        value["m_a"] = round(calc(base_value, value, previous))
    value["m_t"] = value["m_rate"] * position_size / 100
    return value


def calculate_position_size(entry, size, contract_size=None):
    if contract_size:
        new_size = size * contract_size
        if new_size:
            btc_size = new_size / entry
            return btc_size
    return entry * size


def get_size(size, kind="usdt"):
    return size


def contract_balance(value, entry, kind="usdt", symbol="btc"):
    return value


def determine_liquidation(
    balance,
    long_position,
    short_position,
    both_position={"entry": 0, "size": 0},
    additional=None,
    contract_size=None,
    maximum_leverage=125,
    symbol="",
):
    coin_type = contract_size is not None
    wallet_balance = balance
    unrealized_pnl = 0
    direction = -1
    entry_one_way = 0
    size_one_way = 0
    size_hedge_long = 0
    size_hedge_short = 0
    entry_hedge_long = 0
    entry_hedge_short = 0
    if both_position:
        entry_one_way = both_position["entry"]
        size_one_way = both_position["size"]

    if long_position and short_position:
        size_hedge_long = long_position["size"]
        size_hedge_short = short_position["size"]
        entry_hedge_long = long_position["entry"]
        entry_hedge_short = short_position["entry"]
    if additional:
        _long = additional.get("long")
        short = additional.get("short")
        if _long:
            size_hedge_long = _long["size"] + size_hedge_long
            entry_hedge_long = (
                (entry_hedge_long * long_position["size"])
                + (_long["entry"] * _long["size"])
            ) / (size_hedge_long or 1)
        if short:
            size_hedge_short = short["size"] + size_hedge_short
            entry_hedge_short = (
                (entry_hedge_short * short_position["size"])
                + (short["entry"] * short["size"])
            ) / (size_hedge_short or 1)

    mm_one_way = get_maintenance_margin(
        calculate_position_size(
            entry_one_way, size_one_way, contract_size=contract_size
        ),
        max_leverage=maximum_leverage,
        coin_type=coin_type,
        symbol=symbol,
    )
    mm_hedge_long = get_maintenance_margin(
        calculate_position_size(
            entry_hedge_long, size_hedge_long, contract_size=contract_size
        ),
        max_leverage=maximum_leverage,
        coin_type=coin_type,
        symbol=symbol,
    )
    mm_hedge_short = get_maintenance_margin(
        calculate_position_size(
            entry_hedge_short, size_hedge_short, contract_size=contract_size
        ),
        max_leverage=maximum_leverage,
        coin_type=coin_type,
        symbol=symbol,
    )
    maintenance_margin_one_way = mm_one_way["m_rate"] / 100
    maintenance_margin_long = mm_hedge_long["m_rate"] / 100
    maintenance_margin_short = mm_hedge_short["m_rate"] / 100
    maintenance_amount_one_way = mm_one_way["m_a"]
    maintenance_amount_hedge_long = mm_hedge_long["m_a"]
    maintenance_amount_hedge_short = mm_hedge_short["m_a"]
    maintenance_margin = 0

    if coin_type:
        one_way_div = 0
        if entry_one_way > 0:
            one_way_div = size_one_way / entry_one_way
        hedge_long_div = 0
        if entry_hedge_long:
            hedge_long_div = size_hedge_long / entry_hedge_long
        hedge_short_div = 0
        if entry_hedge_short:
            hedge_short_div = size_hedge_short / entry_hedge_short
        liquidation = (
            size_one_way * maintenance_margin_one_way
            + size_hedge_long * maintenance_margin_long
            + size_hedge_short * maintenance_margin_short
            + direction * size_one_way
            + size_hedge_long
            - size_hedge_short
        ) / (
            (
                wallet_balance
                - maintenance_margin
                + unrealized_pnl
                + maintenance_amount_one_way
                + maintenance_amount_hedge_long
                + maintenance_amount_hedge_short
            )
            / (contract_size
            + direction * one_way_div
            + hedge_long_div
            - hedge_short_div)
        )

    else:
        below = (
            get_size(size_one_way) * maintenance_margin_one_way
            + get_size(size_hedge_long) * maintenance_margin_long
            + get_size(size_hedge_short) * maintenance_margin_short
            - direction * get_size(size_one_way)
            - get_size(size_hedge_long)
            + get_size(size_hedge_short)
        )
        liquidation = 0
        if below:
            liquidation = (
                wallet_balance
                - maintenance_margin
                + unrealized_pnl
                + maintenance_amount_one_way
                + maintenance_amount_hedge_long
                + maintenance_amount_hedge_short
                # - direction * get_size(size_one_way, kind) * entry_one_way
                - direction
                * calculate_position_size(
                    entry_one_way, size_one_way, contract_size=contract_size
                )
                # - get_size(size_hedge_long, kind=kind) * entry_hedge_long
                - calculate_position_size(
                    entry_hedge_long, size_hedge_long, contract_size=contract_size
                )
                # + get_size(size_hedge_short, kind=kind) * entry_hedge_short
                + calculate_position_size(
                    entry_hedge_short, size_hedge_short, contract_size=contract_size
                )
            ) / below
    data = {
        "liquidation": liquidation,
        "long": {"entry": entry_hedge_long, "size": size_hedge_long},
        "short": {"entry": entry_hedge_short, "size": size_hedge_short},
    }
    return data


def determine_pnl(
    entry, close_price, quantity, leverage=None, kind="long", contract_size=None
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


def calculate_liquidation(
    balance,
    _long,
    short,
    additional=None,
    pnl=None,
    both=None,
    contract_size=None,
    leverage=125,
    symbol=None,
):
    result = determine_liquidation(
        balance,
        _long,
        short,
        both,
        None,
        contract_size=contract_size,
        maximum_leverage=leverage,
        symbol=symbol,
    )
    if pnl:
        _longs = pnl["long"]
        _short = pnl["short"]
        result_long = result["long"]
        result_short = result["short"]
        profit = 0
        if _longs:
            l_profit = (
                determine_pnl(
                    result["long"]["entry"],
                    _longs["entry"],
                    _longs["size"],
                    "long",
                    contract_size,
                )
                or 0
            )
            profit += l_profit
            result_long = {
                **result["long"],
                "size": result["long"]["size"] - _longs["size"],
            }
        if _short:
            s_profit = (
                determine_pnl(
                    result["short"]["entry"],
                    _short["entry"],
                    _short["size"],
                    "short",
                    contract_size,
                )
                or 0
            )
            profit += s_profit
            result_short = {
                **result["short"],
                "size": result["short"]["size"] - _short["size"],
            }

        if profit > 0:
            new_liquidation = determine_liquidation(
                balance + profit,
                result_long,
                result_short,
                contract_size=contract_size,
                maximum_leverage=leverage,
                symbol=symbol,
            )
            return {**new_liquidation, "pnl": profit, "balance": balance + profit}
    if additional:
        result = determine_liquidation(
            result.get("balance", 0) or balance,
            result.get("long"),
            result.get("short"),
            both,
            additional=additional,
            contract_size=contract_size,
            maximum_leverage=leverage,
            symbol=symbol,
        )

    return result


def calculate_maximum_size(
    balance, _long, short, current_price, leverage=125, contract_size=None
):
    if _long and short:
        long_pnl = determine_pnl(
            _long["entry"], current_price, _long["size"], kind="long"
        )
        short_pnl = determine_pnl(
            short["entry"], current_price, short["size"], kind="short"
        )
        pnl = long_pnl + short_pnl
        remaining = balance + pnl
        r_nominal = remaining * leverage
        left = (
            r_nominal
            - (_long["entry"] * _long["size"])
            - (short["entry"] * short["size"])
        )
        result = left / leverage
        liquidation = calculate_liquidation(
            balance, _long, short, contract_size=contract_size, leverage=leverage
        )
        m_long = get_maintenance_margin(
            calculate_position_size(current_price, _long["size"])
        )["m_t"]
        m_short = get_maintenance_margin(
            calculate_position_size(current_price, short["size"])
        )["m_t"]
        return {
            "balance": float("%.2f" % result),
            "quantity": float("%.3f" % (left / current_price)),
            "liquidation": float("%.2f" % liquidation["liquidation"]),
            "maintenance_margin": float("%.2f" % (m_long + m_short)),
            "pnl": float("%.2f" % pnl),
        }
    return {}


def get_entry(target_liquidation, wallet_balance, _long, short, kind="long"):
    long_size = _long["size"]
    short_size = short["size"]
    if kind == "long":
        m_short = get_maintenance_margin(
            calculate_position_size(short["entry"], short["size"])
        )
    else:
        m_short = get_maintenance_margin(
            calculate_position_size(_long["entry"], _long["size"])
        )
    rate = m_short["m_rate"] / 100
    if kind == "long":
        result = target_liquidation * (
            (
                (
                    (short["entry"] * short["size"] / target_liquidation)
                    + (wallet_balance / target_liquidation)
                    - (short["size"] * (rate + 1))
                )
                / long_size
            )
            - (rate - 1)
        )
    else:
        result = (target_liquidation / short_size) * (
            (short_size * (rate + 1))
            + (_long["size"] * ((_long["entry"] / target_liquidation) + (rate - 1)))
            - (wallet_balance / target_liquidation)
        )
    return float("%.2f" % result)


def get_size_for_target_liquidation(
    target_liquidation, wallet_balance, _long, short, kind="short"
):
    if kind == "short":
        m_long = get_maintenance_margin(
            calculate_position_size(_long["entry"], _long["size"])
        )
    else:
        m_long = get_maintenance_margin(
            calculate_position_size(short["entry"], short["size"])
        )
    rate = m_long["m_rate"] / 100
    if kind == "short":
        result = (
            (wallet_balance / target_liquidation)
            - ((_long["entry"] * _long["size"]) / target_liquidation)
            - (_long["size"] * (rate - 1))
        ) / ((rate + 1) - (short["entry"] / target_liquidation))
    else:
        result = (
            (short["entry"] * short["size"] / target_liquidation)
            + (wallet_balance / target_liquidation)
            - (short["size"] * (rate + 1))
        ) / ((_long["entry"] / target_liquidation) + (rate - 1))
    return float("%.3f" % result)


def determine_new_entry(
    ideal_position, previous_position, price_places="%.2f", decimal_places="%.3f"
):
    new_size = ideal_position["size"] - previous_position["size"]
    result = (
        ideal_position["entry"] * ideal_position["size"]
        - previous_position["entry"] * previous_position["size"]
    ) / new_size
    return {
        "entry": float(price_places % result),
        "size": float(decimal_places % new_size),
    }


def get_ideal_entry_and_size(
    target_liquidation,
    wallet_balance,
    _long,
    short,
    kind="short",
    price_places="%.2f",
    decimal_places="%.3f",
):
    size = get_size_for_target_liquidation(
        target_liquidation,
        wallet_balance,
        _long,
        short,
        kind=kind,
        # decimal_places
    )
    _short = {**short}
    if kind == "short":
        _short["size"] = size
    else:
        _long["size"] = size

    entry = get_entry(
        target_liquidation,
        wallet_balance,
        _long,
        _short,
        kind=kind,
        # price_places,
    )
    buy_point = None
    sell_point = None
    if kind == "long" and size > _long["size"]:
        buy_point = determine_new_entry(
            {"entry": entry, "size": size}, _long, price_places, decimal_places
        )
    if kind == "short" and size > short["size"]:
        sell_point = determine_new_entry(
            {"entry": entry, "size": size}, short, price_places, decimal_places
        )
    additional = {}
    if buy_point:
        ideal = None
        if buy_point["entry"] > _long["entry"]:
            diff = abs(buy_point["entry"] - _long["entry"])
            ideal = {"entry": _long["entry"] - diff, "size": buy_point["size"]}
        additional["long"] = {"raw": buy_point, "ideal": ideal}
    if sell_point:
        ideal = None
        if sell_point["entry"] < short["entry"]:
            diff = abs(sell_point["entry"] - short["entry"])
            ideal = {"entry": short["entry"] + diff, "size": sell_point["size"]}
        additional["short"] = {"raw": sell_point, "ideal": ideal}
    result = {"entry": entry, "size": size}
    if additional.get("long") or additional.get("short"):
        result["additional"] = additional
    return result


def determine_entry(
    _long,
    short,
    config,
    price_places="%.2f",
    fee=0,
    current_price=None,
    decimal_places="%.3f",
):

    kind = config.get("bias") or "long"
    budget = config.get("budget")
    support = config.get("support")
    minimum_size = config.get("minimum_size")
    bullish = config.get("bullish")
    bias_r = config.get("bias_r")
    spread = config.get("spread")

    if not _long.get("entry") or not short.get("entry"):
        long_exists = True
        short_exists = True
        long_entry = _long.get("entry")
        if not long_entry:
            long_exists = False
        short_entry = short.get("entry")
        if not short_entry:
            short_exists = False
        result = {}
        if not long_exists:
            result["long"] = {
                "quantity": float(decimal_places % config["maximum_size"]),
                "price": float(price_places % current_price),
            }
        if not short_exists:
            result["short"] = {
                "quantity": float(decimal_places % config["maximum_size"]),
                "price": float(price_places % current_price),
            }
        return {"open": result, "close": {}}
    if _long["size"] == short["size"] and _long["size"] < config["maximum_size"]:
        diff = abs(_long["entry"] - short["entry"])
        f_diff = diff * config["r_ratio"]
        size = config["maximum_size"] - _long["size"]
        long_entry = _long["entry"] - f_diff
        short_entry = short["entry"] + f_diff
        return {
            "open": {
                "long": {
                    "quantity": float(decimal_places % size),
                    "price": float(price_places % long_entry),
                },
                "short": {
                    "quantity": float(decimal_places % size),
                    "price": float(price_places % short_entry),
                },
            }
        }
    # if (
    #     _long["size"] >= config["maximum_size"]
    #     or short["size"] >= config["maximum_size"]
    # ):
    result = {}
    open_result = {}
    from example import pnl

    if kind == "long":
        diff = abs(_long["entry"] - short["entry"])
        new_size = get_size_for_target_liquidation(
            support, budget, _long, short, kind="short"
        )
        if diff <= spread:
            klose = pnl.determine_close_price(
                _long["entry"], bias_r * budget, _long["size"], kind=kind
            )["close"]
            result["long"] = {
                "price": float(price_places % klose),
                "quantity": float(decimal_places % _long["size"]),
            }
        elif short["size"] >= config["maximum_size"]:
            sell_size = abs(new_size - short["size"])
            klose = get_close_price(short, config, kind="short", fee=fee)
            result["short"] = {
                "price": float(price_places % klose),
                "quantity": float(decimal_places % sell_size),
            }
        elif _long["size"] >= config["maximum_size"]:
            sell_size = abs(config["maximum_size"] - _long["size"])
            if short["size"] < _long["size"]:
                sell_size = abs(_long["size"] - short["size"])
            if not sell_size:
                sell_size = abs(new_size - _long["size"])
            if sell_size > minimum_size:
                klose = get_close_price(_long, config, kind="long", fee=fee)
                result["long"] = {
                    "price": float(price_places % klose),
                    "quantity": float(decimal_places % sell_size),
                }
        elif short["size"] >= _long["size"]:
            sell_size = abs(new_size - short["size"])
            if sell_size > minimum_size:
                klose = get_close_price(short, config, kind="short", fee=fee)
                result["short"] = {
                    "price": float(price_places % klose),
                    "quantity": float(decimal_places % sell_size),
                }
        elif _long["size"] > short["size"]:
            sell_size = abs(short["size"] - _long["size"])
            if (sell_size > minimum_size) and not bullish:
                klose = get_close_price(_long, config, kind="long", fee=fee)
                result["long"] = {
                    "price": float(price_places % klose),
                    "quantity": float(decimal_places % sell_size),
                }
    if result or open_result:
        return {"close": result, "open": open_result}


def get_close_price(short, config, kind="short", fee=0):
    from example import pnl

    budget = config.get("budget")
    support = config.get("support")
    sell_at_entry = config.get("sell_at_entry")
    bias_r = config.get("bias_r")
    if sell_at_entry:
        klose = pnl.determine_close_price(
            short["entry"], fee / 100, short["size"], kind=kind
        )["close"]
    else:
        klose = pnl.determine_close_price(
            short["entry"], bias_r * budget, short["size"], kind=kind
        )["close"]
    return klose


def calculate_avg_entry(
    start, stop, size, total_size, minimum=0.001, direction="+", current_price=None
):
    # remaining = total_size - size
    remaining = total_size
    diff = abs(start - stop)
    count = int(remaining / minimum)
    spread = diff / count
    if direction == "+":
        first = min(start, stop)
        array = [
            {"entry": first + (x * spread), "size": minimum}
            for x in range(1, count)
            if (x + spread) < max(start, stop)
        ]
        if current_price:
            array = [{"entry": first - spread, "size": minimum}] + array
    else:
        first = max(start, stop)
        array = [
            {"entry": first - (x * spread), "size": minimum}
            for x in range(1, count)
            if (x + spread) < max(start, stop)
        ]
        if current_price:
            array = [{"entry": first + spread, "size": minimum}] + array
    result = start if direction == "+" else stop
    if array:
        total = sum([x["size"] for x in array])
        avg = sum([x["entry"] * x["size"] for x in array]) / total
        result = ((first * size) + (avg * total)) / (size + total)

    return {"result": result, "array": array}


def get_orders_to_execute_and_reduce(
    _long,
    short,
    budget,
    current_price=None,
    spread=20,
    minimum_size=0.001,
    fee=0,
    price_places="%.2f",
    decimal_places="%.3f",
    resistance=None,
    support=None,
    display=False,
    leverage=125,
    contract_size=None,
):
    result = {}
    size = _long["size"]
    ux = calculate_maximum_size(
        budget,
        _long,
        short,
        current_price,
        leverage=leverage,
        contract_size=contract_size,
    )
    liquidation = ux["liquidation"]
    qty = ux["quantity"]
    if display:
        result["liquidation"] = liquidation
        result["max_quantity"] = qty
    # qty = max_quantity / 2
    if (
        _long["entry"] > short["entry"]
        # and (_long["entry"] - short["entry"]) > spread
        and ((_long["size"] + short["size"]) < qty)
    ):
        # if _long["size"] == short["size"]:
        direction = "+" if _long["entry"] > short["entry"] else "-"
        max_result = calculate_avg_entry(
            _long["entry"],
            short["entry"],
            size,
            qty,
            direction=direction,
            minimum=minimum_size,
            current_price=current_price,
        )
        long_r = [x for x in max_result["array"] if x["entry"] <= current_price]
        short_r = [x for x in max_result["array"] if x["entry"] >= current_price]
        _open = {}
        vv = lambda r: {
            "quantity": float(decimal_places % r["size"]),
            "price": float(price_places % r["entry"]),
        }
        if direction == "+":
            # if _min == _long["entry"]:
            if long_r:
                r = long_r[-1]
                _open["long"] = vv(long_r[-1])
            if short_r:
                _open["short"] = vv(short_r[0])
            if support < liquidation < current_price:
                if _open.get("long"):
                    del _open["long"]
            if current_price < liquidation < resistance:
                if _open.get("short"):
                    del _open["short"]
        result["open"] = _open
        from example import pnl

        to_reduce = abs(_long["size"] - short["size"])
        kind = None
        _close = {}
        entry = None
        quantity = None
        # if _long["size"] > short["size"]:
        if resistance and support:
            # if liquidation < support:
            if support < liquidation < current_price:
                entry = _long["entry"]
                quantity = _long["size"]
                kind = "long"
            # if short["size"] > _long["size"]:
            # if liquidation > resistance:
            if current_price < liquidation < resistance:
                entry = short["entry"]
                quantity = short["size"]
                kind = "short"
        if kind:
            _pnl = fee * entry * quantity / 100
            close = pnl.determine_close_price(entry, _pnl, quantity, kind=kind)["close"]
            _close[kind] = {
                "price": float(price_places % close),
                "quantity": float(decimal_places % minimum_size),
            }
        else:
            pass
        if _close:
            result["close"] = _close

    return result


def determine_order_based_on_maximum(
    _long, short, config, current_price=None, contract_size=None, leverage=125
):
    budget = config.get("budget")
    support = config.get("support")
    resistance = config.get("resistance")
    minimum_size = config.get("minimum_size")
    start_size = config.get("start_size")
    price_places = config.get("price_places")
    decimal_places = config.get("decimal_places")
    maximum_size = config.get("maximum_size")
    spread = config.get("spread")
    bias = config.get("bias")
    bias_r = config.get("bias_r")
    _reduce = config.get("reduce")
    leverage = config.get("leverage")
    ux = calculate_maximum_size(
        budget,
        _long,
        short,
        current_price,
        leverage=leverage,
        contract_size=contract_size,
    )
    open_trade = create_orders_respecting_liquidation(
        current_price,
        budget,
        support,
        resistance,
        minimum_size=minimum_size,
        start_size=start_size,
        price_places=price_places,
        decimal_places=decimal_places,
        long_position=_long,
        short_position=short,
        bias=bias,
        leverage=leverage,
        contract_size=contract_size,
    )
    long_trade = open_trade.get("long")
    short_trade = open_trade.get("short")
    result = {"open": {}, "close": {}}
    if not _reduce:
        if long_trade or short_trade:
            ll = long_trade.get("quantity") if long_trade else 0
            ss = short_trade.get("quantity") if short_trade else 0
            bb = {"long": long_trade, "short": short_trade}
            if not bb.get("long"):
                del bb["long"]
            if not bb.get("short"):
                del bb["short"]
            result["open"] = bb
        from example import pnl

        if _long and _long.get("size") > 0:
            close = pnl.determine_close_price(
                _long["entry"], bias_r * budget, _long["size"], kind="long"
            )["close"]
            result["close"]["long"] = {
                "price": float(price_places % close),
                "quantity": _long["size"],
            }
        if short and short.get("size") > 0:
            close = pnl.determine_close_price(
                short["entry"], bias_r * budget, short["size"], kind="short"
            )["close"]
            result["close"]["short"] = {
                "price": float(price_places % close),
                "quantity": short["size"],
            }
    else:
        value = get_orders_to_execute_and_reduce(
            _long or {"entry": 0, "size": 0},
            short or {"entry": 0, "size": 0},
            budget,
            current_price,
            spread=spread,
            minimum_size=minimum_size,
            support=support,
            resistance=resistance,
            contract_size=contract_size,
            leverage=leverage,
        )
        result["open"] = value.get("open")
        result["close"] = value.get("close")
    return result


def create_orders_respecting_liquidation(
    current_price,
    budget,
    support,
    resistance,
    minimum_size=0.001,
    start_size=0.001,
    bias="long",
    long_position=None,
    short_position=None,
    price_places="%.2f",
    decimal_places="%.3f",
    leverage=125,
    contract_size=None,
):
    _long = long_position or {}
    short = short_position or {}
    # if not _long.get("size"):
    #     _long = {}
    # if not short.get("size"):
    #     short = {}
    if not long_position and not short_position:
        return {
            "long": {"price": current_price, "quantity": start_size},
            "short": {"price": current_price, "quantity": start_size},
        }
    _long = _long or {"entry": 0, "size": 0}
    short = short or {"entry": 0, "size": 0}
    ux = calculate_maximum_size(
        budget,
        _long,
        short,
        current_price,
        leverage=leverage,
        contract_size=contract_size,
    )
    quantity = ux.get("quantity")
    liquidation = ux.get("liquidation")
    # if (quantity /2) >
    if (_long["size"] + short["size"]) < (quantity - (minimum_size * 2)):
        long_entry = get_ideal_entry_and_size(
            support, budget, {**_long}, {**short}, kind="long"
        )
        short_entry = get_ideal_entry_and_size(
            resistance, budget, {**_long}, {**short}, kind="short"
        )
        __long = None
        if long_entry["size"] > _long["size"]:
            __long = {"entry": long_entry["entry"], "size": long_entry["size"]}
        __short = None
        if short_entry["size"] > short["size"]:
            __short = {"entry": short_entry["entry"], "size": short_entry["size"]}
        if long_entry.get("additional"):
            __long = long_entry["additional"]["long"]["raw"]
        if short_entry.get("additional"):
            __short = short_entry["additional"]["short"]["raw"]
        if not _long.get("size"):
            __long = {"entry": current_price, "size": start_size}
        if not short.get("size"):
            __short = {"entry": current_price, "size": start_size}
        result = {"liquidation": liquidation, "quantity": quantity}
        vv = lambda r: {
            "quantity": float(decimal_places % r["size"]),
            "price": float(price_places % r["entry"]),
        }
        if __long:
            result["long"] = vv(__long)
            if result["long"]["price"] > current_price:
                result["long"]["force_market"] = True

        if __short:
            result["short"] = vv(__short)
            if result["short"]["price"] < current_price:
                result["short"]["force_market"] = True

        return result
    return {"liquidation": liquidation, "quantity": quantity}


def getSize2(
    config,
    openTrade,
    contract_size=0,
    budget=0,
):
    from example.pnl import determine_close_price

    _budget = budget or config["budget"]
    pnl = (
        _budget * config["bias_r"] * config["long_p"]
        if openTrade["kind"] == "long"
        else _budget * config["other_r"] * config["short_p"]
    )
    quantity = (
        openTrade["quantity"] * config["long_p"]
        if openTrade["kind"] == "long"
        else openTrade["quantity"] * config["short_p"]
    )
    close = determine_close_price(
        openTrade["entryPrice"],
        pnl,
        quantity,
        kind=openTrade["kind"],
        contract_size=contract_size,
        single=True,
    )
    return {"takeProfit": close, "pnl": pnl, "quantity": quantity}


def profitHelper(
    longPosition,
    shortPosition,
    config=None,
    contract_size=0,
    balance=0,
):
    _long = {"takeProfit": 0, "quantity": 0, "pnl": 0}
    short = {"takeProfit": 0, "quantity": 0, "pnl": 0}
    if longPosition:
        _long = getSize2(config, longPosition, contract_size, balance) or 0

    if shortPosition:
        short = getSize2(config, shortPosition, contract_size, balance) or 0

    return {"long": _long, "short": short}


def liquidationAnalysis(
    kind,
    longPosition,
    shortPosition,
    config,
    balance,
    leverage=125,
    additionalFunc=lambda config: {
        "long": {"entry": config["long_e"], "size": config["long_s"]},
        "short": {"entry": config["short_e"], "size": config["short_s"]},
    },
    contract_size=None,
):
    if config:
        profit = profitHelper(
            longPosition,
            shortPosition,
            config,
            contract_size,
            balance,
        )
        longSize = longPosition["quantity"] * config["long_p"] if longPosition else 0
        shortSize = (
            shortPosition["quantity"] * config["short_p"] if shortPosition else 0
        )
        pnlLong = {
            "long": {"entry": profit["long"]["takeProfit"] or 0, "size": longSize},
            "short": {
                "entry": profit["short"]["takeProfit"] or 0,
                "size": shortSize,
            },
        }
        kindProps = additionalFunc(config) if kind == "additional" else None
        result = calculate_liquidation(
            balance,
            {
                "entry": longPosition["entryPrice"],
                "size": longPosition["quantity"],
            }
            if longPosition
            else {"entry": 0, "size": 0},
            {
                "entry": shortPosition["entryPrice"],
                "size": shortPosition["quantity"],
            }
            if shortPosition
            else {"entry": 0, "size": 0},
            additional=kindProps,
            pnl=pnlLong,
            both=None,
            leverage=leverage,
            contract_size=contract_size,
            symbol=config["symbol"],
        )
        if not result.get("balance"):
            result["balance"] = balance
        return result
    return {}


def determine_liquidation_after_purchase(
    long_position,
    short_position,
    balance,
    minimum=0.005,
    entry_price=0.001,
    size_increment=1,
    spread=10,
    max_size=10,
    symbol=None,
    contract_size=100,
    leverage=125,
    direction="long",
):
    config = {
        "long_e": long_position["entry"],
        "long_s": long_position["size"],
        "short_e": short_position["entry"],
        "short_s": short_position["size"],
        "long_p": 0,
        "short_p": 0,
        "bias_r": 0.25,
        "other_r": 0.25,
        "symbol": symbol,
        "along_e": 0,
        "along_s": 0,
    }
    longPosition = lambda _config: {
        "entryPrice": _config["long_e"],
        "quantity": _config["long_s"],
        "contractSize": contract_size,
        "kind": "long",
    }
    shortPosition = lambda _config: {
        "entryPrice": _config["short_e"],
        "quantity": _config["short_s"],
        "contractSize": contract_size,
        "kind": "short",
    }
    additionalFunc = lambda config: {
        "long": {"entry": config.get("along_e", 0), "size": config.get("along_s", 0)},
        "short": {
            "entry": config.get("ashort_e", 0),
            "size": config.get("ashort_s", 0),
        },
    }
    kind = "additional"
    _liquidation = 0

    evaluator = lambda: config["long_s"] if direction == "long" else config["short_s"]
    from example.pnl import determine_pnl

    while evaluator() < max_size:
        if (
            direction == "long"
            and config["short_s"] == 0
            and config["long_s"] > minimum and entry_price
        ):
            config["short_e"] = config["along_e"]
            config["short_s"] = entry_price
            long_pnl = determine_pnl(
                config["long_e"],
                config["short_e"],
                config["long_s"],
                kind="long",
                contract_size=contract_size,
            )
            print(
                f"short entry_price is {config['short_e']} and long entry_price is {config['long_e']} and long_pnl is {long_pnl}"
            )
        if (
            direction == "short"
            and config["long_s"] == 0
            and config["short_s"] > minimum and entry_price
        ):
            config["long_e"] = config["ashort_e"]
            config["long_s"] = entry_price
            short_pnl = determine_pnl(
                config["short_e"],
                config["long_e"],
                config["short_s"],
                kind="short",
                contract_size=contract_size,
            )
            print(
                f"long entry_price is {config['long_e']} and short_entry_price is {config['short_e']} and short_pnl is {short_pnl}"
            )
        if direction == "long":
            config["along_e"] = config["long_e"] - spread
            config["along_s"] = size_increment
        else:
            config["ashort_e"] = config["short_e"] - spread
            config["ashort_s"] = size_increment
        result = liquidationAnalysis(
            kind,
            longPosition(config),
            shortPosition(config),
            config,
            balance,
            leverage=leverage,
            additionalFunc=additionalFunc,
            contract_size=contract_size,
        )
        vv = {"entry": config["along_e"], "size": config["along_s"]}
        if direction == "short":
            vv = {"entry": config["ashort_e"], "size": config["ashort_s"]}
        print(f"result is {result} purchase_points: {vv}")
        _liquidation = result["liquidation"]
        config["long_e"] = result["long"]["entry"]
        config["long_s"] = result["long"]["size"]
        config["short_e"] = result["short"]["entry"]
        config["short_s"] = result["short"]["size"]

    return {
        "liquidation": _liquidation,
        "entry": config["long_e"],
        "size": config["long_s"],
    }


def determine_profit_count(position, spread, profit, kind="long", contract_size=None):
    total_profit = 0
    count = 0
    new_position = {**position}
    from example.pnl import determine_pnl

    final_close = 0
    per_profit = 0
    while total_profit < profit:
        close = new_position["entry"] + spread
        if kind == "short":
            close = new_position["entry"] - spread
        pnl = determine_pnl(
            new_position["entry"],
            close,
            new_position["size"],
            kind=kind,
            contract_size=contract_size,
        )
        per_profit = pnl
        count += 1
        total_profit += pnl
        new_position["entry"] = close
        final_close = close
        print(total_profit)
    return {"profit": total_profit, "count": count, "close": final_close,'per_profit':per_profit}
