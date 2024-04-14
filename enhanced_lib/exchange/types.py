from dataclasses import dataclass
from typing import List, Literal, Optional, TypedDict

from ..calculations.utils import (
    determine_pnl,
    get_decimal_places,
    to_f,
    determine_close_price,
)
from ..calculations.hedge import determine_liquidation
import statistics


def inject_fields(parent):
    def doit(cls):
        cls.__annotations__ = parent.__annotations__ | cls.__annotations__
        return cls

    return doit


PositionKind = Literal["long", "short"]


class TradeDict(TypedDict):
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

    # # invalid
    # incurred_sell: float
    # stop_percent: float
    # rr: int
    # start_entry: float
    # take_profit: float
    # risk_sell: float


class TradeEntryDict(TypedDict):
    stop: float
    entry: float
    size: float
    risk_reward: float
    risk_per_trade: float
    trades: List[TradeDict]


class ProfileDict(TypedDict):
    focus: int
    zone_risk: int
    zone_split: int
    price_places: str
    buy_more: bool
    is_margin: bool
    budget: int
    expected_loss: int
    risk_reward: int
    spread: int
    follow_profit: bool
    follow_stop: bool
    id: str
    entry_price: int
    dollar_price: int
    max_size: float
    bull_factor: float
    bear_factor: float
    loss_factor: int
    support: int
    resistance: float
    tradeSplit: int
    futureBudget: int
    decimal_places: str
    min_size: float
    transfer_funds: bool
    sub_accounts: List[str]
    margin_sub_account: str
    risk_per_trade: int
    profit_quote_price: int
    profit_base_price: int


class OrderDict(TypedDict):
    orderId: Optional[int]
    symbol: Optional[str]
    status: Optional[str]
    clientOrderId: Optional[str]
    price: Optional[str]
    avgPrice: Optional[str]
    origQty: Optional[str]
    executedQty: Optional[str]
    cumQuote: Optional[str]
    timeInForce: Optional[str]
    type: Optional[str]
    reduceOnly: Optional[bool]
    closePosition: Optional[bool]
    side: Optional[str]
    positionSide: Optional[str]
    stopPrice: Optional[str]
    workingType: Optional[str]
    priceProtect: Optional[bool]
    origType: Optional[str]
    priceMatch: Optional[str]
    selfTradePreventionMode: Optional[str]
    goodTillDate: Optional[int]
    time: Optional[int]
    updateTime: Optional[int]
    # cummulativeQuoteQty: Optional[str]
    # icebergQty: Optional[str]
    # isWorking: Optional[bool]
    # isIsolated: Optional[bool]

class MarginOrderDict(TypedDict):
    orderId: Optional[int]
    symbol: Optional[str]
    status: Optional[str]
    clientOrderId: Optional[str]
    price: Optional[str]
    origQty: Optional[str]
    executedQty: Optional[str]
    timeInForce: Optional[str]
    type: Optional[str]
    side: Optional[str]
    stopPrice: Optional[str]
    selfTradePreventionMode: Optional[str]
    time: Optional[int]
    updateTime: Optional[int]
    cummulativeQuoteQty: Optional[str]
    icebergQty: Optional[str]
    isWorking: Optional[bool]
    isIsolated: Optional[bool]


class AccountBalanceDict(TypedDict):
    asset: str
    balance: float


class PositionDict(TypedDict):
    symbol: str
    positionAmt: float
    entryPrice: float
    breakEvenPrice: str
    markPrice: float
    unRealizedProfit: float
    liquidationPrice: float
    leverage: int
    maxNotionalValue: float
    marginType: str
    isolatedMargin: float
    isAutoAddMargin: str
    positionSide: str
    notional: str
    isolatedWallet: float
    updateTime: int
    isolated: bool
    adlQuantile: int


class ClosedOrderDict(TypedDict):
    symbol: str
    id: int
    orderId: int
    side: str
    price: str
    qty: str
    realizedPnl: str
    marginAsset: str
    quoteQty: str
    commission: str
    commissionAsset: str
    time: int
    positionSide: str
    buyer: bool
    maker: bool


class PositionsDict(TypedDict):
    long: PositionDict
    short: PositionDict
    both: Optional[PositionDict]


class ClosedOrdersDict(TypedDict):
    long: ClosedOrderDict
    short: ClosedOrderDict


