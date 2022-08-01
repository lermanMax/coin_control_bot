import requests
from .market_base import Market, Coin, Cup, CupEntry


class Mexc(Market):

    def __init__(self) -> None:
        super().__init__('mexc')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}{base_coin.get_upper_name()}'

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        symbol = self.make_name_for_market(coin, base_coin)
        payload = {'symbol': symbol, 'limit': depth}
        resp = requests.get('https://api.mexc.com/api/v3/depth',
                            params=payload)
        # ---------------------------------------------------------------------
        rjson = resp.json()
        asks_json = rjson['asks']
        bids_json = rjson['bids']

        asks = [CupEntry(entry[0], entry[1]) for entry in asks_json]
        bids = [CupEntry(entry[0], entry[1]) for entry in bids_json]

        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = \
            f'{coin.get_upper_name(self)}_{base_coin.get_upper_name()}'
        return f'https://www.mexc.com/exchange/{market_name}'
