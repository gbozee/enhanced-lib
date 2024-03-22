from dataclasses import dataclass
import typing

from . import hedge, utils

empty_position = {
    "entry": 0,
    "size": 0,
}


class PositionControl:
    def __init__(self, avg_entry=None, avg_size=None, **kwargs):
        self.avg_entry = avg_entry
        self.avg_size = avg_size
        self.__dict__.update(kwargs)
        if kwargs.get("entry") and kwargs.get("stop"):
            self.kind = self.get_kind(kwargs["entry"], kwargs["stop"])
        else:
            self.kind = kwargs.get("kind") or "long"

    def get_kind(self, entry, stop):
        if entry > stop:
            return "long"
        elif entry < stop:
            return "short"

    @property
    def position(self):
        return {
            "entry": self.avg_entry,
            "size": self.avg_size,
        }

    def determine_liquidation(self, balance: float, symbol="BTCUSDT"):
        long_position = self.position if self.kind == "long" else empty_position
        short_position = self.position if self.kind == "short" else empty_position
        result = hedge.determine_liquidation(
            balance=balance,
            long_position=long_position,
            short_position=short_position,
            symbol=symbol,
        )
        return utils.to_f(result["liquidation"], "%.1f")

    def determine_new_size_or_pnl(self, sell_price: float, loss=None):
        if loss:
            size = utils.determine_amount_to_sell(
                entry=self.position["entry"],
                quantity=self.position["size"],
                sell_price=sell_price,
                pnl=loss,
                places="%.3f",
                _kind=self.kind,
            )
            new_size = self.position["size"] - size
            return utils.to_f(new_size, "%.3f")
        pnl = utils.determine_pnl(
            self.position["entry"],
            sell_price,
            self.position["size"],
            kind=self.kind,
        )
        return utils.to_f(pnl, "%.3f")

    def can_place_opposite_trade(
        self,
        balance: float,
        entry_price: float,
        quantity: float,
        leverage=125,
    ):
        current_position = self.position["size"] * self.position["entry"]
        current_loss = self.determine_new_size_or_pnl(entry_price)
        new_balance = balance + current_loss
        new_max_position = new_balance * leverage
        remaining = new_max_position - current_position
        new_trade_position = quantity * entry_price
        remaining = remaining - new_trade_position
        return {
            "remaining": utils.to_f(remaining, "%.1f"),
            "can_trade": remaining > 0,
            "balance": utils.to_f(remaining / leverage, "%.3f"),
        }

    def increase_position(self, entry_price: float, quantity: float):
        new_entry = utils.determine_avg(
            [
                {
                    "price": self.position["entry"],
                    "quantity": self.position["size"],
                },
                {
                    "price": entry_price,
                    "quantity": quantity,
                },
            ]
        )
        return new_entry
        # self.avg_size = new_size
        # self.avg_entry = new_entry

    def simulate_liquidation_reduction(self, balance: float, short_entries: list):
        for i in short_entries:
            if self.can_place_opposite_trade(balance, i["avg_entry"], i["avg_size"])[
                "can_trade"
            ]:
                short_instance = PositionControl(
                    avg_entry=i["avg_entry"],
                    avg_size=i["avg_size"],
                    kind="short" if self.kind == "long" else "long",
                )
                sell_price = i["entry"]
                pnl = short_instance.determine_new_size_or_pnl(sell_price)
                reduced_size = self.determine_new_size_or_pnl(sell_price, loss=pnl)
                self.avg_size = reduced_size
                liquidation_price = self.determine_liquidation(balance)
                print(
                    {
                        "sell_price": sell_price,
                        "size": reduced_size,
                        "liquidation_price": liquidation_price,
                        "unrealized_pnl": self.determine_new_size_or_pnl(sell_price),
                    }
                )
                if reduced_size < 0:
                    break


class PositionType(typing.TypedDict):
    entry: float
    size: float


class AccountPosition(typing.TypedDict):
    long: PositionType
    short: PositionType


@dataclass
class AccountClient:
    owner: str
    long_position: typing.Optional[PositionControl] = None
    short_position: typing.Optional[PositionControl] = None
    last_updated: typing.Optional[str] = None

    def update_positions(self, positions: AccountPosition):
        self.long_position = PositionControl(
            avg_entry=positions["long"]["entry"],
            avg_size=positions["long"]["size"],
            kind="long",
        )
        self.short_position = PositionControl(
            avg_entry=positions["short"]["entry"],
            avg_size=positions["short"]["size"],
            kind="short",
        )
        self.last_updated = utils.get_current_time()
