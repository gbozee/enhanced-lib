from dataclasses import dataclass
from typing import Optional, List, Any, TypedDict, Literal
from .trade_signal import Signal, to_f, determine_pnl, determine_expected_loss
from . import shared, workers
from .position_control import PositionControl
import multiprocessing


class TradeItem(TypedDict):
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
    avg_entry: float
    avg_size: float
    start_entry: float


class TradeRow(TypedDict):
    trade: List[TradeItem]
    support: Optional[float]
    resistance: Optional[float]


@dataclass
class TradeBuilder:
    entries: List[TradeRow]
    spread_factor = 1.00001
    price_places: Optional[str] = "%.1f"
    decimal_places: Optional[str] = "%.3f"
    opposite_trade: Optional["TradeBuilder"] = None
    fee_cost: Optional[float] = 0.0006

    @property
    def pnl(self):
        if self.take_profit:
            return to_f(self.take_profit["pnl"], "%.2f")

    @property
    def kind(self):
        entry = self.entries[0]["trade"][0]["entry"]
        stop = self.entries[0]["trade"][0]["stop"]
        if entry > stop:
            return "long"
        return "short"

    @property
    def spread(self):
        return self.get_spread(self.kind)

    def get_spread(self, kind):
        if kind == "short":
            return self.spread_factor
        return 1 / self.spread_factor

    @property
    def stop_order(self):
        first_entry = self.entries[0]["trade"][0]
        return {
            "price": first_entry["avg_entry"],
            "quantity": first_entry["avg_size"],
            "kind": self.kind,
            "side": "buy" if self.kind == "long" else "sell",
            "stop": to_f(first_entry["avg_entry"] * self.spread, self.price_places),
        }

    @property
    def flat_entries(self):
        return [x for y in self.entries for x in y["trade"]]

    @property
    def orders(self):
        orders = []
        for j in self.flat_entries:
            orders.append(
                {
                    "price": j["entry"],
                    "quantity": j["quantity"],
                    "kind": self.kind,
                    "side": "buy" if self.kind == "long" else "sell",
                }
            )
        return orders

    @property
    def take_profit(self):
        price = None
        if self.kind == "long":
            if self.entries[0].get("resistance"):
                price = self.entries[0]["resistance"]
        else:
            if self.entries[0].get("support"):
                price = self.entries[0]["support"]
        if price:
            return {
                "price": price,
                "close": True,
                "kind": self.kind,
                "pnl": determine_pnl(
                    self.stop_order["price"],
                    price,
                    self.stop_order["quantity"],
                    kind=self.kind,
                ),
            }

    def build_opposite_trade(self, entries):
        result = self.without_opposite_stop_loss
        price = result["price"]
        order = [x for x in self.flat_entries if x["entry"] >= price]
        stop_loss = None
        if order:
            _entry = min(order, key=lambda x: x["entry"])
            # get the closest trade_entry
            found = [
                x
                for x in entries
                if _entry["avg_entry"] > x > self.take_profit["price"]
            ]
            if found:
                stop_price = max(found)
                stop_loss = determine_expected_loss(
                    {
                        "close_price": stop_price,
                        "quantity": _entry["avg_size"],
                        "pnl": determine_pnl(
                            _entry["avg_entry"],
                            stop_price,
                            _entry["avg_size"],
                            kind=self.kind,
                        ),
                    },
                    {"quantity": result["quantity"], "price": result["price"]},
                    base_fee=self.fee_cost,
                    kind=result["kind"],
                    decimal_places=self.decimal_places,
                    spread_factor=self.spread_factor,
                    price_places=self.price_places,
                )
        return {
            result["kind"]: {
                "orders": [],
                "stop_order": {
                    "price": result["price"],
                    "quantity": result["quantity"],
                    "kind": result["kind"],
                    "side": result["side"],
                    "stop": result["stop"],
                },
                "take_profit": {
                    "price": result["close_price"],
                    "close": True,
                    "kind": result["kind"],
                    "pnl": result["pnl"],
                },
                "pnl": result["pnl"],
                "stop_loss": stop_loss,  # figure out how long to reduce the quantity for the opposite trade
            }
        }

    @property
    def without_opposite_stop_loss(self):
        opposite_entry = self.stop_order
        kind = "long" if self.kind == "short" else "short"
        opposite_entry["kind"] = kind
        opposite_entry["side"] = "buy" if kind == "long" else "sell"
        opposite_entry["stop"] = to_f(
            opposite_entry["price"] * self.get_spread(kind), self.price_places
        )
        opposite_entry["close_price"] = self.orders[0]["price"]
        opposite_entry["pnl"] = to_f(
            determine_pnl(
                opposite_entry["price"],
                opposite_entry["close_price"],
                opposite_entry["quantity"],
                kind=kind,
            ),
            "%.2f",
        )
        return opposite_entry

    @property
    def stop_loss(self):
        """
        Start with naive implementation and only use opposite trade if it exists
        """
        close_price = self.without_opposite_stop_loss["close_price"]
        trade_quantity = self.without_opposite_stop_loss["quantity"]
        pnl = self.without_opposite_stop_loss["pnl"]
        if self.opposite_trade:
            if self.opposite_trade.pnl:
                close_price = self.opposite_trade.take_profit["price"]
                trade_quantity = self.opposite_trade.stop_order["quantity"]
                pnl = self.opposite_trade.pnl
        loss_value = determine_expected_loss(
            {
                "close_price": close_price,
                "quantity": trade_quantity,
                "pnl": pnl,
            },
            {
                "quantity": self.stop_order["quantity"],
                "price": self.stop_order["price"],
            },
            base_fee=self.fee_cost,
            kind=self.kind,
            decimal_places=self.decimal_places,
            price_places=self.price_places,
            spread_factor=self.spread_factor,
        )
        return loss_value


