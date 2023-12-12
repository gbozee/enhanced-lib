import typing
from ..shared import AppConfig, build_config, to_f
from .utils import run_in_parallel, chunks_in_threads


class EvalFuncType(typing.TypedDict):
    result: typing.List[typing.Any]
    value: int
    total: float
    max: float
    min: float
    entry: float
    max_index: int


def eval_func(y: int, config: AppConfig) -> typing.List[EvalFuncType]:
    profit = config.take_profit
    if not profit:
        profit = (
            max(config.entry, config.stop)
            if config.kind == "long"
            else min(config.entry, config.stop)
        )
    params = {
        "take_profit": profit,
        "entry": config.entry,
        "stop": config.stop,
        "no_of_trades": y,
        "risk_reward": y,
        "increase": True,
        "kind": config.kind,
        "decimal_places": config.decimal_places,
    }
    # print("params", params)
    trades = build_config(
        config,
        params,
    )
    # print("trades", trades)
    _max = max([x["entry"] for x in trades]) if trades else 0
    _min = min([x["entry"] for x in trades]) if trades else 0
    # total = sum([x["quantity"] for x in trades])
    # result = {
    #     "result": trades,
    #     "value": y,
    #     "total": total,
    #     "max": max([x["quantity"] for x in trades]) if trades else 0,
    #     "min": min([x["quantity"] for x in trades]) if trades else 0,
    #     "entry": _max if config.kind == "long" else _min,
    # }
    # found_trades = [x for x in trades if x["quantity"] == result["max"]]
    _max_quantity = 0
    _min_quantity = 0
    if trades:
        _min_quantity = trades[0]["quantity"]
    total = 0
    max_index = -1
    total = sum([x["quantity"] for x in trades])
    _max_quantity = max([x["quantity"] for x in trades]) if trades else 0
    _min_quantity = min([x["quantity"] for x in trades]) if trades else 0
    max_index = (
        [o["quantity"] for o in trades].index(_max_quantity) if _max_quantity else -1
    )
    if isinstance(max_index,list):
        max_index = -1
    # for i, x in enumerate(trades):
    #     total += x["quantity"]
    #     _max_quantity = max(_max_quantity, x["quantity"])
    #     _min_quantity = min(_min_quantity, x["quantity"])
    #     if _max_quantity == x["quantity"]:
    #         max_index = i
    result = {
        "result": trades,
        "value": y,
        "total": total,
        "max": _max_quantity,
        "min": _min_quantity,
        "entry": _max if config.kind == "long" else _min,
        "max_index": max_index,
    }
    found_trades = max_index > -1

    if found_trades:
        return result
    return []


def find_index_by_condition(
    lst: typing.List[typing.Any], condition: typing.Callable[[typing.Any], bool]
):
    for i, item in enumerate(lst):
        if condition(item):
            return i
    return -1  # Return -1 if no matching item is found


def determine_optimum_reward(
    app_config: AppConfig, no_of_cpu=4, gap=1, option="default", ignore=False
):
    criterion = app_config.strategy or "quantity"
    risk_rewards = [x for x in range(30, 199, gap)]

    # run each risk reward through the eval function in parallel using multiprocessing
    def passCriterion(x: EvalFuncType):
        if criterion != "quantity":
            return True
        if isinstance(x, list):
            return False
        found_index = x["max_index"]
        # found_index = find_index_by_condition(
        #     x["result"], lambda j: j["quantity"] == x["max"]
        # )
        return found_index == 0

    _options = {"default": run_in_parallel, "chunks": chunks_in_threads}
    if ignore:
        func = [eval_func(x, app_config) for x in risk_rewards]
    else:
        func = _options[option](
            eval_func, [(x, app_config) for x in risk_rewards], no_of_cpu=no_of_cpu
        )
    highest = 0
    new_func = []
    for j in func:
        if passCriterion(j):
            new_func.append(j)
            if criterion == "quantity":
                highest = max(highest, j["max"])
            else:
                if app_config.kind == "long":
                    highest = max(highest, j["entry"])
                else:
                    highest = min(highest, j["entry"])
    func = new_func
    # func = [x for x in func if x and passCriterion(x)]
    # highest = 0
    # if func:
    #     if criterion == "quantity":
    #         highest = max([x["max"] for x in func])
    #     else:
    #         if app_config.kind == "long":
    #             highest = max([x["entry"] for x in func])
    #         else:
    #             highest = min([x["entry"] for x in func])
    key = "max" if criterion == "quantity" else "entry"
    if app_config.as_array:
        working_list = set([x[key] for x in func])
        highest_values = (
            sorted(list(working_list), reverse=True)
            if (criterion == "quantity" or app_config.kind == "long")
            else sorted(list(working_list))
        )[:5]
        considered = [x for x in func if x[key] in highest_values]
        considered_sorted = (
            sorted(considered, key=lambda x: x[key], reverse=True)
            if (criterion == "quantity" or app_config.kind == "long")
            else sorted(considered, key=lambda x: x[key])
        )
        return [x["value"] for x in considered_sorted[:5]]
    index = find_index_by_condition(func, lambda x: x[key] == highest)
    if index > -1:
        if app_config.raw:
            return func[index]
        return func[index].get("value")
    print("func", func)
    print("highest", highest)
    print("index", index)
    raise Exception("No optimum reward found for ",app_config.risk_per_trade)


