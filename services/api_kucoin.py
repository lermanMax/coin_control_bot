import requests
from .market_base import Market, Coin, Cup, CupEntry


class Kucoin(Market):

    def __init__(self) -> None:
        super().__init__('kucoin')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}-{base_coin.get_upper_name()}'

    # можно запросить только depth=20 или depth=100 ->
    # будет запрашиваться 20 и обрезаться при необходимости на выходе
    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        symbol = self.make_name_for_market(coin, base_coin)
        payload = {'symbol': symbol}
        resp = requests.get('https://api.kucoin.com/api/v1/market'
                            '/orderbook/level2_20', params=payload)
        # ---------------------------------------------------------------------
        rjson = resp.json()['data']
        asks_json = rjson['asks']
        bids_json = rjson['bids']

        asks = [CupEntry(entry[0], entry[1]) for entry in asks_json]
        bids = [CupEntry(entry[0], entry[1]) for entry in bids_json]

        return Cup(asks[0:depth], bids[0:depth])

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = self.make_name_for_market(coin, base_coin)
        return f'https://www.kucoin.com/ru/trade/{market_name}'
