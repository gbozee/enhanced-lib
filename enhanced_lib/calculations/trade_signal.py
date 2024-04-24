import numpy as np
from dataclasses import dataclass
import math
from typing import Iterable, List, Optional, Tuple
import typing
import operator
from .utils import *


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


def _get_zone_nogen(
    current_price: float, focus: float, percent_change: float, places: str = "%.5f"
):
    result = []
    last = focus
    focus_high = last * (1 + percent_change)
    focus_low = last * (1 + percent_change) ** -1
    if focus_high > current_price:
        while focus_high > current_price:
            if last < 1:  # to resolve for tother symbols
                break
            if focus_high == last:
                break
            result.append(to_f(last, places))
            focus_high = last
            last = focus_high * (1 + percent_change) ** -1
            focus_low = last * (1 + percent_change) ** -1
    else:
        if focus_high <= current_price:
            while focus_high <= current_price:
                result.append( to_f(focus_high, places))
                focus_low = focus_high
                last = focus_low * (1 + percent_change)
                focus_high = last * (1 + percent_change)
        else:
            while focus_low <= current_price:
                result.append( to_f(focus_high, places))
                focus_low = focus_high
                last = focus_low * (1 + percent_change)
                focus_high = last * (1 + percent_change)
    return result


# write a generator function that results values until the last value is greater than the focus
def _get_zones(
    current_price: float, focus: float, percent_change: float, places: str = "%.5f"
) -> Iterable[float]:
    last = focus
    focus_high = last * (1 + percent_change)
    focus_low = last * (1 + percent_change) ** -1
    if focus_high > current_price:
        while focus_high > current_price:
            if last < 1:  # to resolve for tother symbols
                break
            if focus_high == last:
                break
            yield to_f(last, places)
            focus_high = last
            last = focus_high * (1 + percent_change) ** -1
            focus_low = last * (1 + percent_change) ** -1
    else:
        if focus_high <= current_price:
            while focus_high <= current_price:
                yield to_f(focus_high, places)
                focus_low = focus_high
                last = focus_low * (1 + percent_change)
                focus_high = last * (1 + percent_change)
        else:
            while focus_low <= current_price:
                yield to_f(focus_high, places)
                focus_low = focus_high
                last = focus_low * (1 + percent_change)
                focus_high = last * (1 + percent_change)


def _get_range(
    _range: Tuple[float, float], divisor: int, places: str = "%.5f"
) -> List[float]:
    difference = max(_range) - min(_range)
    if divisor == 0:
        factor = 0
    else:
        factor = float(places % (difference / divisor))
    return [float(places % (min(_range) + (factor * x))) for x in range(divisor)] + [
        max(_range)
    ]


def _get_trade_zone(
    current_price: float, array: Tuple[float, float], risk: int, places="%.5f"
) -> Optional[Tuple[float, float]]:
    zones = _get_range(array, risk, places=places)
    considered = [i for i, x in enumerate(zones) if x > current_price]
    if considered and considered[0] > 0:
        ranges = zones[considered[0] - 1 : considered[0] + 1]
        return (ranges[0], ranges[1])


