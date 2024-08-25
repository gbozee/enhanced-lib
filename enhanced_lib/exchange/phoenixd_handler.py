from dataclasses import dataclass
import requests
import typing
import json
from requests.auth import HTTPBasicAuth


class ChannelDetailsType(typing.TypedDict):
    channel_id: str
    fee_rate: int
    address: str


@dataclass
class PhoenixdHandler:
    base_url: str
    api_key: str

    def api_call(self, method: str, path: str, data: dict = None) -> dict:
        headers = {"Content-Type": "application/json"}
        url = f"{self.base_url}{path}"

        if method.lower() == "get":
            response = requests.get(
                url, auth=HTTPBasicAuth("_", self.api_key), headers=headers, params=data
            )
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    def node_info(self):
        return self.api_call("get", "/getinfo")

    def balance(self):
        return self.api_call("get", "/getbalance")

    def list_channels(self):
        return self.api_call("get", "/listchannels")

    def close_channel(self, channel_details: ChannelDetailsType):
        return self.api_call(
            "post",
            "/closechannel",
            {
                "channelId": channel_details["channel_id"],
                "feerateSatByte": channel_details["fee_rate"],
                "address": channel_details["address"],
            },
        )

    def decode_invoice(self, invoice: str):
        return self.api_call("post", "/decodeinvoice", {"invoice": invoice})

    def decode_offer(self, offer: str):
        return self.api_call("post", "/decodeoffer", {"offer": offer})

    def lnurl_pay(self, lnurl: str, amount_sat: int):
        return self.api_call(
            "post",
            "/lnurlpay",
            {
                "lnurl": lnurl,
                "amountSat": amount_sat
            }
        )
