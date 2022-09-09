import requests
from .market_base import Market, Coin, Cup, CupEntry


class Jupyter(Market):

    def __init__(self) -> None:
        super().__init__('Jupyter')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_name(self)}/{base_coin.get_name()}'

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        target_base_amount = 510
        market = f'id={coin.get_name(self)}&vsToken={base_coin.get_name()}'
        resp = requests.get(
            f'https://quote-api.jup.ag/v1/price?{market}')
        price = float(resp.json()['data']['price'])
        coin_amount = target_base_amount / price

        asks = [CupEntry(float(price), float(coin_amount)), ]
        bids = [CupEntry(float(price), float(coin_amount)), ]
        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market = \
            f'{coin.get_upper_name(self)}-{base_coin.get_upper_name(self)}'
        return f'https://jup.ag/swap/{market}'
