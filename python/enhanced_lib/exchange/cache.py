from dataclasses import dataclass
from ..calculations.workers.utils import run_in_threads

from ..calculations.future_config import (
    Config,
    FutureInstance,
    to_f,
    shared,
    determine_pnl,
)
from .account import Account
from .types import ExchangeInfo, OrderControl, Position, PositionKlass


@dataclass
class ExchangeCache:
    account: Account
    symbol: str

    def __post_init__(self):
        self.exchange_info: ExchangeInfo = self.get_exchange_information()[
            self.symbol.upper()
        ]["payload"]["future"][self.symbol.lower()]
        self.config = self.get_future_config()

    @property
    def future_instance(self):
        return FutureInstance(self.get_future_config())

    def get_future_config(self):
        config = self.account.general_config.get("config") or {}
        if not config:
            config[self.symbol.upper()] = {}
        value = config[self.symbol.upper()]
        instance = Config(**value)
        if value.get("min_size"):
            instance.minimum_size = value.get("min_size")
        instance.use_fibonacci = True
        instance.use_default = False
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
            result[self.symbol.upper()]["payload"]["future"] = {
                self.symbol.lower(): {},
            }
        future = payload["future"]
        if not future:
            result[self.symbol.upper()]["payload"]["future"][self.symbol.lower()] = {}

        return result

    async def save(self, save=True):
        await self.account.fetch_latest(self.symbol, save=save)

    async def fetch_latest(self, save=True):
        await self.account.fetch_latest(self.symbol, save=save)
        self.exchange_info: ExchangeInfo = self.get_exchange_information()[
            self.symbol.upper()
        ]["payload"]["future"][self.symbol.lower()]

    @property
    def open_orders(self):
        return OrderControl(self.exchange_info["open_orders"], positions=self.position)

    @property
    def position(self):
        return Position(
            self.exchange_info["position"], self.exchange_info["closed_orders"]
        )

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

    def get_zone_for_position(self, kind: Position):
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

    def get_next_tradable_zone(self, kind: Position):
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
                long_zones = self.get_next_tradable_zone("long")
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
        self, kind: Position, with_trades=False, no_of_cpu=6,gap=None
    ):
        zones = self.get_next_tradable_zone(kind)
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
            )
            return {
                **o,
                "risk_reward": y["risk_reward"],
                "risk_per_trade": y["value"],
                "trades": y.get("trades", []),
            }

        result = run_in_threads(func, [(x,) for x in zones], num_threads=no_of_cpu)

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