class ExchangeInfo(TypedDict):
    last_order: float
    account_balance: List[AccountBalanceDict]
    open_orders: List[OrderDict]
    position: PositionsDict
    closed_orders: ClosedOrdersDict


@dataclass
@inject_fields(TradeDict)
class Trade:
    pass


@dataclass
@inject_fields(TradeEntryDict)
class TradeEntry:
    @property
    def trade_instances(self):
        def transform(u):
            return {k: u.get(k) for k in TradeDict.__annotations__.keys()}

        return [Trade(**transform(x)) for x in self.trades]

    @property
    def kind(self) -> PositionKind:
        single_trade = self.trade_instances[0]
        if single_trade.entry > single_trade.sell_price:
            return "short"
        return "long"

    def split_at(self, entry: float):
        orders_above = [x for x in self.trade_instances if x.entry > entry]
        orders_below = [x for x in self.trade_instances if x.entry < entry]
        if self.kind == "long":
            market_size = sum(x.quantity for x in orders_above)
            list_order_entry = min(orders_above, key=lambda x: x.entry)
            remaining = orders_below
        else:
            market_size = sum(x.quantity for x in orders_below)
            list_order_entry = max(orders_below, key=lambda x: x.entry)
            remaining = orders_above

        return market_size, list_order_entry, remaining

    def new_entry_at(self, entry: float):
        market_size, list_order_entry, remaining = self.split_at(entry)
        kwargs = {
            k: getattr(list_order_entry, k) for k in TradeDict.__annotations__.keys()
        }
        kwargs["quantity"] = market_size
        return remaining + [Trade(**kwargs)]

    def pnl_at_sell(self, entry: float):
        market_size, list_order_entry, remaining = self.split_at(entry)
        sell_price = list_order_entry.sell_price
        return determine_pnl(entry, sell_price, market_size, kind=self.kind)

    def last_placed_trade(self, current_size: float):
        result = [
            i for i, x in enumerate(self.trade_instances) if x.avg_size > current_size
        ]
        if result:
            bb = result[-1]
            return self.trade_instances[bb]

    def avg_entry(self, entry: float):
        trades = self.new_entry_at(entry)
        return sum(x.entry * x.quantity for x in trades) / sum(
            x.quantity for x in trades
        )


@dataclass
@inject_fields(OrderDict)
class Order:
    @property
    def quantity(self):
        return float(self.origQty)

    @property
    def entry_price(self):
        return float(self.price)

    @property
    def stop_price(self):
        return float(self.stopPrice)

@dataclass
@inject_fields(MarginOrderDict)
class MarginOrder:
    @property
    def quantity(self):
        return float(self.origQty)

    @property
    def entry_price(self):
        return float(self.price)

    @property
    def stop_price(self):
        return float(self.stopPrice)


@dataclass
@inject_fields(PositionDict)
class PositionKlass:
    fee_rate = 0.018

    @property
    def size(self):
        return abs(self.positionAmt)

    @property
    def entry_price(self):
        return self.entryPrice

    @property
    def kind(self) -> PositionKind:
        return self.positionSide.lower()

    def determine_pnl(self, current_price: float):
        return determine_pnl(
            self.entry_price,
            current_price,
            self.size,
            kind=self.kind,
        )

    def determine_minimum_pnl(self, fee_percent):
        notional_value = self.entry_price * self.size
        value = notional_value * self.fee_rate / 100
        return value / fee_percent

    def determine_close_price(self, pnl: float):
        return determine_close_price(self.entry_price, pnl, self.size, kind=self.kind)


@dataclass
@inject_fields(ClosedOrderDict)
class ClosedOrder:
    @property
    def sell_price(self):
        return float(self.price)

    @property
    def is_take_profit(self):
        return float(self.realizedPnl) > 0

    @property
    def is_stop_loss(self):
        return float(self.realizedPnl) < 0

    @property
    def kind(self) -> PositionKind:
        return self.positionSide.lower()


class OpenOrderStat(TypedDict):
    size: float
    count: int
    avg: float
    fees: float


class CloseOrderStat(TypedDict):
    pnl: float
    remaining_size: float
    fees: float


