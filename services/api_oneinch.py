from python_1inch import OneInchExchange

from .market_base import Market, Coin, Cup, CupEntry


class Oneinch(Market):

    def __init__(self) -> None:
        super().__init__('1inch')
        self.exchange = OneInchExchange(address=None)
        self.exchange.get_tokens()

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_name(self)}/{base_coin.get_name()}'

    def _get_price_quote(
            self, from_token_symbol: str,
            to_token_symbol: str,
            amount: int) -> tuple:
        quote_dict = self.exchange.get_quote(
            from_token_symbol=from_token_symbol,
            to_token_symbol=to_token_symbol,
            amount=amount
        )
        toTokenAmount = self.exchange.convert_amount_to_decimal(
            token_symbol=to_token_symbol,
            amount=quote_dict['toTokenAmount']
        )
        fromTokenAmount = self.exchange.convert_amount_to_decimal(
            token_symbol=from_token_symbol,
            amount=quote_dict['fromTokenAmount']
        )
        return (fromTokenAmount, toTokenAmount)

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        target_base_amount = 510
        base_amount, coin_amount = self._get_price_quote(
            from_token_symbol=base_coin.get_upper_name(),
            to_token_symbol=coin.get_upper_name(),
            amount=target_base_amount
        )
        ask_price = base_amount / coin_amount
        asks = [CupEntry(float(ask_price), float(coin_amount)), ]

        coin_amount_int = int(coin_amount)
        coin_amount, base_amount = self._get_price_quote(
            from_token_symbol=coin.get_upper_name(),
            to_token_symbol=base_coin.get_upper_name(),
            amount=coin_amount_int
        )
        bid_price = base_amount / coin_amount
        bids = [CupEntry(float(bid_price), float(coin_amount)), ]
        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = f'{coin.get_upper_name()}/{base_coin.get_upper_name()}'
        return f'https://www.app.1inch.io/#/1/classic/swap/{market_name}'
