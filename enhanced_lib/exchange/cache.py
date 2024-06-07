from dataclasses import dataclass
import typing
from ..calculations.workers.utils import chunks_in_threads, run_in_threads
from ..calculations.workers import determine_optimum_reward

from ..calculations.future_config import (
    Config,
    FutureInstance,
    to_f,
    shared,
    determine_pnl,
)
from .account import Account
from .types import ExchangeInfo, OrderControl, Position, PositionKlass, PositionKind


@dataclass
class ExchangeCache:
    account: Account
    symbol: str

    def __post_init__(self):
        self.exchange_info: ExchangeInfo = self.get_exchange_information()[
            self.symbol.upper()
        ]["payload"]["future"][self.symbol.lower()]
        self.config = self.get_future_config()
        self.margin_info = None

    @property
    def future_instance(self):
        return FutureInstance(self.get_future_config())

    def get_future_config(self, additional=None):
        # additional is to be used when you want to update the config
        config = self.account.general_config.get("config") or {}
        if not config:
            config[self.symbol.upper()] = {}
        value = config[self.symbol.upper()]
        if additional:
            value.update(additional)
        instance = Config(**value)
        if value.get("min_size"):
            instance.minimum_size = value.get("min_size")
        instance.use_fibonacci = True
        instance.use_default = False
        return instance

    def build_custom_config(self, payload, kind):
        config = self.account.general_config.get("config") or {}
        if not config:
            config[self.symbol.upper()] = {}
        value = config[self.symbol.upper()]
        value["entry"] = payload["entry"]
        value["stop"] = payload["stop"]
        value["kind"] = kind
        if payload.get('risk_reward'):
            value["risk_reward"] = payload["risk_reward"]
        if payload.get("risk_per_trade"):
            value["risk_per_trade"] = payload["risk_per_trade"]
        if payload.get("min_size"):
            value["min_size"] = payload.get("min_size")
        if payload.get("minimum_size"):
            value["minimum_size"] = payload.get("minimum_size")
        instance = Config(**value)

        return instance

    def get_exchange_information(self):
        result = self.account.general_config.get("position_information") or {}
        if not result:
            result[self.symbol.upper()] = {
                "payload": {
                    "future": {
                        self.symbol.lower(): {},
                    }
                }
            }
        instance = result[self.symbol.upper()]
        if not instance:
            result[self.symbol.upper()]["payload"] = {
                "future": {
                    self.symbol.lower(): {},
                }
            }
        payload = instance["payload"]
        if not payload:
            value = {
                self.symbol.upper(): {
                    "payload": {
                        "future": {
                            self.symbol.lower(): {},
                        }
                    }
                }
            }
            if (
                self.symbol.upper() not in result
                or "payload" not in result[self.symbol.upper()]
                or not result[self.symbol.upper()]["payload"]
            ):
                result.update(value)
            else:
                result[self.symbol.upper()]["payload"]["future"] = {
                    self.symbol.lower(): {},
                }
            payload = {"future": {self.symbol.lower(): {}}} if not payload else payload
        future = payload["future"]
        if not future:
            result[self.symbol.upper()]["payload"]["future"][self.symbol.lower()] = {}

        return result

    async def save(self, save=True):
        await self.account.fetch_latest(self.symbol, save=save)

    async def fetch_latest(self, save=True, margin=False):
        await self.account.fetch_latest(self.symbol, save=save, margin=margin)
        self.exchange_info: ExchangeInfo = self.get_exchange_information()[
            self.symbol.upper()
        ]["payload"]["future"][self.symbol.lower()]
        if margin:
            self.margin_info = self.get_exchange_information()[self.symbol.upper()][
                "payload"
            ]["margin"][self.symbol.lower()]

    @property
    def open_orders(self):
        return OrderControl(self.exchange_info["open_orders"], positions=self.position)

    @property
    def margin_open_orders(self):
        return OrderControl(self.margin_info["open_orders"], positions=None)

    @property
    def position(self):
        return Position(
            self.exchange_info["position"], self.exchange_info["closed_orders"]
        )

    def expected_pnl(self, kind: PositionKind):
        reverse = "short" if kind == "long" else "long"
        tp = self.open_orders.get_tp_orders(kind, True)
        sl = self.open_orders.get_sl_orders(reverse, True)
        if tp and sl:
            return tp["pnl"] + sl["pnl"]
        return 0

    @property
    def maximum_sell_size(self):
        long_position = self.position.long
        short_position = self.position.short
        if long_position.size == 0:
            return self.future_instance.config.max_size
        return to_f(
            abs(long_position.size - short_position.size),
            self.future_instance.config.decimal_places,
        )

    def get_zone_for_position(self, kind: PositionKind):
        zones = self.future_instance.config.get_trading_zones(kind)
        position: PositionKlass = getattr(self.position, kind)

        def condition(zone: shared.TradingZoneDict):
            if kind == "long":
                return zone["entry"] > position.entry_price
            if position.entry_price == 0:
                return True
            return zone["entry"] < position.entry_price

        active_zones = [x for x in zones if condition(x) and position.size > 0]

        def compute_pnl(zone: shared.TradingZoneDict):
            return determine_pnl(
                position.entry_price,
                zone["entry"],
                position.size,
                kind=kind,
            )

        return [{**x, "pnl": compute_pnl(x)} for x in active_zones]

    def get_next_tradable_zone(self, kind: Position, full=False):
        zones = self.future_instance.config.get_trading_zones(kind)
        closed_order = (
            self.position.closed_long if kind == "long" else self.position.closed_short
        )
        position: PositionKlass = getattr(self.position, kind)

        def condition(zone: shared.TradingZoneDict):
            if kind == "long":
                if position and position.entry_price:
                    return zone["entry"] > position.entry_price
                return zone["entry"] > closed_order.sell_price
            if position and position.entry_price:
                return zone["entry"] < position.entry_price
            return zone["entry"] < closed_order.sell_price

        active_zones = [x for x in zones if closed_order and condition(x)]
        if full:
            active_zones = zones

        def compute_new_stop(zone: shared.TradingZoneDict):
            liquidation_zone = None
            max_sell_size = self.future_instance.config.max_size
            if kind == "long":
                liquidation_zone = (
                    self.future_instance.config.determine_long_liquidation(
                        zone["entry"]
                    )
                )
            else:
                max_sell_size = self.maximum_sell_size
                # interested in where the long zone would take profit
                long_zones = self.get_next_tradable_zone("long", full)
                if long_zones:
                    liquidation_zone = long_zones[-1]["entry"]
            if liquidation_zone and max_sell_size:
                return {
                    "stop": to_f(
                        liquidation_zone, self.future_instance.config.price_places
                    ),
                    "size": to_f(
                        max_sell_size, self.future_instance.config.decimal_places
                    ),
                }
            return {}

        return [{**x, **y} for x in active_zones if (y := compute_new_stop(x))]

    def config_params_for_future_trades(
        self,
        kind: Position,
        with_trades=False,
        no_of_cpu=6,
        gap=None,
        full=False,
        ignore=False,
    ):
        zones = self.get_next_tradable_zone(kind, full=full)
        config = self.future_instance.config

        def get_gap(x: shared.TradingZoneDict):
            if gap:
                return gap
            if x.get("size") < 0.15:
                return 0.1
            return 1

        def func(o):
            y = config.determine_optimum_risk(
                kind,
                o,
                max_size=o["size"],
                gap=get_gap(o),
                with_trades=with_trades,
                no_of_cpu=no_of_cpu,
                ignore=ignore,
            )
            return {
                **o,
                "risk_reward": y["risk_reward"],
                "risk_per_trade": y["value"],
                "trades": y.get("trades", []),
            }

        result = run_in_threads(
            func, [(x,) for x in zones], num_threads=no_of_cpu, ignore=ignore
        )

        return result

    def config_params_for_future_trades2(
        self, kind: Position, with_trades=False, no_of_cpu=6
    ):
        zones = self.get_next_tradable_zone(kind)
        config = self.future_instance.config

        def get_gap(x: shared.TradingZoneDict):
            if x.get("size") < 0.15:
                return 0.1
            return 1

        def func(o):
            y = config.determine_optimum_risk(
                kind,
                o,
                max_size=o["size"],
                gap=get_gap(o),
                with_trades=with_trades,
                no_of_cpu=no_of_cpu,
            )
            return {
                **o,
                "risk_reward": y["risk_reward"],
                "risk_per_trade": y["value"],
                "trades": y.get("trades", []),
            }

        klass = ProcessedParams()

        def non_blocking():
            import time

            while True:
                if len(klass.trades) == len(zones):
                    break
                print("waiting for all trades to be processed", klass.trades)
                time.sleep(2)

        klass.process(func, [(x,) for x in zones], non_blocking=non_blocking)
        # result = run_in_threads(func, [(x,) for x in zones], num_threads=no_of_cpu)

        # return result

    def get_calculations_for_kind(
        self, no_of_cpu=6, strategy="entry", kind="long", daemon=False
    ):
        zones = [
            {"entry": x["entry"], "stop": x["stop"]}
            for x in self.future_instance.trade_entries
        ]
        config = self.future_instance.config
        # use entry strategy because quantity causes errors
        config.strategy = "quantity" if self.config.max_size > 0.2 else "entry"
        # config.strategy = strategy
        # results = run_in_threads(
        #     lambda x: config.determine_optimum_risk(
        #         kind,  # doesn't work well with short
        #         x,
        #         max_size=self.config.max_size,
        #         gap=self.config.gap,
        #         no_of_cpu=no_of_cpu,
        #     ),
        #     [(x,) for x in zones],
        #     num_threads=len(zones),
        # )
        results = map(
            lambda x: config.determine_optimum_risk(
                kind,  # doesn't work well with short
                x,
                max_size=self.config.max_size,
                gap=self.config.gap,
                no_of_cpu=no_of_cpu,
                ignore=daemon,
            ),
            zones,
        )
        return [
            {
                "entry": to_f(x["entry"], config.price_places),
                "stop": to_f(x["stop"], config.price_places),
                "risk_per_trade": to_f(x["value"], config.decimal_places),
                "risk_reward": x["risk_reward"],
                "size": x["size"],
            }
            for x in [
                {
                    **x[0],
                    **x[1],
                }
                for x in zip(zones, results)
            ]
        ]

    async def save_trades(self, trades):
        result = await self.account.save_trades(
            self.symbol, {"long": [{**x, "trades": []} for x in trades], "short": []}
        )

    async def get_trades(self):
        return await self.account.get_trades(self.symbol)

    def build_trade_zones(self, trades={}, kind="long", fee_percent=0.06):
        fee_value = self.account.general_config["config"][self.symbol].get(
            "fee_percent", fee_percent
        )
        long_trades = trades.get("long", [])
        short_trades = trades.get("short", [])
        intermediate = []
        position = self.position.long if kind == "long" else self.position.short
        minimum = position.determine_minimum_pnl(fee_value)
        print("minimum", minimum, "fee_value", fee_value)
        # if long_trades and not short_trades:
        #     intermediate = [
        #         {**x, "entry": x["stop"], "stop": x["entry"]} for x in long_trades
        #     ]
        # if short_trades and not long_trades:
        #     intermediate = [
        #         {**x, "entry": x["stop"], "stop": x["entry"]} for x in short_trades
        #     ]
        # if intermediate:
        #     if not long_trades:
        #         long_trades = intermediate
        #     if not short_trades:
        #         short_trades = intermediate

        # t = long_trades if kind == "long" else short_trades

        # def condition(x):
        #     if position.kind == "long":
        #         return x["entry"] >= position.entry_price
        #     return x["entry"] <= position.entry_price

        # result = [
        #     {
        #         **x,
        #         # "trades": build_trades(self, x, kind),
        #         "trades": [y["entry"] for y in build_trades(self, x, kind)],
        #     }
        #     for x in t
        #     if condition(x)
        # ]
        # # combined_trades = result
        # combined_trades = [z for y in [x["trades"] for x in result] for z in y]
        # combined_trades = [
        #     {"price": x, "pnl": position.determine_pnl(x)} for x in combined_trades
        # ]
        # combined_trades = [x for x in combined_trades if x["pnl"] >= minimum]
        # if combined_trades:
        #     return min(combined_trades, key=lambda x: x["pnl"])
        close_price = position.determine_close_price(minimum)
        return {"price": close_price, "pnl": minimum}

    async def update_support_resistance(self, support=None, resistance=None):
        """New function to update support and resistance"""
        payload = {}
        if support:
            payload["support"] = support
        if resistance:
            payload["resistance"] = resistance
        await self.account.update_config_fields(self.symbol, payload)