class TradeInstanceType(typing.TypedDict):
    entry: float
    risk: float
    quantity: float
    sell_price: float
    incurred_sell: float
    stop: float
    pnl: float
    fee: float
    net: float
    incurred: float
    stop_percent: float
    rr: int


class RiskType(typing.TypedDict):
    value: float
    risk_reward: float
    size: float
    trades: typing.List[TradeInstanceType]


def size_resolver(
    trade_no: float, app_config: AppConfig, no_of_cpu=4, with_trades=False
) -> RiskType:
    app_config.risk_per_trade = trade_no
    app_config.raw = True

    result = determine_optimum_reward(app_config, no_of_cpu=no_of_cpu)
    if result:
        r = {
            "value": trade_no,
            "risk_reward": result["value"],
            "size": result["total"],
        }
        if with_trades:
            r["trades"] = result["result"]
        return r
    raise Exception("No optimum reward found")
    # return {
    #     "value": trade_no,
    #     "risk_reward": 1,
    #     "size": 0,
    # }


def determine_optimum_risk(
    app_config: AppConfig,
    max_size: float,
    gap: float = 1,
    no_of_cpu=4,
    with_trades=False,
) -> typing.Optional[RiskType]:
    start_index = 0
    highest = None
    # first = app_config.risk_per_trade + (gap * start_index)
    # result = size_resolver(first, app_config, no_of_cpu=no_of_cpu)
    # print("result", result)
    while True:
        current_risk = app_config.risk_per_trade + (gap * start_index)
        try:
            result = size_resolver(
                current_risk, app_config, no_of_cpu=no_of_cpu, with_trades=with_trades
            )
        except Exception as e:
            print("error", e)
            result = {
                'size': 0,
                'value': current_risk,
                'risk_reward': 0,
                'trades':[]
            }
        size = to_f(result["size"], app_config.decimal_places)
        if size <= max_size:
            print(f"size for risk {current_risk}", size)
            highest = {**result, "size": size}
            # yield result
            start_index += 1
        else:
            break
    return highest


def get_highest(
    func_r: typing.List[typing.Any], max_size: float, key: str, places="%.3f"
):
    func = []
    highest = 0
    for x in func_r:
        value = to_f(x[key], places)
        print("key", key, value)
        if value <= max_size:
            func.append(x)
            highest = max(highest, value)
    return func, highest


def float_range(start: float, stop: float, step: float):
    while start < stop:
        yield start
        start += step


def entry_resolver(stop: float, app_config: AppConfig):
    app_config.stop = stop
    app_config.raw = True
    app_config.strategy = "entry"
    return determine_optimum_reward(app_config, no_of_cpu=4)


def determine_optimum_stop(
    app_config: AppConfig, stop_target: float, gap: float, no_of_cpu=4
):
    start = min(app_config.stop, stop_target)
    stop = max(stop_target, app_config.stop)

    risk_rewards = [x for x in float_range(start, stop, gap)]
    func_r = run_in_parallel(
        entry_resolver, [(x, app_config) for x in risk_rewards], no_of_cpu=no_of_cpu
    )
    func, highest = get_highest(func_r, stop_target, "avg_entry")
    if len(func) == 0:
        return None
    index = find_index_by_condition(func, lambda x: x["avg_entry"] == highest)
    if index > -1:
        return func[index]
