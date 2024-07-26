from dataclasses import dataclass, fields
import operator
from typing import Optional, List, Literal, TypedDict
from .trade_signal import Signal, TradeInstanceType
from .utils import (
    determine_avg as determine_average_entry_and_size,
    OrderType,
    determine_pnl,
    to_f,
    fibonacci_analysis,
)


class TradingZoneType(TypedDict):
    kind: Literal["long", "short"]
    trend: Literal["long", "short"]
    entry: float
    stop: float
    no_of_trades: int
    use_fibonacci: bool


class TradingZoneDict(TypedDict):
    entry: float
    stop: float
    size: float


@dataclass
class AppConfig:
    fee: float
    risk_per_trade: float
    risk_reward: float
    focus: float
    budget: float
    support: float
    resistance: float
    percent_change: float
    tradeSplit: float
    take_profit: Optional[float]
    kind: Literal["long", "short"]
    entry: float
    stop: float
    min_size: float
    minimum_size: Optional[float]
    price_places: Optional[str]
    decimal_places: Optional[str]
    strategy: Literal["quantity", "entry"]
    as_array: Optional[bool] = False
    raw: Optional[bool] = False

    @property
    def currentEntry(self):
        return self.entry

    @classmethod
    def get_all_fields(cls, exclude=()):
        return [field.name for field in fields(cls) if field.name not in exclude]

    def get_trading_zones(self, params: TradingZoneType) -> List[TradingZoneDict]:
        kind = params["kind"] or self.kind
        _entry = self.resistance if kind == "long" else self.support
        _stop = self.support if kind == "long" else self.resistance

        def build_entry_and_stop(u: List[float], _kind: Literal["long", "short"]):
            def condition(i):
                return i < len(u) - 1 if _kind == "long" else i > 0

            return [
                {
                    "stop": o if _kind == "long" else u[i - 1],
                    "entry": u[i + 1] if _kind == "long" else o,
                }
                for i, o in enumerate(u)
                if condition(i)
            ]

        if params["use_fibonacci"]:
            _r = fibonacci_analysis(
                self.support, self.resistance, kind=kind, places=self.price_places
            )
            return [
                x for x in build_entry_and_stop(_r, kind) if x["entry"] and x["stop"]
            ]
        result = build_config(
            self,
            {
                "entry": params["entry"] or _entry,
                "stop": params["stop"] or _stop,
                "kind": params["trend"],
                "no_of_trades": params["no_of_trades"],
            },
        )
        return [
            {
                "entry": x["entry"] if kind == "long" else x["stop"],
                "stop": x["stop"] if kind == "long" else x["entry"],
            }
            for x in result
            if x
        ]


class ParamType(TypedDict):
    take_profit: Optional[float]
    entry: float
    risk: Optional[float]
    stop: Optional[float]
    risk_reward: Optional[float]
    raw_instance: Optional[bool]
    no_of_trades: Optional[int]
    increase: Optional[bool]
    price_places: Optional[str]
    decimal_places: Optional[str]
    kind: Optional[Literal["long", "short"]]
    support: Optional[float]
    resistance: Optional[float]


def build_config(app_config: AppConfig, params: ParamType):
    fee = app_config.fee / 100
    working_risk = params.get("risk") or app_config.risk_per_trade
    trade_no = params.get("no_of_trades") or app_config.risk_reward
    minimum_size = app_config.min_size or app_config.minimum_size
    instance = Signal(
        focus=app_config.focus,
        fee=fee,
        budget=app_config.budget,
        risk_reward=params.get("risk_reward") or trade_no,
        support=params.get("support") or app_config.support,
        resistance=params.get("resistance") or app_config.resistance,
        price_places=app_config.price_places or params.get("price_places"),
        decimal_places=params.get("decimal_places") or app_config.decimal_places,
        percent_change=app_config.percent_change / app_config.tradeSplit,
        risk_per_trade=working_risk,
        increase_position=params["increase"],
        minimum_size=minimum_size,
        # first_order_size=app_config.first_order_size
    )
    if params.get("raw_instance"):
        return instance
    if not params.get("stop"):
        return []

    condition = (
        (params["entry"] > app_config.support)
        if params["kind"] == "long"
        else params["entry"] >= app_config.support
    ) and params["stop"] >= 0.999
    if (params["entry"] == params["stop"]) or not condition:
        return []
    result = instance.default_build_entry(
        entry_price=params["entry"],
        stop_loss=params["stop"],
        risk=working_risk,
        kind=params["kind"] or app_config.kind,
        no_of_trades=trade_no,
    )
    return compute_total_average_for_each_trade(app_config, result, current_qty=0)
    return result


class AvgType(TypedDict):
    price: float
    quantity: float
    pnl: float


def build_avg(
    _trades: List[OrderType],
    kind: Literal["long", "short"],
    decimal_places="%.3f",
    price_places="%.1f",
):
    assert len(_trades) > 0
    avg: AvgType = determine_average_entry_and_size(
        _trades, places=decimal_places, price_places=price_places
    )
    # stop_prices = [trade["stop"] for trade in _trades]
    # stop_loss = min(stop_prices) if kind == "long" else max(stop_prices)
    # avg["pnl"] = determine_pnl(avg["price"], stop_loss, avg["quantity"], kind)
    return avg


def compute_total_average_for_each_trade(
    app_config: AppConfig, trades: List[TradeInstanceType], current_qty=0,_current_entry=0
):
    take_profit = (
        max(app_config.entry, app_config.stop)
        if app_config.kind == "long"
        else min(app_config.entry, app_config.stop)
    )
    current_entry = _current_entry or app_config.currentEntry
    kind = app_config.kind

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
        avg_entry = build_avg(
            [{"price": x["entry"], "quantity": x["quantity"]} for x in considered]
            + [{"price": current_entry, "quantity": current_qty}],
            kind=kind,
            price_places=app_config.price_places,
            decimal_places=app_config.decimal_places,
        )
        _pnl = x.get("pnl")
        sell_price = x["sell_price"]
        loss = 0
        if take_profit:
            _pnl = determine_pnl(
                avg_entry["price"],
                take_profit,
                avg_entry["quantity"],
                kind=kind,
            )
            sell_price = take_profit
            loss = determine_pnl(avg_entry['price'],x.get('stop'),avg_entry['quantity'],kind=kind)
        return {
            **x,
            "avg_entry": avg_entry["price"],
            "avg_size": avg_entry["quantity"],
            "pnl": to_f(_pnl, app_config.decimal_places),
            'neg.pnl': to_f(loss, app_config.decimal_places),
            "sell_price": sell_price,
            "start_entry": current_entry,
        }

    return [avgCondition(x) for x in trades]
