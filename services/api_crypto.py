import requests
from .market_base import Market, Coin, Cup, CupEntry


class Crypto(Market):

    def __init__(self) -> None:
        super().__init__('crypto')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}_{base_coin.get_upper_name()}'

    # параметр depth не срабатывает, поэтому entries обрезаются уже на выходе
    # без подписки доступно только depth <= 10
    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        if depth > 10:
            depth = 10
        symbol = self.make_name_for_market(coin, base_coin)
        payload = {'instrument_name': symbol, 'depth': str(depth)}
        resp = requests.get('https://api.crypto.com/v2/public/get-book',
                            params=payload)

        rjson = resp.json()['result']['data'][0]
        asks_json = rjson['asks']
        bids_json = rjson['bids']

        asks = [CupEntry(float(entry[0]), float(entry[1])) for entry in asks_json]
        bids = [CupEntry(float(entry[0]), float(entry[1])) for entry in bids_json]

        return Cup(asks[0:depth], bids[0:depth])

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = self.make_name_for_market(coin, base_coin)
        return f'https://crypto.com/exchange/trade/spot/{market_name}'
