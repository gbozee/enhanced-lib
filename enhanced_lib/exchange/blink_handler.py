from dataclasses import dataclass
import requests
import typing


class WalletType(typing.TypedDict):
    balance: int
    walletCurrency: str
    id: str


class InvoiceType(typing.TypedDict):
    paymentRequest: str
    paymentHash: str
    paymentSecret: str
    satoshis: int


@dataclass
class BlinkWallet:
    api_key: str
    base_url = "https://api.blink.sv/graphql"

    def api_call(self, query: str, variables=None):
        headers = {"Accept": "application/json", "X-API-KEY": self.api_key}
        result = requests.post(
            self.base_url,
            json={"query": query, "variables": variables or {}},
            headers=headers,
        )
        if result.status_code < 400:
            return result.json()

    def get_email(self):
        query = """
        query {
            me {
                email{
                    address
                }
            }
        }
        """
        result = self.api_call(query)
        return result["data"]["me"]["email"]

    def get_wallet(self, wallet_type: typing.Literal["btc", "usd"]) -> WalletType:
        query = """
        query {
            me {
              	defaultAccount {
                    wallets {
                        balance
                        walletCurrency
                        id
                    }
                }
            }
        }
        """
        result = self.api_call(query)
        response = result["data"]["me"]["defaultAccount"]["wallets"]
        return [x for x in response if x["walletCurrency"].lower() == wallet_type][0]

    def generate_invoice(
        self, wallet_type: typing.Literal["btc", "usd"], amount: float
    ):
        wallet = self.get_wallet(wallet_type)
        if wallet["walletCurrency"].lower() == "usd":
            query = """
            mutation LnInvoiceCreate($input: LnUsdInvoiceCreateInput!) {
                lnUsdInvoiceCreate(input: $input) {
                    invoice {
                        paymentRequest
                        paymentHash
                        paymentSecret
                        satoshis
                    }
                    errors {
                        message
                    }
                }
            }
        """
        else:
            query = """
            mutation LnInvoiceCreate($input: LnInvoiceCreateInput!) {
                lnInvoiceCreate(input: $input) {
                    invoice {
                        paymentRequest
                        paymentHash
                        paymentSecret
                        satoshis
                    }
                    errors {
                        message
                    }
                }
            }
        """
        variables = {
            "input": {
                "amount": amount,
                "walletId": wallet["id"],
            }
        }
        result = self.api_call(query, variables)
        key = (
            "lnInvoiceCreate"
            if wallet["walletCurrency"].lower() == "btc"
            else "lnUsdInvoiceCreate"
        )
        return result["data"][key]["invoice"]

    def get_latest_price(self):
        query = """
        query btcPriceList($range: PriceGraphRange!)  {
            btcPriceList(range: $range) {
                timestamp
                price {
                    base
                    offset
                    currencyUnit
                    formattedAmount
                }
            }
        }
        """
        variables = {"range": "ONE_DAY"}
        result = self.api_call(query, variables)
        return (
            float(result["data"]["btcPriceList"][-1]["price"]["formattedAmount"]) / 100
        )

    def get_invoice_amount(
        self,
        from_wallet: typing.Literal["btc", "usd"],
        amount: int,
    ):
        current_price = self.get_latest_price()
        if from_wallet == "btc":
            return int(current_price * amount * 100 / 100_000_000)
        return int(amount * 100_000_000 / (current_price * 100))

    def swap(self, from_wallet: typing.Literal["btc", "usd"], btc_fee=100, usd_fee=10):
        btc_wallet = self.get_wallet("btc")
        usd_wallet = self.get_wallet("usd")
        amount = 0
        if from_wallet == btc_wallet["walletCurrency"].lower():
            if btc_wallet["balance"] - btc_fee > 0:
                amount = self.get_invoice_amount("btc", btc_wallet["balance"] - btc_fee)
        else:
            if usd_wallet["balance"] - usd_fee > 0:
                amount = self.get_invoice_amount("usd", usd_wallet["balance"] - usd_fee)
        if amount:
            destination = "usd" if from_wallet == "btc" else "btc"
            invoice = self.generate_invoice(destination, amount)
            return self.pay_invoice(from_wallet, invoice["paymentRequest"])
        else:
            return {
                'btc': btc_wallet['balance'] - btc_fee,
                'usd': usd_wallet['balance'] - usd_fee
            }

    def pay_invoice(self, wallet_type: typing.Literal["btc", "usd"], invoice: str):
        wallet = self.get_wallet(wallet_type)
        query = """
            mutation LnInvoicePaymentSend($input: LnInvoicePaymentInput!) {
                lnInvoicePaymentSend(input: $input) {
                    status
                    errors {
                    message
                    path
                    code
                    }
                }
            }
        """
        variables = {
            "input": {
                "paymentRequest": invoice,
                "walletId": wallet["id"],
            }
        }
        result = self.api_call(query, variables)
        return result["data"]["lnInvoicePaymentSend"]["status"]
