import requests
from .market_base import Market, Coin, Cup, CupEntry


class Bitrue(Market):

    def __init__(self) -> None:
        super().__init__('bitrue')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}{base_coin.get_upper_name()}'

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        symbol = self.make_name_for_market(coin, base_coin)
        payload = {'symbol': symbol, 'limit': depth}
        resp = requests.get('https://openapi.bitrue.com/api/v1/depth',
                            params=payload)

        bids_json = resp.json()['bids']
        asks_json = resp.json()['asks']

        asks = [CupEntry(float(entry[0]), float(entry[1]))
                for entry in asks_json]
        bids = [CupEntry(float(entry[0]), float(entry[1]))
                for entry in bids_json]

        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = f'{coin.get_name(self)}_{base_coin.get_name()}'
        return f'https://www.bitrue.com/trade/{market_name}'
