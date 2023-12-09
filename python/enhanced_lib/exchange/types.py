from dataclasses import dataclass
from typing import List, Literal, Optional, TypedDict

from ..calculations.utils import determine_pnl, get_decimal_places, to_f


def inject_fields(parent):
    def doit(cls):
        cls.__annotations__ = parent.__annotations__ | cls.__annotations__
        return cls

    return doit


PositionKind = Literal["long", "short"]


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
    orderId: int
    symbol: str
    status: str
    clientOrderId: str
    price: str
    avgPrice: str
    origQty: str
    executedQty: str
    cumQuote: str
    timeInForce: str
    type: str
    reduceOnly: bool
    closePosition: bool
    side: str
    positionSide: str
    stopPrice: str
    workingType: str
    priceProtect: bool
    origType: str
    priceMatch: str
    selfTradePreventionMode: str
    goodTillDate: int
    time: int
    updateTime: int


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
@inject_fields(PositionDict)
class PositionKlass:
    @property
    def size(self):
        return abs(self.positionAmt)

    @property
    def entry_price(self):
        return self.entryPrice

    @property
    def kind(self) -> PositionKind:
        return self.positionSide.lower()


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

    def open_orders(
        self, orders: List[Order], position: Optional[PositionKlass]
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

        avg_entry = total_notional_value / size
        last_order = orders[-1].entry_price if orders else None
        fees = sum((x.quantity * x.entry_price) * self.maker for x in orders)
        return {
            "size": to_f(size, f"%.{decimal_places}f"),
            "count": len(orders),
            "avg": to_f(avg_entry, f"%.{places}f"),
            "last": last_order,
            "fees": to_f(fees, f"%.{places}f"),
        }

    def close_orders(
        self, orders: List[Order], position: PositionKlass
    ) -> CloseOrderStat:
        def get_key():
            if position:
                return position.entry_price
            return orders[0].price if orders else 0

        places = get_decimal_places(str(get_key()))
        decimal_places = get_decimal_places(str(orders[0].origQty)) if orders else 0
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
        return {
            "pnl": to_f(pnl * ratio, f"%.{places}f"),
            "remaining_size": to_f((1 - ratio) * position.size, f"%.{decimal_places}f"),
            "fees": to_f(
                (orders[0].entry_price * orders[0].quantity) * fee_rate,
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
        if self.closed_orders:
            self.closed_long: ClosedOrder = ClosedOrder(**self.closed_orders["long"])
            self.closed_short: ClosedOrder = ClosedOrder(**self.closed_orders["short"])


@dataclass
class OrderControl:
    order_lists: List[OrderDict]
    positions: Optional[Position]
    maker_rate = 0.0002
    taker_rate = 0.0005

    def __post_init__(self):
        self.orders: List[Order] = [Order(**x) for x in self.order_lists]
        self.stats: OrderStats = OrderStats(self.maker_rate, self.taker_rate)

    def get_orders(self, kind: PositionKind, side: Literal["buy", "sell"]):
        return [
            x
            for x in self.orders
            if x.side.lower() == side and x.positionSide.lower() == kind
        ]

    def get_open_orders(
        self,
        kind: PositionKind,
        stats=False,
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
            return self.stats.open_orders(result, position)
        return result

    def get_tp_orders(self, kind: PositionKind, stats=False):
        side = {
            "long": "sell",
            "short": "buy",
        }
        result = [x for x in self.get_orders(kind, side[kind]) if x.stop_price == 0]
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