@dataclass
class Signal:
    focus: float
    budget: float
    percent_change: float = 0.02
    price_places: str = "%.5f"
    decimal_places: str = "%.0f"
    zone_risk: float = 1
    fee: float = 0.08 / 100
    support: Optional[float] = None
    risk_reward: float = 4
    resistance: Optional[float] = None
    take_profit: Optional[float] = None
    risk_per_trade: Optional[float] = None
    increase_size: Optional[bool] = False
    additional_increase = 0
    minimum_pnl: Optional[float] = 0
    split: Optional[int] = None
    max_size: Optional[float] = None
    trade_size: Optional[float] = None
    take_profit: Optional[float] = None
    increase_position: Optional[bool] = False
    default: Optional[bool] = False
    minimum_size: Optional[float] = None

    @property
    def risk(self) -> float:
        return self.budget * self.percent_change

    @property
    def min_trades(self) -> int:
        return int(self.risk)

    @property
    def min_price(self) -> float:
        number = self.price_places.replace("%.", "").replace("f", "")
        return 1 * 10 ** -int(number)

    def get_range(self, current_price: float, kind="long") -> List[float]:
        zones = []
        risk = int(self.risk)
        future_range = self.get_future_range(current_price)
        if future_range:
            zones = _get_range(future_range, risk, places=self.price_places)
            if kind == "short":
                second_future_range = self.get_future_range(
                    future_range[0] - self.min_price
                )
                if second_future_range:
                    secondary_zones = _get_range(
                        second_future_range, risk, places=self.price_places
                    )
                    zones += secondary_zones
                    third_future_range = self.get_future_range(
                        future_range[1] + self.min_price
                    )
                    if third_future_range:
                        third_zones = _get_range(
                            third_future_range, risk, places=self.price_places
                        )
                        zones += third_zones
                        zones = [x for x in sorted(zones)]
        return zones

    def get_trade_range(
        self, current_price: float, kind="long"
    ) -> Optional[Tuple[float, float]]:
        future_range = self.get_future_range(current_price)
        if future_range:
            second_future_range = self.get_future_range(
                future_range[0] - self.min_price
            )
            third_future_range = self.get_future_range(future_range[1] + self.min_price)
            if second_future_range:
                zones = self.get_range(current_price, kind=kind)

                if kind == "short":
                    high_zone = zones[-1]
                    if third_future_range:
                        return (zones[3], high_zone)
                if len(zones) > 2:
                    high_zone = zones[1]
                    return (second_future_range[0], high_zone)

    def get_trade_zones(
        self,
        current_price: float,
        upper_bound: Optional[float] = None,
        minimum: Optional[int] = None,
        kind="long",
    ) -> Optional[List[float]]:
        trade_zones = self.get_range(current_price, kind=kind)
        if upper_bound and minimum and trade_zones:
            condition = lambda x: x <= upper_bound
            if kind == "short":
                condition = lambda x: True
                # condition = lambda x: x >= upper_bound
            trade_zones = [x for x in trade_zones if condition(x)]
            if 0 < len(trade_zones) < minimum:
                new_set = self.get_trade_zones(
                    trade_zones[0] - self.min_price, kind=kind
                )
                if new_set:
                    trade_zones = sorted(set(trade_zones + new_set))
        return trade_zones

    def get_future_range(self, current_price: float) -> Optional[Tuple[float, float]]:
        margin_range = self.get_margin_range(current_price)
        if margin_range:
            future_zone = _get_trade_zone(
                current_price, margin_range, int(self.risk), places=self.price_places
            )
            if future_zone:
                return (self.to_f(future_zone[0]), self.to_f(future_zone[1]))

    def to_f(self, number: float) -> float:
        return float(self.price_places % number)

    def to_df(self, current_price: float, places="%.3f"):
        return float(places % current_price)

    def get_future_zones(
        self, current_price: float, kind="long"
    ) -> Optional[List[float]]:
        return self.get_future_range_new(current_price, kind=kind)
        # margin_range = self.get_margin_range(current_price)
        # if margin_range:
        #     return _get_range(margin_range, int(self.risk), places=self.price_places)

    def get_margin_zones(self, current_price: float, kind="long"):
        if self.support and kind == "long":
            result = []
            start = current_price
            counter = 0
            while start > self.support:
                v = self.get_margin_range(start)
                result.append(v)
                start = v[0] - self.min_price
                counter += 1
                if counter > 20:
                    break
            return result
        if self.resistance:
            result = []
            start = current_price
            counter = 0
            while start < self.resistance:
                v = self.get_margin_range(start)
                result.append(v)
                start = v[1] + self.min_price
                counter += 1
                if counter > 20:
                    break
            return result
        return [self.get_margin_range(current_price)]

    def get_margin_range(self, current_price: float) -> Optional[Tuple[float, float]]:
        # top_zones = []
        # for x in _get_zones(
        #     to_f(current_price - self.min_price, self.price_places),
        #     self.focus,
        #     self.percent_change,
        #     places=self.price_places,
        # ):
        #     top_zones.append(x)
        #     if len(top_zones) > 10:
        #         break
        top_zones = [
            self.to_f(x)
            for x in _get_zone_nogen(
            # for x in _get_zones(
                current_price - self.min_price,
                self.focus,
                self.percent_change,
                places=self.price_places,
            )
        ]
        if top_zones:
            result = top_zones[-1]
            # result = top_zones[0]
            return self.to_f(result), self.to_f(result * (1 + self.percent_change))
            return (self.to_f(result * (1 + self.percent_change) ** -1), result)

    def transform_build_orders(self, orders: List[typing.Any]) -> List[typing.Any]:
        u = [{y: x.get(y) for y in ["entry", "risk", "quantity"]} for x in orders]
        return u

    def build_trade_dict(
        self,
        entry: float,
        stop: float,
        risk: float,
        arr: List[float],
        index: int,
        new_fees: float = 0,
        kind="long",
        take_profit=None,
        start=0,
    ):
        considered = [i for i, x in enumerate(arr) if i > index]
        with_quantity = [
            {"quantity": q, "entry": arr[x]}
            for x in considered
            if (
                q := determine_position_size(
                    arr[x],
                    arr[x - 1],
                    # stop,
                    risk,
                    places=self.decimal_places,
                )
            )
            is not None
        ]
        if self.increase_size:
            arr_length = len(with_quantity)
            with_quantity = [
                {**x, "quantity": x["quantity"] * (arr_length - i)}
                for i, x in enumerate(with_quantity)
            ]
        fees = [
            self.to_df(self.fee * x["quantity"] * x["entry"])
            for x in with_quantity
            # if (
            #     q := determine_position_size(
            #         arr[x],
            #         arr[x - 1],
            #         # stop,
            #         risk,
            #         places=self.decimal_places,
            #     )
            # )
            # is not None
        ]
        previous_risks = [self.to_df(risk) for x in with_quantity]
        # print(f"entry: {entry}", previous_risks, "index:", index)
        # print(f"entry: {entry}", fees)
        multiplier = start - index
        incured_fees = sum(fees) + sum(previous_risks)
        lost_risk = len(fees) * risk
        quantity = determine_position_size(
            entry,
            stop,
            risk,
            places=self.decimal_places,
        )
        # print({"entry": entry, "stop": stop, "risk": risk, "quantity": quantity})
        if quantity:
            if self.increase_size:
                quantity = quantity * multiplier
                new_risk = determine_pnl(entry, stop, quantity=quantity, kind=kind)
                risk = abs(new_risk)
            fee = self.to_df(self.fee * quantity * entry)
            increment = abs(len(arr) - (index + 1))
            pnl = self.to_df(risk) * (self.risk_reward + increment)
            # pnl = self.to_df(pnl + new_fees + incured_fees + lost_risk + fee)
            # if pnl < self.additional_increase:
            #     pnl += self.additional_increase
            # if pnl < self.minimum_pnl:
            #     pnl = self.minimum_pnl
            if self.minimum_pnl:
                pnl = self.minimum_pnl + fee
            sell_price = determine_close_price(entry, pnl, quantity=quantity, kind=kind)
            if take_profit and not self.minimum_pnl:
                sell_price = take_profit
                pnl = determine_pnl(entry, sell_price, quantity=quantity, kind=kind)
                pnl = pnl + fee
                sell_price = determine_close_price(
                    entry, pnl, quantity=quantity, kind=kind
                )
            risk_sell = sell_price
            incurred = self.to_df(incured_fees + new_fees)
            incurred_sell = sell_price
            if incurred:
                incurred_sell = determine_close_price(
                    entry, incurred, quantity=quantity, kind=kind
                )
            return {
                "entry": entry,
                "risk": self.to_df(risk),
                "quantity": quantity,
                "sell_price": self.to_f(sell_price),
                "incurred_sell": self.to_f(incurred_sell),
                "stop": stop,
                "pnl": pnl,
                "fee": fee,
                "net": self.to_df(pnl - fee),
                "incurred": incurred,
                "stop_percent": self.to_df(abs(entry - stop) / entry),
                "rr": self.risk_reward,
                # 'considered': considered,
                # 'index': index,
            }

    def _trade_zones(self, current_price: float, kind="long"):
        signal = self.get_trade_range(current_price, kind=kind)
        future_range = self.get_future_range(current_price)
        if signal and future_range:
            v = current_price
            if kind == "short":
                v = signal[0] if current_price < signal[0] else current_price

            trade_zones = self.get_trade_zones(
                v, upper_bound=signal[1], minimum=self.min_trades, kind=kind
            )
            if trade_zones:
                return future_range[1], trade_zones[0], trade_zones

    def get_risk_per_trade(self, number_of_orders: int):
        if self.risk_per_trade:
            return self.risk_per_trade
        return self.zone_risk / number_of_orders

    def process_orders(
        self,
        current_price: float,
        stop_loss: float,
        trade_zones: List[float],
        kind="long",
    ) -> typing.List[TradeInstanceType]:
        number_of_orders = len(trade_zones[1:])
        take_profit = stop_loss * (1 + (2 * self.percent_change))
        if kind == "short":
            take_profit = stop_loss * math.pow((1 + (2 * self.percent_change)), -1)
        if self.take_profit:
            take_profit = self.take_profit
        if number_of_orders > 0:
            # self.zone_risk = self.risk_
            risk_per_trade = self.get_risk_per_trade(number_of_orders)
            allowed_spread = self.percent_change / 100
            limit_orders = [x for x in trade_zones[1:] if x <= self.to_f(current_price)]
            market_orders = [x for x in trade_zones[1:] if x > self.to_f(current_price)]
            if kind == "short":
                limit_orders = [
                    x for x in trade_zones[1:] if x >= self.to_f(current_price)
                ]
                market_orders = [
                    x for x in trade_zones[1:] if x < self.to_f(current_price)
                ]
            # print("limit_orders", limit_orders)
            # print("market_orders", market_orders)
            increase_position = self.support and self.increase_position
            market_trades = [
                y
                for i, x in enumerate(market_orders)
                if limit_orders
                and (
                    y := self.build_trade_dict(
                        x,
                        # limit_orders[-1],
                        self.support
                        if increase_position
                        else (limit_orders[-1] if i == 0 else market_orders[i - 1]),
                        risk_per_trade,
                        market_orders,
                        i,
                        kind=kind,
                        start=len(market_orders) + len(limit_orders),
                        take_profit=take_profit,
                    )
                )
                is not None
            ]
            # total_incurred_market_fees = sum([x["incurred"] for x in market_trades])
            total_incurred_market_fees = 0
            if market_trades:
                total_incurred_market_fees += market_trades[0]["incurred"]
                total_incurred_market_fees += market_trades[0]["fee"]
            new_stop = self.support if kind == "long" else stop_loss
            limit_trades = [
                y
                for i, x in enumerate(limit_orders)
                if (
                    y := self.build_trade_dict(
                        x,
                        new_stop
                        if increase_position
                        else (stop_loss if i == 0 else limit_orders[i - 1]),
                        risk_per_trade,
                        # new_tp,
                        limit_orders,
                        i,
                        new_fees=total_incurred_market_fees,
                        kind=kind,
                        start=len(market_orders) + len(limit_orders),
                        take_profit=take_profit,
                    )
                )
                is not None
            ]
            # if market_trades:
            #     return limit_trades + [max(market_trades, key=lambda x: ["net"])]
            total_orders = limit_trades + market_trades
            if self.minimum_size and len(total_orders) > 0:
                greater_than_min_size = [
                    x for x in total_orders if x["quantity"] >= self.minimum_size
                ]
                less_than_min_size = [
                    x for x in total_orders if x["quantity"] < self.minimum_size
                ] or total_orders
                pair_size = 0
                if total_orders:
                    pair_size = math.ceil(
                        self.minimum_size / total_orders[-1]["quantity"]
                    )
                if pair_size == 0:
                    return []
                less_than_min_size = group_into_pairs_with_sum_less_than(
                    less_than_min_size, self.minimum_size
                )  # noqa: F405
                # less_than_min_size = group_into_pairs(less_than_min_size, pair_size)  # noqa: F405
                # less_than_size = [x for x in less_than_min_size if len(x) < pair_size]
                # less_than_min_size = [
                #     x for x in less_than_min_size if len(x) >= pair_size
                # ]
                # if len(less_than_size) > 0:
                #     for i in less_than_size:
                #         for q in i:
                #             less_than_min_size[-1].append(q)
                less_than_min_size = [
                    {
                        **x[0],
                        "entry": z["price"],
                        "quantity": z["quantity"],
                        "risk": to_f(sum([y["risk"] for y in x]), self.decimal_places),
                        "pnl": to_f(  # noqa: F405
                            determine_pnl(  # noqa: F405
                                z["price"],
                                x[0]["sell_price"],
                                quantity=z["quantity"],
                                kind=kind,
                            ),
                            self.decimal_places,
                        ),
                    }
                    for x in less_than_min_size
                    if (z := determine_avg([{**y, "price": y["entry"]} for y in x]))  # noqa: F405
                    is not None
                ]
                if len(less_than_min_size) == len(total_orders):
                    return total_orders
                return greater_than_min_size + less_than_min_size
            return total_orders

    def build_orders(
        self,
        current_price: float,
        kind="long",
        limit=False,
        replace_focus=False,
        min_index=0,
        max_index=2,
    ):
        focus = self.focus
        if replace_focus:
            self.focus = current_price
        new_kind = "short" if kind == "long" else "long"
        take_profit = self.take_profit
        self.take_profit = None
        result = self.get_bulk_trade_zones(current_price, kind=new_kind, limit=limit)
        if result:
            opposite_stop = result[0]["sell_price"]
            opposite_entry = result[-1]["entry"]
            trade_length = self.risk_reward + 1
            percent_change = (
                abs(
                    1
                    - (
                        max(opposite_entry, opposite_stop)
                        / min(opposite_entry, opposite_stop)
                    )
                )
                / trade_length
            )
            new_trades = [
                opposite_stop * (1 + percent_change) ** x for x in range(trade_length)
            ]
            if kind == "short":
                new_trades = [
                    opposite_stop * (1 + percent_change) ** (x * -1)
                    for x in range(trade_length)
                ]
            self.take_profit = take_profit
            new_trades = [self.to_f(x) for x in new_trades]
            if kind == "long":
                if new_trades[1] > current_price:
                    new_trades = sorted(
                        [
                            new_trades[0] * (1 + percent_change) ** (x * -1)
                            for x in range(trade_length)
                        ],
                        # reverse=True,
                    )
            # else:
            #     if min(new_trades) > current_price:
            #         new_trades = sorted(
            #             [
            #                 new_trades[1] * (1 + percent_change) ** x
            #                 for x in range(trade_length)
            #             ],
            #             reverse=True,
            #         )
            print("new_trades ", new_trades)
            result = self.process_orders(
                current_price=current_price,
                stop_loss=new_trades[0],
                trade_zones=new_trades,
                kind=kind,
            )

        self.focus = focus
        return result

    # def update_build_orders(self, current_price: float, orders:typing.List[])

    def get_bulk_trade_zones(self, current_price: float, kind="long", limit=False):
        futures = self.get_future_zones(current_price, kind=kind)
        original = self.zone_risk
        if futures:
            values = futures
            if values:
                trade_zones = sorted(values)
                if self.resistance:
                    trade_zones = [x for x in trade_zones if x <= self.resistance]
                    if kind == "short":
                        trade_zones = sorted(
                            [
                                x
                                for x in trade_zones
                                #  if x >= futures[0]
                            ],
                            reverse=True,
                        )
                if trade_zones:
                    stop_loss = trade_zones[0]
                    result = self.process_orders(
                        current_price, stop_loss, trade_zones, kind=kind
                    )
                    if not result:
                        if self.zone_risk == 1 and len(futures) > 100:
                            return []
                        if kind == "long":
                            m_z = self.get_margin_range(futures[0])
                            if m_z and m_z[0] < self.to_f(current_price):
                                return self.get_bulk_trade_zones(
                                    m_z[1], kind=kind, limit=limit
                                )
                    # if result and kind == "long" and self.support:
                    #     result = [x for x in result if x["entry"] >= self.support]
                    self.zone_risk = original
                    return result
        self.zone_risk = original

    def spot_trade(self, current_price: float, kind="long", limit=False, _orders=None):
        orders = _orders
        if not orders:
            orders = self.build_orders(current_price, kind=kind, limit=limit)
        if orders:
            incurred_fees = sum([x["fee"] for x in orders]) + sum(
                [x["risk"] for x in orders]
            )
            quantity = determine_stop_and_size(
                orders[-1]["entry"], incurred_fees, orders[0]["stop"], kind=kind
            )
            # quantity = determine_position_size(
            #     orders[-1]["entry"],
            #     orders[0]["sell_price"],
            #     incurred_fees,
            # )
            result = {
                "entry": orders[-1]["entry"],
                "stop_loss": orders[0]["stop"],
                "take_profit": orders[0]["entry"],
                "size": self.to_df(quantity),
                "risk": incurred_fees,
                "entries": [x["entry"] for x in orders],
                "sells": [x["sell_price"] for x in orders],
                "stops": [x["stop"] for x in orders],
                "pnl": [x["pnl"] for x in orders],
                "risks": [x["risk"] for x in orders],
            }
            return {
                **result,
            }

    @property
    def config_as_dict(self):
        config = {
            x: getattr(self, x)
            for x in [
                "focus",
                "budget",
                "percent_change",
                "price_places",
                "decimal_places",
                "zone_risk",
                "support",
                "resistance",
                "risk_reward",
                "risk_per_trade",
                "increase_size",
                "increase_position",
                "minimum_size",
            ]
        }
        return config

    def determine_min_risk(
        self, current_price: float, support: float, resistance: float, limit=False
    ):
        long = Signal(
            **{**self.config_as_dict, "support": support, "resistance": resistance}
        )
        long_margin = long.spot_trade(current_price, kind="long", limit=limit)
        short_margin = long.spot_trade(current_price, kind="short", limit=limit)
        return {
            "long": long_margin,
            "short": short_margin,
        }

    def build_orders_to_support(
        self, current_price: float, kind="long", margin_only=False
    ):
        if self.support or self.resistance:
            condition = lambda x: x[0] < current_price
            if kind == "short":
                condition = lambda x: x[1] >= current_price
            zones = [
                x
                for x in self.get_margin_zones(current_price, kind=kind)
                if x and condition(x)
            ]
            if margin_only:
                return zones
            # breakpoint()
            condition_1 = lambda x: x[0]
            # if kind == "short":
            #     condition_1 = lambda x: x[1]
            future_zones = [
                y
                for x in zones
                if (y := self.get_future_zones(condition_1(x))) is not None
            ]
            if kind == "short":
                closest_zone = sorted(
                    [y for x in zones if (y := self.get_future_zones(x[0])) is not None]
                )
                if closest_zone:
                    future_zones += [[closest_zone[-1][-1]]]
            ordered_future_zones = sorted(
                list(set([y for x in future_zones for y in x]))
                # ,  reverse=kind == "short"
            )
            condition_2 = lambda x: x >= self.support
            closest_support = [
                x for x in ordered_future_zones if self.support < x <= current_price
            ]
            if closest_support:
                closest_support = max(closest_support)
            if kind == "short":
                j = current_price
                if closest_support and closest_support < current_price:
                    j = closest_support
                condition_2 = lambda x: j <= x < self.resistance
            result = [
                x + self.min_price for x in ordered_future_zones if condition_2(x)
            ]
            if kind == "short" and not result:
                percent_change = self.percent_change / self.min_trades
                if ordered_future_zones:
                    result = [
                        self.to_f(
                            (ordered_future_zones[0] * math.pow(1 + percent_change, -1))
                        )
                    ] + result
            return result

    def build_orders_off_zones(
        self,
        current_price,
        start_index=0,
        kind="long",
        spread=False,
        zone_increase=1,
    ):
        future_zones = self.build_orders_to_support(current_price, kind=kind)
        if future_zones:
            if kind == "long":
                # future_zones = [x for x in future_zones]
                future_zones = [x for x in future_zones if x <= current_price]
                future_zones = sorted(future_zones, reverse=True)
            else:
                future_zones = [x for x in future_zones if x >= current_price]
            if kind == "long":
                config_array = [
                    {
                        **self.config_as_dict,
                        "support": x - self.min_price,
                        "risk_reward": self.risk_reward,
                    }
                    for i, x in enumerate(future_zones)
                ]
            else:
                config_array = [
                    {
                        **self.config_as_dict,
                        "resistance": x + self.min_price,
                        "risk_reward": self.risk_reward,
                    }
                    for i, x in enumerate(future_zones)
                ]
            # remove the first element because that would be the current price
            config_array = config_array[1:]
            current_prices = future_zones[:-1]
            if kind == "long":
                current_prices = [
                    x + self.min_price if i == 0 else x - self.min_price
                    for i, x in enumerate(current_prices)
                ]
            else:
                current_prices = [
                    x - self.min_price if i == 0 else x
                    for i, x in enumerate(current_prices)
                ]

            def smart_signals(x, i):
                vv = Signal(**x)
                vv.zone_risk = vv.zone_risk + (i * zone_increase)
                # spot_orders = vv.spot_trade(current_prices[i], kind=kind, limit=True)
                # if spot_orders:
                #     vv.additional_increase = spot_orders["risk"] * i
                return vv

            signal_instances = [Signal(**x) for x in config_array]
            signal_instances = [smart_signals(x, i) for i, x in enumerate(config_array)]
            orders = [
                r
                for i, x in enumerate(signal_instances)
                if (r := x.build_orders(current_prices[i], kind=kind, limit=True))
            ]
            sport_orders = [
                r
                for i, x in enumerate(signal_instances)
                if (r := x.spot_trade(current_prices[i], kind=kind, limit=True))
            ]
            sport_orders = process_spot(sport_orders, kind=kind)
            # run though the orders creation again but this time the instances have minimum_pnl set
            # if kind == "short":
            orders, sport_orders, signal_instances, current_prices = loop(
                sport_orders, signal_instances, current_prices, kind=kind
            )
            if orders:
                orders, sport_orders, signal_instances, current_prices = loop(
                    sport_orders,
                    signal_instances,
                    current_prices,
                    kind=kind,
                    display=True,
                )

            full_orders = sorted(
                [v for x in orders for v in x], key=lambda x: x["entry"], reverse=True
            )
            if kind == "long":
                full_orders = [x for x in full_orders if x["entry"] <= current_price]
            if kind == "long":
                full_orders = sorted(full_orders, key=lambda x: x["entry"])
            full_spot = [x for x in sport_orders if x]
            # if kind == "short":
            #     full_orders = sorted(
            #         [v for x in orders for v in x], key=lambda x: x["entry"],
            #     )
            total_risk = sum([x["risk"] for x in sport_orders])
            spread_orders = [y for x in orders for y in x]
            entry = None
            stop = None
            quantity = None
            if spread_orders:
                entry = current_prices[0]
                stop = min([x["stop"] for x in spread_orders])
                if kind == "short":
                    # entry = min([x["entry"] for x in spread_orders])
                    stop = max([x["stop"] for x in spread_orders])
                quantity = determine_stop_and_size(entry, total_risk, stop, kind=kind)
            if start_index != None:
                orders = [x for i, x in enumerate(orders) if i % 2 == start_index]
                sport_orders = [
                    x for i, x in enumerate(sport_orders) if i % 2 == start_index
                ]
            if spread:
                orders = [y for x in orders for y in x]
                orders = sorted(orders, key=lambda x: x["entry"])
                if kind == "short":
                    orders = sorted(orders, key=lambda x: x["entry"], reverse=True)
                if kind == "long":
                    orders = [x for x in orders if x["entry"] <= current_price]
            return {
                "orders": orders,
                "spot": sport_orders,
                "quantity": quantity,
                "entry": entry,
                "stop": stop,
                "total_risk": total_risk,
                "full_spot": full_spot,
                "full_orders": full_orders,
            }

    def determine_equivalent_trade(
        self,
        current_price,
        start_index=0,
        kind="long",
        spread=False,
        zone_increase=1,
    ):
        result = self.build_orders_off_zones(
            current_price,
            start_index,
            kind=kind,
            spread=spread,
            zone_increase=zone_increase,
        )
        amount_to_loose = result["total_risk"]
        entries = [y for x in result["full_spot"] for y in x["entries"]]
        sell_prices = [y for x in result["full_spot"] for y in x["sells"]]
        entry = max(entries)
        stop = max(sell_prices)
        config = self.config_as_dict
        if kind == "long":
            config.update({"resistance": stop})
        else:
            entry = min(entries)
            stop = min(sell_prices)
            config.update(
                {
                    "support": stop,
                }
            )

        signal = Signal(**config)
        signal.minimum_pnl = amount_to_loose
        new_kind = "long" if kind == "short" else "short"
        orders = signal.build_orders(
            entry,
            kind=new_kind,
        )
        total_risk = sum([x["risk"] for x in orders]) + sum([x["fee"] for x in orders])
        return result

    def get_future_range_new(self, current_price, kind="long"):
        """
        return the list of zones within the margin range based off the risk_reward
        it always increase the risk_reward by 1
        """
        margin_range = self.get_margin_range(current_price)
        # margin_zones = self.get_margin_zones(current_price)
        # remaining_zones = [x for x in margin_zones if x != margin_range]
        # print("margin_range", margin_range, "support", self.support)
        # print('margin_zones', margin_zones)
        if margin_range:
            if margin_range[1] < self.support:
                return []
            percent_change = self.percent_change / self.risk_reward
            difference = abs(margin_range[0] - margin_range[1])
            # print('difference', difference,'risk_reward', self.risk_reward)
            spread = to_f(difference / self.risk_reward)
            entries = [
                to_f(margin_range[1] - (spread * x))
                for x in range(int(self.risk_reward) + 1)
            ]
            if kind == "short":
                entries = [
                    to_f(margin_range[1] * math.pow(1 + (percent_change), x))
                    for x in range(int(self.risk_reward) + 1)
                ]
            # print('entries', entries)
            if min(entries) < self.to_f(current_price) < max(entries):
                return sorted(entries)
            new_range = None
            margin_zones = self.get_margin_zones(current_price)
            remaining_zones = [x for x in margin_zones if x != margin_range]
            if remaining_zones:
                new_range = remaining_zones[0][1]
                if new_range:
                    entries = []
                    x = 0
                    new_range = self.to_f(new_range)
                    while len(entries) < int(self.risk_reward) + 1:
                        if kind == "long":
                            value = to_f(new_range - (spread * x))
                            if value <= self.to_f(current_price):
                                entries.append(value)
                        else:
                            value = to_f(new_range * math.pow(1 + (percent_change), x))
                            if value >= self.to_f(current_price):
                                entries.append(value)
                        x += 1
            if len(remaining_zones) == 0 and to_f(current_price) <= min(entries):
                next_focus = margin_range[0] * math.pow(1 + self.percent_change, -1)
                entries = []
                x = 0
                while len(entries) < int(self.risk_reward) + 1:
                    if kind == "long":
                        value = to_f(next_focus - (spread * x))
                        if value <= self.to_f(current_price):
                            entries.append(value)
                    else:
                        value = to_f(next_focus * math.pow(1 + (percent_change), x))
                        if value >= self.to_f(current_price):
                            entries.append(value)
                    x += 1
                return sorted(entries)
            # elif self.to_f(current_price) <= min(entries) and len(remaining_zones) == 0:
            #     new_range = margin_range[0] * math.pow(1 + self.percent_change, -1)
            # entries.append(entries[-1] * (1 + percent_change))
            return sorted(entries)

    def default_build_entry(
        self,
        entry_price: float,
        stop_loss: float,
        risk: float,
        pnl: float = None,
        kind="long",
        stop_percent=None,
        no_of_trades=1,
        take_profit=None,
        current_entry=None,
        current_quantity=0,
        support=None,
        resistance=None,
        **kwargs,
    ):
        """Build out trades with tight stops to get the maximum position sizes"""
        _stop_loss = stop_loss
        _entry_price = entry_price
        _resistance = resistance
        if not _stop_loss and stop_percent:
            _stop_loss = (
                _entry_price * (1 + stop_percent) ** -1
                if kind == "long"
                else _entry_price * (1 + stop_percent)
            )
        percent_change = (
            (max(_entry_price, _stop_loss) / min(_entry_price, _stop_loss)) - 1
            if _stop_loss
            else self.percent_change
        )
        _no_of_trades = no_of_trades or self.risk_reward
        # print('original_risk_per_trade', self.risk_per_trade)
        risk_per_trade = risk / self.risk_reward
        # risk_per_trade = risk / _no_of_trades

        derived_config = {
            **self.config_as_dict,
            "percent_change": percent_change,
            "focus": _entry_price,
            "resistance": (entry_price * pow(1 + percent_change, 5)),
            # "risk_per_trade": risk / self.risk_reward,
            "risk_per_trade": risk_per_trade,
            "risk_reward": _no_of_trades,
            "minimum_pnl": pnl,
            "take_profit": take_profit or self.take_profit,
            "support": _stop_loss if kind == "long" else (support or self.support),
        }
        # print('derived_config', derived_config)
        instance = Signal(**derived_config)
        # if optimum:
        #     breakpoint()
        result = instance.get_bulk_trade_zones(_entry_price, kind=kind) or []

        def best_transform(x):
            if kind == "long":
                return x["entry"] > x["stop"] + 0.5
            return x["entry"] + 0.5 < x["stop"]

        # return result
        trades = [x for x in result if best_transform(x)]
        return trades

    def build_entry(
        self,
        entry_price: float,
        stop_loss: float,
        risk: float,
        pnl: float = None,
        kind="long",
        stop_percent=None,
        no_of_trades=0,
        take_profit=None,
        current_entry=None,
        current_quantity=0,
        support=None,
        resistance=None,
        **kwargs,
    ):
        """Build out trades with tight stops to get the maximum position sizes"""
        _stop_loss = stop_loss
        _entry_price = entry_price
        _resistance = resistance
        if not _stop_loss and stop_percent:
            _stop_loss = (
                _entry_price * (1 + stop_percent) ** -1
                if kind == "long"
                else _entry_price * (1 + stop_percent)
            )
        percent_change = (
            (max(_entry_price, _stop_loss) / min(_entry_price, _stop_loss)) - 1
            if _stop_loss
            else self.percent_change
        )
        _no_of_trades = no_of_trades or self.risk_reward
        # print('original_risk_per_trade', self.risk_per_trade)
        # risk_per_trade = risk / self.risk_reward
        risk_per_trade = risk / _no_of_trades
        optimum = None
        if no_of_trades == 0:
            optimum = self.determine_optimum_risk_reward(
                entry=_entry_price,
                stop_loss=stop_loss,
                risk=self.risk_per_trade,
                kind=kind,
                support=support,
                single=True,
            )
            if optimum:
                _no_of_trades = optimum["value"] or self.risk_reward
                if kind == "short":
                    _resistance = optimum["stop"]
                if self.default:
                    risk_per_trade = self.risk_per_trade / _no_of_trades
                else:
                    _entry_price = optimum["entry"]
                    risk_per_trade = self.risk_per_trade / optimum["length"]

        derived_config = {
            **self.config_as_dict,
            "percent_change": percent_change,
            "focus": _entry_price,
            "resistance": _resistance or (entry_price * pow(1 + percent_change, 5)),
            # "risk_per_trade": self.risk_per_trade,
            "risk_per_trade": risk_per_trade,
            "risk_reward": _no_of_trades,
            "minimum_pnl": pnl,
            "take_profit": take_profit or self.take_profit,
            "support": _stop_loss if kind == "long" else (support or self.support),
        }
        # print('derived_config', derived_config)
        instance = Signal(**derived_config)
        # if optimum:
        #     breakpoint()
        result = instance.get_bulk_trade_zones(_entry_price, kind=kind)

        def best_transform(x):
            if kind == "long":
                return x["entry"] > x["stop"] + 0.5
            return x["entry"] + 0.5 < x["stop"]

        # return result
        trades = [x for x in result if best_transform(x)]
        if current_entry:
            rr = self.update_open_prices(
                trades,
                current_entry,
                kind=kind,
                current_qty=current_quantity,
                _take_profit=take_profit,
            )
            return rr
        return trades

    def determine_optimum_risk_reward(
        self,
        entry: float = None,
        stop_loss: float = None,
        risk: float = None,
        kind="long",
        single=True,
        lower_bound=30,
        support=None,
        upper_bound=199,
    ):
        risk_rewards = [x for x in range(lower_bound, upper_bound, 1)]

        def eval_func(y):
            new_inst = Signal(
                **{**self.config_as_dict, "risk_reward": y, "increase_position": True}
            )
            trades = new_inst.default_build_entry(
                # trades = self.build_entry(
                take_profit=self.take_profit,
                entry_price=entry,
                stop_loss=stop_loss,
                no_of_trades=y,
                risk=risk,
                kind=kind,
                # current_entry=entry,
                # support=support or min(entry, stop_loss),
            )
            _max = max([x["entry"] for x in trades]) if trades else 0
            _min = min([x["entry"] for x in trades]) if trades else 0
            result = {
                "result": trades,
                "value": y,
                "max": max([x["quantity"] for x in trades]) if trades else 0,
                "entry": _max if kind == "long" else _min,
                "stop": max([x["stop"] for x in trades]) if trades else 0,
            }
            found_trades = [x for x in trades if x["quantity"] == result["max"]]
            if found_trades:
                return result

        result = [y for x in risk_rewards if (y := eval_func(x))]
        # for i in result:
        #     # print(i)
        #     print(
        #         {
        #             "value": i["value"],
        #             'result': i['result'],
        #             "max": i["max"],
        #             "entry": i["entry"],
        #             "stop": i["stop"],
        #         }
        #     )
        # sort by max
        result = sorted(result, key=lambda x: x["max"], reverse=True)[:5]
        if single:
            if result:
                value = max(result, key=lambda x: x["max"])
                return {
                    "value": value["value"],
                    "max": value["max"],
                    "length": len(value["result"]),
                    "entry": value["entry"],
                    "stop": value["stop"],
                }
        # return result
        return [
            {
                "value": x["value"],
                "max": x["max"],
                "pnl": max(y["pnl"] for y in x["result"]),
                "entry": x["entry"],
            }
            for x in result
        ]

    def update_open_prices(
        self,
        trades: typing.List[typing.Any],
        current_entry: float = None,
        kind="long",
        current_qty=0,
        _take_profit=0,
    ):
        take_profit = _take_profit or self.take_profit

        def kindCondition(x, v=None, operand=None, operand_reverse=None):
            _v = v
            _operand = operand or operator.le
            _operand_reverse = operand_reverse or operator.ge
            if not _v:
                _v = current_entry
            if kind == "long":
                return _operand(x["entry"], _v)
            return _operand_reverse(x["entry"], _v)

        less = [x for x in trades if kindCondition(x)]

        def avgCondition(x):
            considered = []
            if kind == "long":
                considered = [y for y in trades if y["entry"] > current_entry]
            else:
                considered = [y for y in trades if y["entry"] < current_entry]
            x_pnl = None
            remaining = [
                v
                for v in less
                if kindCondition(
                    v, x["entry"], operand=operator.ge, operand_reverse=operator.le
                )
            ]
            if not remaining:
                return {**x, "pnl": x_pnl}
            start = (
                max([x["entry"] for x in remaining])
                if kind == "long"
                else min([x["entry"] for x in remaining])
            )
            considered = [{**x, "entry": start} for x in considered]
            considered += remaining
            avg_entry = determine_avg(
                [{"price": x["entry"], "quantity": x["quantity"]} for x in considered]
                + [{"price": current_entry, "quantity": current_qty}],
                price_places=self.price_places,
            )
            _pnl = x.get("pnl")
            sell_price = x["sell_price"]
            if take_profit:
                _pnl = determine_pnl(
                    avg_entry["price"],
                    take_profit,
                    avg_entry["quantity"],
                    kind=kind,
                )
                sell_price = take_profit
            return {
                **x,
                "avg_entry": avg_entry["price"],
                "avg_size": avg_entry["quantity"],
                "pnl": to_f(_pnl, self.decimal_places),
                "sell_price": sell_price,
                "start_entry": current_entry,
            }

        return [avgCondition(x) for x in trades]

    def build_trade_entries(
        self,
        risk=4,
        main_split=5,
        sub_split=3,
        kind="long",
        use_fibonacci=False,
    ):
        _entry = self.resistance if kind == "long" else self.support
        _stop = self.support if kind == "long" else self.resistance
        main_entries = self.default_build_entry(
            entry_price=_entry,
            stop_loss=_stop,
            no_of_trades=main_split,
            risk=self.risk_per_trade * main_split,
            kind=kind,
        )
        unique = sorted(
            list(
                set(
                    [x["entry"] for x in main_entries]
                    + [x["stop"] for x in main_entries]
                )
            )
        )
        if use_fibonacci:
            unique = sorted(
                fibonacci_analysis(self.support, self.resistance, kind=kind)
            )
        print("unique", unique)

        def build_large_spread_pair(index, new_unique):
            # only relevant for short trades
            _entry = min(index["entry"], index["stop"])
            start_index = new_unique.index(_entry)
            if start_index > 0:
                start_index = 0
            considered = [x for x in new_unique if x > _entry]
            return [
                {"entry": _entry, "stop": x, "multiplier": i + start_index + 1}
                for i, x in enumerate(considered)
            ]

        def build_pair(arr, _kind):
            def tt(i):
                rr = {
                    "stop": arr[i],
                    "entry": arr[i + 1],
                }
                if _kind == "short" and rr["stop"] < rr["entry"]:
                    prev = rr["stop"]
                    rr["stop"] = rr["entry"]
                    rr["entry"] = prev

                return rr

            pairs = [tt(i) for i, x in enumerate(arr) if i < len(arr) - 1]
            return pairs

        def build_entry_and_pair(
            i, no_of_trades, _kind, as_pair=True, _support=None, pair=None
        ):
            _entry_price = i["entry"]
            _stop_price = i["stop"]
            if _kind == "long" and _entry_price < _stop_price:
                _entry_price = i["stop"]
                _stop_price = i["entry"]
            if _kind == "short" and _entry_price > _stop_price:
                _entry_price = i["stop"]
                _stop_price = i["entry"]

            support = _support or min(_entry_price, _stop_price)
            sub_entries = self.default_build_entry(
                entry_price=_entry_price,
                stop_loss=_stop_price,
                no_of_trades=no_of_trades,
                risk=risk,
                kind=_kind,
                support=support,
            )
            if as_pair:
                sub_unique = sorted(
                    list(
                        set(
                            [x["entry"] for x in sub_entries]
                            + [x["stop"] for x in sub_entries]
                        )
                    )
                )
                return [x for x in build_pair(sub_unique, _kind)]
            return sub_entries

        if unique:
            if kind == "short":
                unique = sorted(unique, reverse=True)
            # build pairs
            pairs = build_pair(unique, kind)
            result = []
            for jj, i in enumerate(pairs):
                result.append(
                    {
                        **i,
                        "zones": {
                            "long": build_entry_and_pair(
                                i,
                                sub_split,
                                "long",
                            ),
                            "short": build_entry_and_pair(
                                i,
                                sub_split,
                                "short",
                            ),
                        },
                        "extended_zones": build_large_spread_pair(i, sorted(unique)),
                        # if kind == "short"
                        # else [],
                    }
                )
            if kind == "short":
                result = list(reversed(result))
            return result

    def calculate_size_and_pnl(
        self,
        entry_price,
        stop_price,
        kind="long",
        support=None,
        resistance=None,
        risk=None,
        loss_price=None,
    ):
        """Determine the average entry, size and pnl for a given entry and stop price"""
        result = {}
        _entry_price = entry_price
        _stop_price = stop_price
        trades = self.build_entry(
            entry_price=_entry_price,
            stop_loss=_stop_price,
            no_of_trades=0,
            risk=risk or self.risk_per_trade,
            kind=kind,
            support=support,
            resistance=resistance,
            current_entry=entry_price,
            take_profit=_entry_price,
        )
        instance = trades[0]  # the first trade is the one with the highest pnl
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

        # instance = None
        return {
            **result,
        }