@dataclass
class OrderStats:
    maker: float
    taker: float

    def determine_liquidation(
        self,
        position: PositionDict,
        balance: float,
    ):
        empty_position = {
            "entry": 0,
            "size": 0,
        }
        _position = {
            "entry": position["entryPrice"],
            "size": abs(position["positionAmt"]),
        }
        long_position = _position if position["kind"] == "long" else empty_position
        short_position = _position if position["kind"] == "short" else empty_position
        result = determine_liquidation(
            balance=balance,
            long_position=long_position,
            short_position=short_position,
            symbol=position["symbol"],
        )
        return result["liquidation"]

    def open_orders(
        self, orders: List[Order], position: Optional[PositionKlass], balance=0
    ) -> OpenOrderStat:
        def get_key():
            if position:
                return position.entry_price
            return orders[0].price if orders else 0

        places = get_decimal_places(str(get_key()))
        decimal_places = get_decimal_places(str(orders[0].origQty)) if orders else 0
        size = sum(x.quantity for x in orders)
        total_notional_value = sum((x.entry_price * x.quantity) for x in orders)
        if position:
            size += position.size
            total_notional_value += position.entry_price * position.size

        avg_entry = total_notional_value / (size or 1)
        last_order = orders[-1].entry_price if orders else None
        fees = sum((x.quantity * x.entry_price) * self.maker for x in orders)
        liquidation = self.determine_liquidation(
            {
                "kind": position.kind,
                "entryPrice": avg_entry,
                "positionAmt": size,
                "symbol": position.symbol,
            },
            balance,
        )
        return {
            "size": to_f(size, f"%.{decimal_places}f"),
            "count": len(orders),
            "avg": to_f(avg_entry, f"%.{places}f"),
            "last": last_order,
            "fees": to_f(fees, f"%.{places}f"),
            "liquidation": to_f(liquidation, f"%.{places}f"),
            "loss": to_f(
                determine_pnl(avg_entry, last_order, size, kind=position.kind),
                f"%.{places}f",
            )
            if last_order
            else 0,
        }

    def close_orders(
        self,
        orders: List[Order],
        position: PositionKlass,
        opposite_result: Optional[List[Order]] = None,
    ) -> CloseOrderStat:
        def get_key(_key="entry_price"):
            if position:
                return position.entry_price
            return orders[0].price if orders else 0

        places = get_decimal_places(str(get_key()))
        decimal_places = get_decimal_places(str(orders[0].origQty)) if orders else 3
        pnl = determine_pnl(
            position.entry_price,
            orders[0].entry_price,
            position.size,
            kind=position.kind,
        )
        if orders[0].quantity < position.size:
            ratio = to_f(orders[0].quantity / position.size, f"%.{decimal_places}f")
        else:
            ratio = 1
        fee_rate = self.maker if orders[0].stop_price == 0 else self.taker
        working_orders = orders
        if opposite_result:
            if (
                position.kind == "long"
                and opposite_result[0].entry_price < orders[0].entry_price
            ):
                if opposite_result[0].entry_price > position.entry_price:
                    working_orders = opposite_result[:1]
            if (
                position.kind == "short"
                and opposite_result[0].entry_price > orders[0].entry_price
            ):
                if opposite_result[0].entry_price < position.entry_price:
                    working_orders = opposite_result[:1]
        return {
            "position": {"entry": position.entry_price, "size": position.size},
            "tp": {
                "entry": statistics.mean([x.entry_price for x in working_orders]),
                "size": statistics.mean([x.quantity for x in working_orders]),
            },
            "pnl": to_f(pnl * ratio, f"%.{places}f"),
            "remaining_size": to_f((1 - ratio) * position.size, f"%.{decimal_places}f"),
            "fees": to_f(
                (working_orders[0].entry_price * working_orders[0].quantity) * fee_rate,
                f"%.{decimal_places}f",
            ),
        }


@dataclass
class Position:
    payload: PositionsDict
    closed_orders: Optional[ClosedOrdersDict]

    def __post_init__(self):
        self.long: PositionKlass = PositionKlass(**self.payload["long"])
        self.short: PositionKlass = PositionKlass(**self.payload["short"])
        self.both: Optional[PositionKlass] = (
            PositionKlass(**self.payload["both"]) if self.payload["both"] else None
        )
        self.closed_long = None
        self.closed_short = None
        if (
            self.closed_orders
            and self.closed_orders["long"]
            and self.closed_orders["short"]
        ):
            self.closed_long: ClosedOrder = ClosedOrder(**self.closed_orders["long"])
            self.closed_short: ClosedOrder = ClosedOrder(**self.closed_orders["short"])