@dataclass
class Config:
    fee: Optional[float] = 0.06
    risk_per_trade: Optional[float] = 4
    risk_reward: Optional[int] = 4
    focus: Optional[float] = 29200
    budget: Optional[float] = 60
    support: Optional[float] = 24581.1
    resistance: Optional[float] = 28456.3
    price_places: Optional[str] = ".1f"
    decimal_places: Optional[str] = ".3f"
    percent_change: Optional[float] = 0.08
    tradeSplit: Optional[int] = 24
    take_profit: Optional[float] = None
    stop: Optional[float] = None
    entry: Optional[float] = None
    increase_position: Optional[bool] = True
    use_default: Optional[bool] = True
    kind: Optional[str] = "long"
    main_split: Optional[int] = 5
    sub_split: Optional[int] = 3
    use_fibonacci: Optional[bool] = False
    use_multiplier: Optional[bool] = False
    # irrelevant fields
    symbol: Optional[str] = "BTCUSDT"
    id: Optional[str] = None
    not_bull: Optional[bool] = False
    is_bear: Optional[bool] = False
    not_bear: Optional[bool] = False
    buy_more: Optional[bool] = False
    profit_quote_price: Optional[float] = None
    profit_base_price: Optional[float] = None
    margin_sub_account: Optional[str] = None
    sub_accounts: Optional[List[Any]] = None
    is_margin: Optional[bool] = False
    expected_loss: Optional[float] = None
    spread: Optional[float] = None
    follow_profit: Optional[bool] = False
    futureBudget: Optional[float] = None
    x_places: Optional[str] = None
    budget: Optional[float] = None
    follow_stop: Optional[bool] = False
    entry_price: Optional[float] = None
    dollar_price: Optional[float] = None
    bull_factor: Optional[float] = None
    bear_factor: Optional[float] = None
    loss_factor: Optional[int] = None
    min_size: Optional[float] = None
    transfer_funds: Optional[bool] = False
    max_size: Optional[float] = None
    zone_risk: Optional[int] = None
    zone_split: Optional[int] = None
    minimum_size: Optional[float] = None
    strategy: Optional[Literal["quantity", "entry"]] = "quantity"

    def as_dict(self):
        fields = shared.AppConfig.get_all_fields()

        def __fetch(key):
            if hasattr(self, key):
                return getattr(self, key)
            return None

        return {x: __fetch(x) for x in fields}

    @property
    def app_config(self):
        return shared.AppConfig(**self.as_dict())

    @property
    def long_liquidation_price(self):
        if self.resistance and self.max_size:
            control = PositionControl(
                avg_entry=self.resistance, avg_size=self.max_size, kind="long"
            )
            return control.determine_liquidation(self.budget, self.symbol)

    def determine_long_liquidation(self, price: float):
        if self.max_size:
            control = PositionControl(
                avg_entry=price, avg_size=self.max_size, kind="long"
            )
            return control.determine_liquidation(self.budget, self.symbol)

    def determine_short_liquidation(self, price: float, size: float):
        control = PositionControl(avg_entry=price, avg_size=size, kind="short")
        return control.determine_liquidation(self.budget, self.symbol)

    def determine_optimum_risk(
        self,
        kind: Literal["long", "short"],
        zone: shared.TradingZoneDict,
        gap=1,
        no_of_cpu=4,
        max_size=None,
        with_trades=False,
    ):
        size = max_size or self.max_size
        self.kind = kind
        app_config = self.app_config
        app_config.entry = zone["entry"]
        app_config.stop = zone["stop"]
        return workers.determine_optimum_risk(
            app_config, size, gap=gap, no_of_cpu=no_of_cpu,with_trades=with_trades
        )

    def get_trading_zones(self, kind: Literal["long", "short"]):
        """This is the main function that will be used to determine the trading zone based
        off the config support and resistance. It uses a list of zones calculated using the
        fibonacci_analysis function.

        Args:
            kind (str): 'long' or 'short'

        """
        app_config = self.app_config
        return app_config.get_trading_zones(
            {"kind": kind, "use_fibonacci": self.use_fibonacci}
        )


