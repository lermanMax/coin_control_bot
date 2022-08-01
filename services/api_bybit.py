import requests
from .market_base import Market, Coin, Cup, CupEntry


class ByBit(Market):

    def __init__(self) -> None:
        super().__init__('bybit')

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}{base_coin.get_upper_name()}'

    # доступна depth <= 25
    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        symbol = self.make_name_for_market(coin, base_coin)
        payload = {'symbol': symbol}
        resp = requests.get('https://api.bybit.com/v2/public/orderBook/L2',
                            params=payload)
        result = resp.json()['result']

        asks = [CupEntry(float(entry['price']), float(entry['size']))
                for entry in result if entry['side'] == 'Sell']
        bids = [CupEntry(float(entry['price']), float(entry['size']))
                for entry in result if entry['side'] == 'Buy']

        return Cup(asks[0:depth], bids[0:depth])

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = f'{coin.get_upper_name()}/{base_coin.get_upper_name()}'
        return f'https://www.bybit.com/en-US/trade/spot/{market_name}'