@dataclass
class OrderControl:
    order_lists: List[OrderDict]
    positions: Optional[Position]
    maker_rate = 0.0002
    taker_rate = 0.0005

    def __post_init__(self):
        if self.positions:
            self.orders: List[Order] = [Order(**x) for x in self.order_lists]
            self.stats: OrderStats = OrderStats(self.maker_rate, self.taker_rate)
        else:
            self.orders:List[MarginOrder] = [MarginOrder(**x) for x in self.order_lists]

    def get_orders(self, kind: PositionKind, side: Literal["buy", "sell"]):
        def condition(u):
            if hasattr(u, "positionSide"):
                return u.positionSide.lower() == kind
            return True
        return [
            x
            for x in self.orders
            if x.side.lower() == side and condition(x)
        ]

    def get_open_orders(
        self,
        kind: PositionKind,
        stats=False,
        balance=0,
    ):
        side = {
            "long": "buy",
            "short": "sell",
        }
        result = [x for x in self.get_orders(kind, side[kind])]
        result = sorted(result, key=lambda x: x.entry_price)
        if kind == "long":
            result = sorted(result, key=lambda x: x.entry_price, reverse=True)

        if stats:
            position: Optional[PositionKlass] = (
                getattr(self.positions, kind) if self.positions else None
            )
            return self.stats.open_orders(result, position, balance)
        return result

    def get_tp_orders(self, kind: PositionKind, stats=False, eager=True):
        side = {
            "long": "sell",
            "short": "buy",
        }
        result = [x for x in self.get_orders(kind, side[kind]) if x.stop_price == 0]
        opposite_kind = "long" if kind == "short" else "short"
        opposite_side = "sell" if opposite_kind == "short" else "buy"
        opposite_result = [
            x
            for x in self.get_orders(opposite_kind, opposite_side)
            if x.stop_price == 0
        ]
        if stats and result:
            position: Optional[PositionKlass] = (
                getattr(self.positions, kind) if self.positions else None
            )
            if position:
                result = sorted(result, key=lambda x: x.entry_price)
                opposite_result = sorted(
                    opposite_result, key=lambda x: x.entry_price, reverse=True
                )
                if kind == "long":
                    result = sorted(result, key=lambda x: x.entry_price, reverse=True)
                    opposite_result = sorted(
                        opposite_result, key=lambda x: x.entry_price
                    )
                return self.stats.close_orders(
                    result, position, opposite_result=opposite_result if eager else None
                )
        return result

    def get_sl_orders(self, kind: PositionKind, stats=False):
        side = {
            "long": "sell",
            "short": "buy",
        }
        result = [x for x in self.get_orders(kind, side[kind]) if x.stop_price > 0]
        if stats and result:
            position: Optional[PositionKlass] = (
                getattr(self.positions, kind) if self.positions else None
            )
            if position:
                result = sorted(result, key=lambda x: x.entry_price)
                if kind == "long":
                    result = sorted(result, key=lambda x: x.entry_price, reverse=True)
                return self.stats.close_orders(result, position)
        return result

    def get_re_entry_order(self, kind:PositionKind):
        position = getattr(self.positions, kind) if self.positions else None
        if position and position.size > 0:
            def condition(x):
                if kind == 'long':
                    return position.entry_price <= x.entry_price
                return position.entry_price >= x.entry_price
            orders = [x for x in self.get_open_orders(kind) if condition(x)]
            if orders:
                return orders[0]



@dataclass
@inject_fields(AccountBalanceDict)
class AccountBalance:
    pass


class Exchange:
    payload: ExchangeInfo

    def __post_init__(self):
        self.account_balance: List[AccountBalance] = [
            AccountBalance(**x) for x in self.payload["account_balance"]
        ]
        self.open_orders: List[Order] = [
            Order(**x) for x in self.payload["open_orders"]
        ]
        self.open_orders[0].__annotations__
        self.position: Position = Position(
            long=PositionKlass(**self.payload["position"]["long"]),
            short=PositionKlass(**self.payload["position"]["short"]),
            both=PositionKlass(**self.payload["position"]["both"]),
        )
        self.last_order: float = self.payload["last_order"]
