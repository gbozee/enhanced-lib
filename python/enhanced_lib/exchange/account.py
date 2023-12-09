from .client import (
    TradeClient,
    loop_helper,
    Constants,
    GetExchangeInfoType,
    CreateSpotProfileType,
    CandleStickParamType,
)
from typing import Union, Optional


from .types import (
    ProfileDict,
)

class Account:
    def __init__(self, owner: str, config_owner: str = None, base_url=""):
        self.owner = owner
        self.config_owner = config_owner or owner
        self.general_config = {
            "position_information": {},
            "config": {},
        }
        self.base_url = base_url

    async def client_helper(
        self,
        method: str,
        params: Union[GetExchangeInfoType, CreateSpotProfileType, CandleStickParamType],
    ):
        client = TradeClient(self.base_url)
        return await loop_helper(lambda: getattr(client, method)(params))

    async def fetch_config(self, symbol: str):
        result = await self.client_helper(
            Constants.GET_SPOT_VALUE,
            {"owner": self.config_owner, "symbol": symbol, "spot_symbol": symbol},
        )
        self.general_config["config"][symbol.upper()] = result
        return result

    async def update_config_fields(self, symbol: str, fields: ProfileDict):
        config = self.general_config["config"].get(symbol.upper()) or {}
        config.update(fields)
        await self.save_config(symbol, config)

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

    async def fetch_latest(self, symbol: str, save=True):
        result = await self.client_helper(
            Constants.EXCHANGE_INFO,
            {"owner": self.owner, "symbol": symbol, "future_only": True, "save": save},
        )
        print("result", result)
        self.general_config["position_information"][symbol.upper()] = {
            "payload": result
        }
        return result

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