def build_trades(
    klass: ExchangeCache,
    payload,
    kind,
    strategy: typing.Literal["entry", "quantity"] = "entry",
    default=True,
):
    config = klass.build_custom_config(payload, kind)
    config.strategy = strategy
    result = config.build_trades()
    return result["result"]


def get_risk_reward(client: ExchangeCache, payload, kind, strategy="entry"):
    config = client.build_custom_config(payload, kind)
    config.strategy = strategy
    app_config = config.app_config
    app_config.raw = True
    result = determine_optimum_reward(app_config)
    return result.get("value"), result.get("result"), result.get("size")


def compute_risk_rewards(
    client: ExchangeCache,
    payload: dict,
    kind: str,
    max_size: float,
    start_risk,
    gap=5,
    strategy="quantity",
    opposite=False,
):
    risk_reward = payload.get("risk_reward") or 199
    risk_reward, trades, current_max_size = get_risk_reward(
        client,
        {**payload, "risk_per_trade": start_risk, "risk_reward": risk_reward},
        kind,
        strategy=strategy,
    )
    new_risk = start_risk - gap
    counter = 0
    if opposite:
        new_risk = start_risk + 5
        if current_max_size < max_size:
            while current_max_size < max_size and new_risk > 0:
                print(
                    "current max size",
                    current_max_size,
                    "new_risk",
                    new_risk,
                    "risk_reward",
                    risk_reward,
                )
                try:
                    risk_reward, trades, current_max_size = get_risk_reward(
                        client,
                        {**payload, "risk_per_trade": new_risk, "risk_reward": 1},
                        kind,
                        strategy=strategy,
                    )
                    if not risk_reward:
                        break
                    if not current_max_size:
                        break
                except Exception as e:
                    print(e)
                new_risk += 5
                counter += 1

            return {
                "risk_reward": risk_reward,
                "risk_per_trade": new_risk,
                "counter": counter,
                "max_size": current_max_size,
                "trades": trades,
            }

    new_risk = start_risk - gap
    if current_max_size:
        if current_max_size > (max_size * 2):
            new_risk = start_risk / 2
        while current_max_size > max_size and new_risk > 0:
            print(
                "current max size",
                current_max_size,
                "new_risk",
                new_risk,
                "risk_reward",
                risk_reward,
            )
            try:
                risk_reward, trades, current_max_size = get_risk_reward(
                    client,
                    {**payload, "risk_per_trade": new_risk, "risk_reward": 1},
                    kind,
                    strategy=strategy,
                )
                if not risk_reward:
                    break
                if not current_max_size:
                    break
            except Exception as e:
                print(e)
            new_risk -= gap
            if current_max_size > (max_size * 2):
                new_risk = new_risk / 2
            counter += 1
    else:
        risk_reward = 25
        new_risk = 40

    return {
        "risk_reward": risk_reward,
        "risk_per_trade": new_risk,
        "counter": counter,
        "max_size": current_max_size,
        "trades": trades,
    }


