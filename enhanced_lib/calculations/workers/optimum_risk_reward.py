import typing
from ..shared import AppConfig, build_config, to_f
from .utils import run_in_parallel, chunks_in_threads
import math
import signal


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
    entry = (
        max(config.entry, config.stop)
        if config.kind == "long"
        else min(config.entry, config.stop)
    )
    stop = (
        min(config.entry, config.stop)
        if config.kind == "long"
        else max(config.entry, config.stop)
    )
    params = {
        "take_profit": profit,
        "entry": entry,
        "stop": stop,
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
    if not trades:
        return {
            "result": [],
            "value": y,
            "total": 0,
            "max": 0,
            "min": 0,
            "entry": 0,
            "max_index": -1,
        }
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
    avg_size = 0
    _pnl = 0
    neg_pnl = 0
    if trades:
        _min_quantity = trades[0]["quantity"]
        avg_size = trades[0]["avg_size"]
        _pnl = trades[0]["pnl"]
        neg_pnl = trades[0]["neg.pnl"]
    total = 0
    max_index = -1
    total = sum([x["quantity"] for x in trades])
    _max_quantity = max([x["quantity"] for x in trades]) if trades else 0
    _min_quantity = min([x["quantity"] for x in trades]) if trades else 0
    # if config.kind == "long":
    #     _max_quantity = max([x["quantity"] for x in trades[1:]]) if trades[1:] else 0
    max_index = (
        [o["quantity"] for o in trades].index(_max_quantity) if _max_quantity else -1
    )
    if isinstance(max_index, list):
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
        "size": avg_size,
        "total": total,
        "max": _max_quantity,
        "min": _min_quantity,
        "entry": _max if config.kind == "long" else _min,
        "pnl": _pnl,
        "neg.pnl": neg_pnl,
        "max_index": max_index,
        "risk_per_trade": config.risk_per_trade,
    }
    found_trades = max_index > -1

    if found_trades:
        return result
    return []

    # def find_index_by_condition(
    #     lst: typing.List[typing.Any],
    #     condition: typing.Callable[[typing.Any], bool],
    #     default_key="pnl",
    # ):
    #     found = []
    #     for i, item in enumerate(lst):
    #         if condition(item):
    #             found.append(i)
    #             # return i
    #     if len(found) == 1:
    #         return found[0]
    #     if len(found) == 0:
    #         return -1
    #     maximum = max(found, key=lambda x: lst[x][default_key])
    #     return maximum
    return -1  # Return -1 if no matching item is found


def find_index_by_condition(
    lst: typing.List[typing.Any],
    kind: str,
    default_key="neg.pnl",
    loss=None,
) -> int:
    found = []
    new_lst = [{**i, "net_diff": i["neg.pnl"] + i["risk_per_trade"]} for i in lst]

    for index, item in enumerate(new_lst):
        if item["net_diff"] > 0:
            found.append(index)

    transformed_found = [{**new_lst[i], "index": i} for i in found]
    sorted_found = sorted(
        (i for i in transformed_found if i["net_diff"] > 0),
        key=lambda x: (-x["total"], -x["net_diff"]),
    )
    if default_key == "quantity":
        if loss:
            sorted_found = [x for x in sorted_found if abs(x["neg.pnl"]) >= loss]
        return sorted_found[0]["index"] if sorted_found else -1

    if len(found) == 1:
        return found[0]

    if not found:
        return -1

    def entry_condition(a, b):
        if kind == "long":
            return a["entry"] > b["entry"]
        return a["entry"] < b["entry"]

    maximum = found[0]
    for current_index in found:
        if new_lst[current_index]["net_diff"] < new_lst[maximum][
            "net_diff"
        ] and entry_condition(new_lst[current_index], new_lst[maximum]):
            maximum = current_index

    return maximum


def determine_optimum_reward(
    app_config: AppConfig, no_of_cpu=4, gap=1, option="default", ignore=False, loss=None
):
    criterion = app_config.strategy or "quantity"
    risk_rewards = [x for x in range(30, 199, gap)]
    # if criterion == "quantity":
    #     risk_rewards = [x for x in range(100, 199, gap)]

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
        if found_index == 0:
            return True
        return found_index > -1

    func = [eval_func(x, app_config) for x in risk_rewards]
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
                    highest = min(highest, j["entry"]) if highest > 0 else j["entry"]
    old_func = [x for x in func]
    func = new_func
    key = "max" if criterion == "quantity" else "entry"
    index = find_index_by_condition(
        func,
        app_config.kind,
        criterion,
        loss=loss,
        # default_key="pnl" if app_config.kind == "short" else "max",
    )
    if index > -1:
        if app_config.raw:
            return func[index]
        return func[index].get("value")
    print("func", func)
    print("old_func", old_func)
    print("highest", highest)
    print("index", index)
    raise Exception("No optimum reward found for ", app_config.risk_per_trade)


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
    trade_no: float, app_config: AppConfig, no_of_cpu=4, with_trades=False, ignore=False
) -> RiskType:
    app_config.risk_per_trade = trade_no
    app_config.raw = True

    result = determine_optimum_reward(app_config, no_of_cpu=no_of_cpu, ignore=True)
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


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException()


