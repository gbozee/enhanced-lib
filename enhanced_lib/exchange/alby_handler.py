import requests
from dataclasses import dataclass
from typing import TypedDict


class InvoiceType(TypedDict):
    description_hash: str
    amount: int
    memo: str
    description: str
    comment: str
    payer_name: str
    payer_email: str
    payer_pubkey: str
    metadata: dict


class QType(TypedDict):
    since: str
    created_at_lt: int
    created_at_gt: int
    before: str


class InvoiceHistoryType(TypedDict):
    q: QType
    page: int
    items: int


class LNURLRequestType:
    ln: str
    amount: int
    comment: str


@dataclass
class AlbyWallet:
    api_key: str
    base_url = "https://api.getalby.com"

    def _api_call(self, path: str, method: str = "GET", params: dict = None):
        url = f"{self.base_url}{path}"
        options = {
            "GET": requests.get,
            "POST": requests.post,
            "DELETE": requests.delete,
        }
        func = options.get(method)
        options = {
            "GET": {"params": params},
            "POST": {"json": params},
            "DELETE": {"params": params},
        }
        kwargs = options.get(method)
        if func and kwargs:
            result = func(
                url, headers={"Authorization": f"Bearer {self.api_key}"}, **kwargs
            )
            if result.status < 400:
                return result.json()
        return None

    def get_balance(self):
        return self._api_call("/balance")

    def create_invoice(self, params: InvoiceType):
        return self._api_call("/invoices", "POST", params)

    def get_invoices(
        self,
        payment_hash: str = None,
        incoming=None,
        outgoing=None,
        filters: InvoiceHistoryType = None,
    ):
        url = "/invoices"
        if incoming:
            url = "/invoices/incoming"
        if outgoing:
            url = "/invoices/outgoing"
        if payment_hash:
            url = f"/invoices/{payment_hash}"

        return self._api_call(url, "GET", params=filters)

    def decode_invoice(self, invoice: str):
        return self._api_call(f"/decode/bolt11/{invoice}")

    def pay_invoice(self, invoice: str):
        return self._api_call("/payments/bolt11", "POST", {"invoice": invoice})

    def create_webhook(self, url: str, incoming=True, outgoing=True):
        filter_types = []
        if incoming:
            filter_types.append("invoice.incoming.settled")
        if outgoing:
            filter_types.append("invoice.outgoing.settled")
        return self._api_call(
            "/webhook_endpoints", "POST", {"url": url, "filter_types": filter_types}
        )

    def get_webhooks(self, id: str):
        return self._api_call(f"/webhook_endpoints/{id}")

    def delete_webhook(self, id: str):
        return self._api_call(f"/webhook_endpoints/{id}", "DELETE")

    def lightning_address_detail(self, address: str):
        return self._api_call(
            "/lnurl/lightning-address-details", "GET", {"ln": address}
        )

    def request_invoice(self, payload: LNURLRequestType):
        return self._api_call("/lnurl/generate-invoice", "GET", payload)