class ProcessedParams:
    def __init__(self) -> None:
        self.trades = []

    def callback(self, future):
        try:
            result = future.result()
            print("processing result for ", result["entry"])
            if result:
                self.trades.append(result)
        except Exception:
            print(f"Callback: Task raised an exception: {exec}")

    def process(self, func, zones, non_blocking):
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(func, *value) for value in zones]

            # Add a callback function to each future
            for future in futures:
                future.add_done_callback(self.callback)
            if non_blocking:
                non_blocking()

        print(
            "All tasks submitted. The program will exit once all callbacks are executed."
        )


def compute_possible_entries(
    client: ExchangeCache,
    payload,
    profit: float,
    kind="short",
    _max_size=0.15,
    switch_to_entry=5,
    minimum_loss=0.5,
    raw=False,
    with_trades=False,
    spread=5,
):
    result = []
    max_size = _max_size
    remaining_profit = profit
    buy_price = min(payload["entry"], payload["stop"])
    stop_price = max(payload["entry"], payload["stop"])
    if kind == "long":
        stop_price = min(payload["entry"], payload["stop"])
        buy_price = max(payload["entry"], payload["stop"])
    strategy = "quantity"
    opposite = False
    risk_reward = None
    loss_diff = 10
    while remaining_profit > 1:
        previous_buy_price = buy_price
        previous_stop_price = stop_price
        pp = compute_risk_rewards(
            client,
            {
                "entry": buy_price,
                "stop": stop_price,
                "risk_per_trade": remaining_profit,
                "risk_reward": risk_reward,
            },
            kind,
            max_size,
            remaining_profit,
            strategy=strategy,
            opposite=opposite,
        )
        # print('pp',pp)
        # rr = build_trades(
        #     client,
        #     {
        #         "entry": buy_price,
        #         "stop": stop_price,
        #         "risk_per_trade": remaining_profit,
        #         "risk_reward": risk_reward,
        #     },
        #     kind=kind,
        #     strategy="quantity",
        # )
        rr = pp["trades"]
        risk_reward = pp["risk_reward"]
        max_size = pp["max_size"]
        if not rr:
            break
        buy_price = rr[-1]["entry"]
        stop_price = rr[0]["entry"]
        loss = abs(rr[0]["neg.pnl"])
        if not loss and kind == "short":
            break
        if loss_diff < minimum_loss:
            break
        if loss < switch_to_entry:
            opposite = True

        if loss > remaining_profit:
            break
        item_to_add = {
            "entry": buy_price,
            "stop": stop_price,
            "risk_per_trade": remaining_profit,
            "loss": loss,
            "pnl": rr[0]["pnl"],
            "%": to_f(rr[0]["pnl"] / loss, "%.2f"),
            "no_of_trades": len(rr),
            "risk_reward_v": risk_reward,
            "max_size": max_size,
        }
        if with_trades:
            item_to_add["trades"] = rr
        result.append(item_to_add)
        # if abs(loss) <= switch_to_entry:
        #     strategy = "entry"
        if kind == "short":
            stop_price = buy_price
            buy_price = min(payload["entry"], payload["stop"])
        else:
            stop_price = buy_price
            buy_price = max(payload["entry"], payload["stop"])
            # buy_price = stop_price
        if abs(buy_price - stop_price) < spread:
            result.pop()
            break
        if kind == "long" and loss < 1:
            strategy = "entry"
            buy_price = previous_buy_price
            stop_price = previous_stop_price
            result.pop()
            # stop_price = self.buy_price
        remaining_profit -= loss
        loss_diff = abs(loss)
        print("remaining_profit", remaining_profit)
        print({"entry": buy_price, "stop": stop_price})
    print("remaining_profit", remaining_profit)
    return parse_trades(client,result, kind)


def parse_trades(client:ExchangeCache,results, kind):
    first_entry = results[0]
    remaining = results[1:]
    solutions = [first_entry]
    if remaining:
        if kind == "long":
            entry = max([x["entry"] for x in remaining])
            stop = min([x["stop"] for x in remaining])
        else:
            entry = min([x["entry"] for x in remaining])
            stop = max([x["stop"] for x in remaining])
        risk = sum([x["loss"] for x in remaining])
        payload = {
            **remaining[0],
            "entry": entry,
            "stop": stop,
            "risk_per_trade": risk,
            "loss": risk,
            "trades": [],
            'risk_reward': 100,
        }
        risk_reward,tt,max_size = get_risk_reward(client,payload,kind,'entry')
        payload['risk_reward_v'] = risk_reward
        payload['no_of_trades'] = len(tt)
        payload['max_size'] = max_size
        solutions.append(payload)

    return solutions
