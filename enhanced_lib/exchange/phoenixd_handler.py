from dataclasses import dataclass
import requests
import typing
import json
from requests.auth import HTTPBasicAuth


class ChannelDetailsType(typing.TypedDict):
    channel_id: str
    fee_rate: int
    address: str


class CreateInvoiceType(typing.TypedDict):
    amount: int
    description: str
    external_id: str
    webhook_url: str


class PayInvoiceType(typing.TypedDict):
    amount: int
    invoice: str
    message: str


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

    def lnurl_pay(self, lnurl: str, amount_sat: typing.Optional[int] = None):
        # Remove 'lightning:' prefix if present
        if lnurl.lower().startswith("lightning:"):
            lnurl = lnurl[10:]

        payload = {"lnurl": lnurl}
        if amount_sat:
            payload["amountSat"] = amount_sat

        return self.api_call("post", "/lnurlpay", payload)

    def lnurl_auth(self, lnurl: str):
        # Remove 'lightning:' prefix if present
        if lnurl.lower().startswith("lightning:"):
            lnurl = lnurl[10:]

        payload = {"lnurl": lnurl}
        return self.api_call("post", "/lnurlauth", payload)

    def create_invoice(self, payload: CreateInvoiceType):
        data = {
            "amountSat": payload["amount_sat"],
            "description": payload["description"],
        }
        if payload.get("external_id"):
            data["externalId"] = payload["external_id"]
        if payload.get("webhook_url"):
            data["webhookUrl"] = payload["webhook_url"]
        return self.api_call("post", "/createinvoice", data)

    def get_offer(self):
        return self.api_call("get", "/getoffer")

    def get_lightning_address(self):
        return self.api_call("get", "/getlnaddress")

    def pay_invoice(self, payload: PayInvoiceType):
        data = {"amountSat": payload["amount"], "invoice": payload["invoice"]}
        return self.api_call("post", "/payinvoice", data)
    
    def pay_offer(self, payload:PayInvoiceType):
        data = {'amountSat':payload['amount'],'offer':payload['invoice']}
        if payload.get('message'):
            data['message'] = payload['message']
            
        return self.api_call('post','/payoffer',data)
