import requests
from .market_base import Market, Coin, Cup, CupEntry


class BitMart(Market):

    def __init__(self) -> None:
        super().__init__('bitmart')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}_{base_coin.get_upper_name()}'

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        symbol = self.make_name_for_market(coin, base_coin)
        payload = {'symbol': symbol, 'size': depth}
        resp = requests.get('https://api-cloud.bitmart.com'
                            '/spot/v1/symbols/book', params=payload)
        # ---------------------------------------------------------------------
        rjson = resp.json()['data']
        asks_json = rjson['sells']
        bids_json = rjson['buys']

        asks = [CupEntry(float(entry['price']), float(entry['amount']))
                for entry in asks_json]
        bids = [CupEntry(float(entry['price']), float(entry['amount']))
                for entry in bids_json]

        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = self.make_name_for_market(coin, base_coin)

        return f'https://www.bitmart.com/trade/' \
               f'en?symbol={market_name}&layout=pro'