signal.signal(signal.SIGALRM, timeout_handler)


def group_in_pairs(array, pairs=2):
    return [array[i : i + pairs] for i in range(0, len(array), pairs)]


def single_worker_on_array(
    app_config: AppConfig, risk_rewards: typing.List[float], no_of_cpu=4, ignore=False
):
    return [
        size_resolver(x, app_config, no_of_cpu=no_of_cpu, ignore=ignore)
        for x in risk_rewards
    ]


def spawn_workers_on_array(
    app_config: AppConfig, risk_rewards: typing.List[float], no_of_cpu=4, ignore=False
):
    pairs = math.ceil(len(risk_rewards) / no_of_cpu)
    arrayPairs = group_in_pairs(risk_rewards, pairs)
    result = run_in_parallel(
        single_worker_on_array,
        [(app_config, x, no_of_cpu, ignore) for x in arrayPairs],
        no_of_cpu=no_of_cpu,
        ignore=ignore,
    )
    result = [item for sublist in result for item in sublist]
    return result


def get_highest_value(arr: typing.List[typing.Any]):
    return max(arr, key=lambda x: x["size"])


def create_array(start, end, gap):
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += gap
    return result


def batch_resolver_generator(
    app_config: AppConfig,
    max_size: float,
    gap=1,
    batchSize=10,
    no_of_cpu=4,
    ignore=False,
):
    first_value = app_config.risk_per_trade
    start = 0
    while True:
        first_batch = create_array(first_value, first_value + (batchSize * gap), gap)
        result = spawn_workers_on_array(
            app_config, first_batch, no_of_cpu=no_of_cpu, ignore=ignore
        )
        all_less_than_max = all([x["size"] <= max_size for x in result])
        if all_less_than_max:
            yield get_highest_value(result)
            first_value = first_value + batchSize * gap
            start += 1
        else:
            valid = [x for x in result if x["size"] <= max_size]
            if valid:
                yield get_highest_value(valid)
            if start == 0:
                yield result[0]
            break


def consume_batch_generator(
    app_config: AppConfig,
    max_size: float,
    gap=1,
    batchSize=10,
    no_of_cpu=4,
    ignore=False,
):
    highest = None
    highest_arr = []
    for r in batch_resolver_generator(
        app_config,
        max_size,
        gap=gap,
        batchSize=batchSize,
        no_of_cpu=no_of_cpu,
        ignore=ignore,
    ):
        # highest = r
        highest_arr.append(r)
        print(f'size for {r["value"]} ', r["size"])
    if highest_arr:
        highest = max(highest_arr, key=lambda x: x["size"])
    return highest


def determine_optimum_risk(
    app_config: AppConfig,
    max_size: float,
    gap: float = 1,
    multiplier=10,
    no_of_cpu=4,
    with_trades=False,
    ignore=False,
) -> typing.Optional[RiskType]:
    return consume_batch_generator(
        app_config,
        max_size,
        gap=gap,
        batchSize=multiplier,
        no_of_cpu=no_of_cpu,
        ignore=ignore,
    )
    start_index = 0
    # highest = {
    #     "value": app_config.risk_per_trade,
    #     "risk_reward": app_config.risk_reward,
    #     "size": max_size,
    # }
    highest = None
    print("max_size", max_size)
    # first = app_config.risk_per_trade + (gap * start_index)
    # result = size_resolver(first, app_config, no_of_cpu=no_of_cpu)
    # print("result", result)
    results = []
    while True:
        current_risk = app_config.risk_per_trade + (2 ** (gap * start_index))
        try:
            signal.alarm(60)
            result = size_resolver(
                current_risk,
                app_config,
                no_of_cpu=no_of_cpu,
                with_trades=with_trades,
                ignore=ignore,
            )
        except Exception as e:
            print(
                "payload",
                {
                    "current_risk": current_risk,
                    "app_config": app_config,
                    "no_of_cpu": no_of_cpu,
                    "with_trades": with_trades,
                    "ignore": ignore,
                },
            )
            print("error", e)
            signal.alarm(0)
            result = {"size": 0, "value": current_risk, "risk_reward": 0, "trades": []}
            raise e
        size = to_f(result["size"], app_config.decimal_places)
        if size <= max_size:
            print(f"size for risk {current_risk}", size)
            results.append(result)
            # update = result
            # previous = highest.get("value", 0) if highest else current_risk
            # if highest and previous == highest["value"]:
            #     update = highest
            # highest = {
            #     **update,
            #     "risk_reward": result["risk_reward"],
            #     "size": size,
            #     "value": max(previous, current_risk),
            # }
            # yield result
            start_index += 1
        else:
            # print(f"size for risk {current_risk}", size)
            # update = result
            # previous = highest.get("value", 0) if highest else current_risk
            # if highest and previous == highest["value"]:
            #     update = highest
            # highest = {
            #     **update,
            #     "risk_reward": result["risk_reward"],
            #     "size": size,
            #     "value": max(previous, current_risk),
            # }
            break
    if results:
        return max(results, key=lambda x: x["size"])
    return result
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