def loop(
    sport_orders: list,
    signal_instances: typing.List[Signal],
    current_prices: typing.List[float],
    kind="long",
    display=False,
):
    if len(sport_orders) != len(signal_instances):
        signal_instances = signal_instances[1:]
        current_prices = current_prices[1:]
    if len(sport_orders) == len(signal_instances):
        for i, j in enumerate(signal_instances):
            j.minimum_pnl = sport_orders[i]["incurred_risk"] + sport_orders[i]["risk"]
            if display:
                print(j.minimum_pnl)
        orders = [
            r
            for i, x in enumerate(signal_instances)
            if (r := x.build_orders(current_prices[i], kind=kind, limit=True))
        ]
        sport_orders = [
            r
            for i, x in enumerate(signal_instances)
            if (r := x.spot_trade(current_prices[i], kind=kind, limit=True))
        ]
        sport_orders = process_spot(sport_orders, kind=kind)
    else:
        orders = []
        sport_orders = []

    return [orders, sport_orders, signal_instances, current_prices]


def process_spot(arr: list, kind="long"):
    new_array = [
        {**x, "incurred_risk": sum(z["risk"] for z in arr[:i])}
        for i, x in enumerate(arr)
    ]

    def custom_calc(r):
        valid_pnl_index = [i for i, x in enumerate(r["pnl"]) if x < r["incurred_risk"]]
        valid_entries = [r["entries"][x] for x in valid_pnl_index]
        pnl_to_recover = [
            abs(r["pnl"][x] - r["incurred_risk"]) for x in valid_pnl_index
        ]
        valid_sells = [r["sells"][x] for x in valid_pnl_index]
        valid_quantities = [
            determine_stop_and_size(valid_entries[i], x, valid_sells[i], kind=kind)
            for i, x in enumerate(pnl_to_recover)
        ]
        result = [
            {
                "pnl": pnl_to_recover[i],
                "sell": valid_sells[i],
                "size": x,
                "entry": valid_entries[i],
            }
            for i, x in enumerate(valid_quantities)
        ]
        if result:
            result = max(result, key=lambda x: x["pnl"])
        return {
            **r,
            "m_orders": result,
        }

    return [custom_calc(x) for x in new_array]
