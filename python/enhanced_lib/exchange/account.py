from typing import Optional, Any


from .types import (
    ProfileDict,
)


class Account:
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