@dataclass
class FutureInstance:
    config: Config

    def build_config(
        self,
        take_profit=None,
        entry=None,
        stop=None,
        risk_reward=None,
        raw_instance=False,
        risk=None,
        no_of_trades=None,
        increase=False,
        kind="long",
        support=None,
        resistance=None,
    ):
        return shared.build_config(
            self.config,
            {
                "take_profit": take_profit,
                "entry": entry,
                "risk": risk,
                "stop": stop,
                "risk_reward": risk_reward,
                "raw_instance": raw_instance,
                "no_of_trades": no_of_trades,
                "increase": increase,
                "price_places": self.config.price_places,
                "decimal_places": self.config.decimal_places,
                "kind": kind,
                "support": support,
                "resistance": resistance,
            },
        )

    def build_full_orders(
        self,
        entry=None,
        kind="long",
        take_profit=None,
        raw_instance=False,
        new_stop=None,
        risk_reward=None,
        risk=None,
        increase=False,
        support=None,
        resistance=None,
    ):
        stop = new_stop or self.config.stop
        if not raw_instance:
            condition = entry and stop
            if not condition:
                return []
        result = self.build_config(
            entry=entry,
            stop=stop,
            risk_reward=risk_reward,
            raw_instance=raw_instance,
            kind=kind,
            risk=risk,
            take_profit=take_profit,
            increase=increase,
            support=support,
            resistance=resistance,
        )
        return result

    @property
    def full_orders(self):
        entry = self.config.entry
        risk_reward = None
        if self.config.use_default:
            first_pass = self.build_full_orders(
                entry=entry,
                kind=self.config.kind,
                increase=self.config.increase_position,
            )
            if first_pass:
                entry = first_pass[-1]["entry"]
                risk_reward = len(first_pass)
        result = self.build_full_orders(
            entry=entry,
            kind=self.config.kind,
            risk_reward=risk_reward,
            increase=self.config.increase_position,
        )
        return result

    @property
    def raw_instance(self):
        return self.build_full_orders(raw_instance=True)

    def determine_optimum_risk_reward(
        self,
    ):
        config = shared.AppConfig(
            fee=self.config.fee,
            risk_per_trade=self.config.risk_per_trade,
            risk_reward=self.config.risk_reward,
            focus=self.config.focus,
            budget=self.config.budget,
            support=self.config.support,
            resistance=self.config.resistance,
            percent_change=self.config.percent_change,
            tradeSplit=self.config.tradeSplit,
            take_profit=self.config.take_profit,
            kind=self.config.kind,
            entry=self.config.entry,
            stop=self.config.stop,
            min_size=self.config.min_size,
            minimum_size=self.config.minimum_size,
            price_places=self.config.price_places,
            strategy="quantity",
            as_array=False,
            decimal_places=self.config.decimal_places,
        )
        result = workers.determine_optimum_reward(config)
        return {
            "value": result,
        }
        return workers.determine_optimum_reward(config)
        instance: Signal = self.build_full_orders(raw_instance=True)
        return instance.determine_optimum_risk_reward(
            entry=self.config.entry,
            stop_loss=self.config.stop,
            risk=self.config.risk_per_trade,
            kind=self.config.kind,
            single=True,
            support=self.config.support,
        )

    @property
    def trade_entries(self):
        instance: Signal = self.build_full_orders(
            raw_instance=True, entry=self.config.entry
        )
        # return self.build_trade_entries()
        return instance.build_trade_entries(
            risk=self.config.risk_per_trade,
            main_split=self.config.main_split,
            sub_split=self.config.sub_split,
            kind=self.config.kind,
            use_fibonacci=self.config.use_fibonacci,
        )

    def determine_trades(self, support: float, resistance: float, kind="long"):
        result = self.calculate_size_and_pnl(
            entry_price=resistance if kind == "long" else support,
            stop_price=support if kind == "long" else resistance,
            kind=kind,
            support=support,
            resistance=resistance,
            increase=True,
            orders=True,
        )
        result["support"] = support
        result["resistance"] = resistance
        return result

    def orders_to_place_v2(
        self,
        kind="long",
        support=None,
        resistance=None,
        custom_entry=None,
        custom_stop=None,
    ):
        result = self.get_trade_entries(
            kind=kind,
            within_zone=False,
            with_result=True,
            support=support,
            resistance=resistance,
            custom_entry=custom_entry,
            custom_stop=custom_stop,
        )
        if not result:
            return {}
        main_trade = TradeBuilder(
            entries=result,
        )
        # new_opposite_trade = TradeBuilder(
        #     entries=opposite_result, opposite_trade=main_trade
        # )
        # currently just shorts are figured out
        opposite = main_trade.build_opposite_trade(
            [min(x["entry"], x["stop"]) for x in self.trade_entries]
        )
        return {
            kind: {
                "orders": main_trade.orders,
                "stop_order": main_trade.stop_order,
                "take_profit": main_trade.take_profit,
                "pnl": main_trade.pnl,
                "stop_loss": main_trade.stop_loss,
                "diff": main_trade.stop_order["quantity"]
                - main_trade.stop_loss["quantity"],
            },
            **opposite,
        }

    def orders_to_place(
        self,
        kind="long",
        support=None,
        resistance=None,
        custom_entry=None,
        custom_stop=None,
    ):
        result = self.get_trade_entries(
            kind=kind,
            within_zone=False,
            with_result=True,
            support=support,
            resistance=resistance,
            custom_entry=custom_entry,
            custom_stop=custom_stop,
        )
        if not result:
            return {}
        result_support = result[0]["support"]
        result_resistance = result[0]["resistance"]
        opposite_entry = result_support - 1 if kind == "long" else result_resistance + 1
        opposite_kind = "short" if kind == "long" else "long"
        opposite_result = self.get_trade_entries(
            opposite_entry,
            kind=opposite_kind,
            within_zone=False,
            with_result=True,
            support=support,
            resistance=resistance,
        )
        # build out the orders
        opposite_trade = TradeBuilder(entries=opposite_result)
        main_trade = TradeBuilder(entries=result, opposite_trade=opposite_trade)
        new_opposite_trade = TradeBuilder(
            entries=opposite_result, opposite_trade=main_trade
        )
        return {
            kind: {
                "orders": main_trade.orders,
                "stop_order": main_trade.stop_order,
                "take_profit": main_trade.take_profit,
                "pnl": main_trade.pnl,
                "stop_loss": main_trade.stop_loss,
                "diff": main_trade.stop_order["quantity"]
                - main_trade.stop_loss["quantity"],
            },
            opposite_kind: {
                "orders": new_opposite_trade.orders,
                "stop_order": new_opposite_trade.stop_order,
                "take_profit": new_opposite_trade.take_profit,
                "pnl": new_opposite_trade.pnl,
                "stop_loss": new_opposite_trade.stop_loss,
                "diff": new_opposite_trade.stop_order["quantity"],
            },
        }

    def get_sub_trade_entries(
        self,
        support=None,
        resistance=None,
    ):
        old_support = self.config.support
        old_resistance = self.config.resistance
        if support and resistance:
            self.config.support = support
            self.config.resistance = resistance

        results = []
        for i in self.trade_entries:
            for q in i["extended_zones"]:
                # convert to use rust code. very slow.
                result = calculate_size_and_pnl(
                    self,
                    i["extended_zones"],
                    q,
                    _inner_kind="short",
                    multiplier=q["multiplier"],
                    # _support=self.config.support,
                    # _resistance=self.config.resistance,
                )
                if result and result[0]:
                    if result[0].get("trade") and result[0].get("trade")[0]:
                        results.append(result)
        if support and resistance:
            self.config.support = old_support
            self.config.resistance = old_resistance
        return [x for y in results for x in y]

    def get_trade_entries(
        self,
        entry: float = None,
        kind="long",
        within_zone=True,
        with_result=False,
        support=None,
        resistance=None,
        custom_entry: float = None,
        custom_stop: float = None,
    ):
        """Kind represents the inner kind and not the config kind"""
        old_support = self.config.support
        old_resistance = self.config.resistance
        if support and resistance:
            self.config.support = support
            self.config.resistance = resistance

        def condition(x, _kind):
            if entry:
                _entry = max(x["entry"], x["stop"])
                stop = min(x["entry"], x["stop"])
                if _kind == "long":
                    return _entry >= entry > stop
                return stop <= entry < _entry
            return True

        entries = [x for x in self.trade_entries if condition(x, self.config.kind)]
        results = []
        if entries:
            for i in entries:
                i["zones"][kind] = [x for x in i["zones"][kind] if condition(x, kind)]
                # make the zones for the other kind empty
                i["zones"]["long"] = [] if kind == "short" else i["zones"]["long"]
            if with_result:
                if custom_entry and custom_stop:
                    # needs to be a list. To refactor.
                    result = [
                        self.determine_trades(
                            min(custom_entry, custom_stop),
                            max(custom_entry, custom_stop),
                            kind=kind,
                        )
                    ]
                else:
                    result = calculate_size_and_pnl(
                        self,
                        i["zones"][kind] if within_zone else [],
                        i,
                        _inner_kind=kind,
                    )
                results.append(result)
            if support and resistance:
                self.config.support = old_support
                self.config.resistance = old_resistance
            return [x for y in results for x in y]
        return entries

    def update_optimum_rr(self):
        optimum = self.determine_optimum_risk_reward()
        if optimum:
            self.config.risk_reward = optimum["value"] or self.config.risk_reward

    def build_instance_with_optimum_rr(
        self,
        entry_price,
        stop_price,
        kind="long",
        support=None,
        risk=None,
        resistance=None,
        increase=True,
    ):
        _entry_price = entry_price
        _stop_price = stop_price
        if kind == "long" and stop_price > entry_price:
            _entry_price = stop_price
            _stop_price = entry_price
        # elif kind == "short" and stop_price < entry_price:
        #     _entry_price = stop_price
        #     _stop_price = entry_price
        config = Config(
            entry=_entry_price,
            stop=_stop_price,
            support=support or self.config.support,
            resistance=resistance or self.config.resistance,
            kind=kind,
            increase_position=increase,
            price_places=self.config.price_places,
            decimal_places=self.config.decimal_places,
            focus=self.config.focus,
            budget=self.config.budget,
            use_default=self.config.use_default,
            risk_per_trade=risk or self.config.risk_per_trade,
            take_profit=_entry_price,
        )
        _klass = FutureInstance(config)
        return _klass

    def calculate_size_and_pnl(
        self,
        entry_price,
        stop_price,
        kind="long",
        inner_kind=None,
        support=None,
        risk=None,
        loss_price=None,
        resistance=None,
        increase=True,
        orders=False,
        risk_reward=None,
        klass: Optional["FutureInstance"] = None,
    ):
        """Determine the average entry, size and pnl for a given entry and stop price"""
        result = {}
        _entry_price = entry_price
        _stop_price = stop_price
        if kind == "long" and stop_price > entry_price:
            _entry_price = stop_price
            _stop_price = entry_price
        if klass:
            _entry_price = klass.config.entry
            _stop_price = klass.config.stop
        # elif kind == "short" and stop_price < entry_price:
        #     _entry_price = stop_price
        #     _stop_price = entry_price
        _klass = klass
        _inner_kind = inner_kind
        if not _inner_kind:
            _inner_kind = kind
        if not _klass:
            config = Config(
                entry=_entry_price,
                stop=_stop_price,
                support=support or self.config.support,
                resistance=resistance or self.config.resistance,
                kind=kind,
                increase_position=increase,
                price_places=self.config.price_places,
                decimal_places=self.config.decimal_places,
                focus=self.config.focus,
                budget=self.config.budget,
                use_default=self.config.use_default,
                risk_per_trade=risk or self.config.risk_per_trade,
                take_profit=_entry_price,
                minimum_size=self.config.minimum_size,
            )
            _risk_reward = risk_reward
            _klass = FutureInstance(config)
            if not _risk_reward:
                if not _risk_reward:
                    _klass.update_optimum_rr()
        trades = _klass.full_orders
        if trades:
            trades = _klass.raw_instance.update_open_prices(
                trades,
                _entry_price,
                kind=_inner_kind,
                current_qty=0,
                _take_profit=None,
            )
            if orders:
                return {"trade": trades}
            instance = trades[0]  # the first trade is the one with the highest pnl
            notional_value = instance["avg_entry"] * instance["avg_size"] / 125
            ratio = instance["pnl"] / notional_value
            result["trade"] = {
                "entry": _entry_price,
                "stop": _stop_price,
                "avg_entry": instance["avg_entry"],
                "avg_size": instance["avg_size"],
                "pnl": instance["pnl"],
                "sell_price": instance["sell_price"],
                "risk": instance["risk"],
                "new_stop": instance["stop"],
                "rr": instance["rr"],
                "count": len(trades),
                "start_entry": instance["start_entry"],
                "support": support,
                "ratio": to_f(ratio, "%.3f"),
                "wr": risk,
            }
            if loss_price:
                result["trade"]["loss"] = to_f(
                    determine_pnl(
                        instance["avg_entry"],
                        loss_price,
                        instance["avg_size"],
                        kind=kind,
                    ),
                    "%.3f",
                )

            return {
                **result,
            }

    def determine_optimum_risk(
        self,
        entry_price,
        stop_price,
        kind="long",
        support=None,
        loss_price=None,
        resistance=None,
        increase=True,
        single=True,
        lower_bound=4,
        upper_bound=20,
    ):
        risk_rewards = [x for x in range(lower_bound, upper_bound, 1)]

        def eval_func(y):
            rr = self.calculate_size_and_pnl(
                entry_price,
                stop_price,
                kind=kind,
                support=support,
                loss_price=loss_price,
                resistance=resistance,
                increase=increase,
                risk=y,
                orders=False,
            )
            return rr

        result = [y for x in risk_rewards if (y := eval_func(x))]
        result = sorted(result, key=lambda x: x["trade"]["ratio"], reverse=True)[:5]
        if single:
            if result:
                value = max(result, key=lambda x: x["trade"]["ratio"])
                return value
        return result

    def fibonacci_analysis(self, swing_high: float, swing_low: float):
        ranges = [0, 0.236, 0.382, 0.5, 0.618, 0.789, 1]
        fib_calc = lambda p, h, l: (p * (h - l)) + l
        fib_values = [fib_calc(x, swing_high, swing_low) for x in ranges]
        return fib_values


