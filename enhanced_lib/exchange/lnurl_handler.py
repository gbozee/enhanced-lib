from dataclasses import dataclass
import asyncio
from typing import Any, Optional,TypedDict
import lnurl
import json
import hashlib
import math
import logging
from enhanced_lib.exchange.client import TradeClient, loop_helper
from enhanced_lib.calculations.utils import to_f
import secrets

MAX_CORN = 0.01 * 100_000_000


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)


class Invoice(TypedDict):
    currency: str
    amount_msat: int
    payment_hash: str
    payment_secret: str
    description: str
    payee: str
    signature: dict
    features: dict
    date: int


class FundSource:
    async def get_owner(self, owner: str):
        raise NotImplementedError

    async def deposit_funds(self, owner: str, amount: int) -> str:
        """amount in sats"""
        raise NotImplementedError

    def withdraw_funds(self, owner: str, amount: int, invoice: str, symbol="BTCUSDC"):
        raise NotImplementedError

    def decode_invoice(self, invoice: str) -> Invoice:
        raise NotImplementedError


@dataclass
class ExchangeFundingSource(FundSource):
    client: TradeClient

    async def deposit_funds(self, owner: str, amount: int) -> str:
        """amount is in sats but exchange expects BTC instead

        Args:
            owner (str): _description_
            amount (int): _description_

        Returns:
            str: lightning invoice
        """
        result = await loop_helper(
            lambda: self.client.lightning_deposit(
                {"owner": owner, "amount": to_f(amount / 100_000_000, "%.8f")}
            )
        )
        if result:
            return result["address"]

        def withdraw_funds(
            self,
            owner: str,
            amount: int,
            invoice: str,
            symbol="BTCUSDC",
        ):
            amount_in_btc = amount / 100_000_000
            result = self.client.lightning_withdraw(
                {
                    "owner": owner,
                    "symbol": symbol,
                    "amount": amount_in_btc,
                    "invoice": invoice,
                },
            )
            return result

    def decode_invoice(self, invoice: str):
        return self.client.lightning_decode({"invoice": invoice})


@dataclass
class LnurlHandler:
    domain: str
    service: FundSource
    min_sats_receivable: Optional[int] = 1
    max_sats_receivable: Optional[int] = MAX_CORN
    username: Optional[str] = ""
    lnurl_address: Optional[str] = ""

    async def get_address(self, owner: str):
        exists = await self.service.get_owner(owner=owner)
        if exists:
            self.username = owner
            self.lnurl_address = f"{owner}@{self.domain}"

    @property
    def base_url(self):
        return f"https://{self.domain}"

    def lnurl_address_encoded(self) -> lnurl.Lnurl:
        if self.username:
            return lnurl.encode(f"{self.base_url}/lnurlp/{self.username}")

    def metadata_for_payrequest(self) -> str:
        return json.dumps(
            [
                ["text/plain", f"Zap {self.username} some sats"],
                ["text/identifier", self.lnurl_address],
                # ["image/jpeg;base64", "TODO optional"],
            ]
        )

    def metadata_hash(self) -> str:
        return hashlib.sha256(
            self.metadata_for_payrequest().encode("UTF-8")
        ).hexdigest()

    async def lnurl_pay_request_lud16(self, ln_address: str) -> lnurl.LnurlPayResponse:
        """
        Implements [LUD-16](https://github.com/lnurl/luds/blob/luds/16.md) `payRequest`
        initial step, using human-readable `username@host` addresses.
        path="/lnurlp/{username}", method="GET">
        path="/.well-known/lnurlp/{username}",
        """
        username = parse_username(ln_address)
        await self.get_address(username)
        if not self.lnurl_address:
            return None

        logger.info(
            "LUD-16 payRequest for username='{username}'".format(username=username)
        )
        return lnurl.LnurlPayResponse.parse_obj(
            dict(
                callback=f"{self.base_url}/lnurlp/{username}/callback",
                minSendable=self.min_sats_receivable * 1000,
                maxSendable=self.max_sats_receivable * 1000,
                metadata=self.metadata_for_payrequest(),
            )
        )

    async def lnurl_pay_request_callback_lud06(
        self,
        username: str,
        amount: int,
        tag="message",
        message=lambda x: f"Thanks for zapping {x}",
    ) -> lnurl.LnurlPayActionResponse:
        """path="/lnurlp/{username}/callback","""
        await self.get_address(parse_username(username))
        if not self.lnurl_address:
            return None
        username = self.username

        # TODO check compatibility of conversion to sats, some wallets
        # may not like the invoice amount not matching?
        amount_sat = math.ceil(amount / 1000)
        logger.info(
            "LUD-06 payRequestCallback for username='{username}' sat={amount_sat} (mSat={amount})".format(
                username=username,
                amount_sat=amount_sat,
                amount=amount,
            )
        )

        if amount_sat < self.min_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-low amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        if amount_sat > self.max_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-high amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        invoice = await self.service.deposit_funds(username, amount_sat)
        if not invoice:
            logger.warning("Failed to generate lightning invoice")
            return None

        return lnurl.LnurlPayActionResponse.parse_obj(
            dict(
                pr=invoice,
                success_action={
                    "tag": tag,
                    "message": message(username),
                },
                routes=[],
            )
        )

    def lnurl_withdraw_lud03(
        self,
        description="Initiating withdrawal",
        callback_url=None,
        username=None,
    ):
        maximum_amount = self.service.get_account_balance()
        minimum_amount = 0
        callback = callback_url or f"{self.base_url}/lnurlw/{username}/callback"
        k1 = secrets.token_hex(32)
        payload = lnurl.LnurlWithdrawResponse.parse_obj(
            {
                "callback": callback,
                "k1": k1,
                "defaultDescription": description,
                "minWithdrawable": minimum_amount,
                "maxWithdrawable": maximum_amount,
            }
        )
        return payload

    def initiate_withdrawal(self, owner: str, invoice: str, fee=100):
        fee_msats = fee * 1000
        details = self.service.decode_invoice(invoice)
        invoice_amount = details["amount_msat"]
        total_amount = invoice_amount + fee_msats
        amount_in_sats = math.ceil(total_amount / 1000)
        return self.service.withdraw_funds(owner, amount_in_sats, invoice)


def parse_username(email_or_name):
    username = email_or_name.split("@")[0]
    return username
