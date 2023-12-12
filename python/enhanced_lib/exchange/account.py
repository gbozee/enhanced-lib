import asyncio
from typing import Optional, Any, Literal, Union
from .client import (
    TradeClient,
    GetExchangeInfoType,
    CreateSpotProfileType,
    CandleStickParamType,
    loop_helper,
    Constants,
)

from .types import (
    ProfileDict,
)


class AccountKeys:
    POSITION_INFORMATION = "position_information"
    CONFIG = "config"
    FUTURE_TRADES = "future_trades"


class BaseAccount:
    def __init__(self, owner: str, config_owner: str = None, client: Any = None):
        self.owner = owner
        self.config_owner = config_owner or owner
        self.general_config = {
            "position_information": {},
            "config": {},
        }

    async def fetch_config(self, symbol: str):
        raise NotImplementedError

    async def update_config_fields(self, symbol: str, fields: ProfileDict):
        config = self.general_config["config"].get(symbol.upper()) or {}
        config.update(fields)
        await self.save_config(symbol, config)

    async def update_config_resistance(
        self, symbol: str, resistance: Optional[float] = None
    ):
        raise NotImplementedError

    async def fetch_latest(self, symbol: str, save=True):
        raise NotImplementedError

    async def save_config(self, symbol: str, profile: ProfileDict):
        raise NotImplementedError


class Account(BaseAccount):
    def __init__(self, base_url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url

    async def client_helper(
        self,
        method: str,
        params: Union[GetExchangeInfoType, CreateSpotProfileType, CandleStickParamType],
    ):
        client = TradeClient(self.base_url)
        return await loop_helper(lambda: getattr(client, method)(params))

    def update_general_config(self, key: str, value: dict):
        self.general_config[key] = value

    async def fetch_config(self, symbol: str):
        result = await self.client_helper(
            Constants.GET_SPOT_VALUE,
            {"owner": self.config_owner, "symbol": symbol, "spot_symbol": symbol},
        )
        self.general_config["config"][symbol.upper()] = result
        return result

    async def update_config_resistance(
        self, symbol: str, resistance: Optional[float] = None
    ):
        _resistance = resistance
        if not _resistance:
            result = await self.client_helper(
                Constants.GET_CANDLESTICKS,
                {
                    "symbol": symbol,
                    "interval": "monthly",
                    "count": 1,
                },
            )
            if result:
                _resistance = max([x["high"] for x in result])
        if _resistance:
            await self.update_config_fields(symbol, {"resistance": _resistance})

    async def _fetch_latest(self, symbol: str, save=True):
        result = await self.client_helper(
            Constants.EXCHANGE_INFO,
            {"owner": self.owner, "symbol": symbol, "future_only": True, "save": save},
        )
        self.general_config[AccountKeys.POSITION_INFORMATION][symbol.upper()] = {
            "payload": result
        }
        return result

    async def fetch_latest(self, symbol: str, save=True):
        await asyncio.gather(
            self._fetch_latest(symbol, save),
            self.fetch_config(symbol),
        )

    async def save_config(self, symbol: str, profile: ProfileDict):
        result = await self.client_helper(
            Constants.SAVE_SPOT_PROFILE,
            {
                "owner": self.config_owner,
                "profile": profile,
                "symbol": symbol,
                "spot_symbol": symbol,
            },
        )
        self.general_config["config"][symbol.upper()] = result

    async def cancel_orders(
        self,
        symbol: str,
        kind: Literal["long", "short"],
        order_ids: list = None,
        cancel_all=True,
    ):
        orders = order_ids or []
        action = "close_open_orders"
        kwargs = {"owner": self.owner, "symbol": symbol, "order_ids": orders}
        if cancel_all:
            action = Constants.PLACE_SIGNAL_ORDERS
            kwargs = {
                "symbol": symbol,
                "orders": [
                    {
                        "entry": 36721,
                        "quantity": 0.006,
                        "sell_price": 35990.7,
                        "stop": 36964.5,
                    },
                ],
                "kind": kind,
                "sub_accounts": self.owner,
                "cancel": True,
            }
        return await self.client_helper(action, kwargs)

    async def save_trades(self, symbol: str, trades: dict):
        return await self.client_helper(
            "trade_actions",
            {
                "owner": self.owner,
                "symbol": symbol,
                "action": "save",
                "trades": trades,
            },
        )
        
    async def get_trades(self, symbol: str):
        return await self.client_helper(
            "trade_actions",
            {
                "owner": self.owner,
                "symbol": symbol,
                "action": "get",
            },
        )

    async def place_orders(
        self, symbol: str, kind: Literal["long", "short"], orders: list
    ):
        await self.cancel_orders(symbol, kind)
        return await self.client_helper(
            "place_signal_orders",
            {
                "symbol": symbol,
                "orders": orders,
                "kind": kind,
                "sub_accounts": self.owner,
            },
        )

    async def update_tp_sl(
        self, symbol: str, kind: Literal["long", "short"], price: float = None
    ):
        opposite_kind = kind
        # if type == "stop-loss":
        #     opposite_kind = "short" if kind == "long" else "long"
        if price:
            return await self.client_helper(
                "update_close_prices",
                {
                    "orders": [{"sell_price": price}],
                    "kind": opposite_kind,
                    "symbol": symbol,
                    "sub_accounts": [self.owner],
                },
            )
        # if type == "stop-loss" and result:
        #     return await self.client_helper(
        #         "reduce_position",
        #         {
        #             "owner": self.owner,
        #             "kind": kind,
        #             "symbol": symbol,
        #         },
        #     )
        # if type == "stop-loss":
        #     raise Exception("Failed to reduce position")