def calculate_size_and_pnl(
    future_trader: FutureInstance,
    zones: list,
    j: dict,
    _inner_kind="long",
    _support=None,
    _resistance=None,
    multiplier=1,
):
    rr = []
    if len(zones) == 0:
        support = min(j["entry"], j["stop"])
        resistance = max(j["entry"], j["stop"])
        result = future_trader.calculate_size_and_pnl(
            entry_price=resistance if _inner_kind == "long" else support,
            stop_price=support if _inner_kind == "long" else resistance,
            kind=_inner_kind,
            support=support,
            loss_price=j["stop"],
            resistance=resistance,
            increase=True,
            orders=True,
        )
        result["support"] = support
        result["resistance"] = resistance
        rr.append(result)
        return rr
    for i in zones:
        # print(i)
        # optimum_rr = future_trader.determine_optimum_risk(
        #     entry_price=i["entry"],
        #     stop_price=i["stop"],
        #     kind=_inner_kind,
        #     support=min(j["entry"], j["stop"]),
        #     loss_price=i["stop"],
        #     resistance=max(j["entry"], j["stop"]),
        #     increase=True,
        # )
        # print(optimum_rr)
        support = min(j["entry"], j["stop"])
        resistance = max(j["entry"], j["stop"])
        result = future_trader.calculate_size_and_pnl(
            # entry_price=i["entry"],
            # stop_price=i["stop"],
            entry_price=resistance if _inner_kind == "long" else support,
            stop_price=support if _inner_kind == "long" else resistance,
            kind=_inner_kind,
            # kind=future_trader.config.kind,
            support=_support or support,
            risk=future_trader.config.risk_per_trade * multiplier,
            loss_price=i["stop"],
            resistance=_resistance or resistance,
            increase=True,
            orders=True,
        )
        rr.append(result)
    return rr


def get_args(f, zones, j, _inner_kind):
    return [(f, x, j, _inner_kind, None, None, j.get("multiplier") or 1) for x in zones]


def use_multi_process(
    future_trader: FutureInstance,
    no_of_cpu=4,
    _kind="long",
    _inner_kind="long",
    sub_array=lambda o, k: o["zones"][k],
    get_args=get_args,
):
    processes = []
    # for o in range(0, no_of_cpu):

    for j in future_trader.trade_entries:
        zones = split_list_into_n_sublists(sub_array(j, _kind), no_of_cpu)
        # arguments = [(future_trader, x, j, _inner_kind) for x in zones]
        arguments = get_args(future_trader, zones, j, _inner_kind)
        # arguments = [(future_trader, x, j, _inner_kind) for x in zones]
        with multiprocessing.Pool(processes=no_of_cpu) as pool:
            result = pool.starmap(calculate_size_and_pnl, arguments)
            ff = [x for y in result for x in y]
            processes.append(ff)
    return [x for y in processes for x in y]


def split_list_into_n_sublists(lst, n):
    if n <= 0:
        return []

    avg = len(lst) // n
    remainder = len(lst) % n
    sublists = []

    start = 0
    for i in range(n):
        sublist_size = avg + 1 if i < remainder else avg
        end = start + sublist_size
        sublists.append(lst[start:end])
        start = end

    return sublists
