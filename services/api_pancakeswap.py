import requests
from .market_base import Market, Coin, Cup, CupEntry, CoinNotFound


class Pancakeswap(Market):

    def __init__(self) -> None:
        super().__init__('Pancakeswap')
        self.symbol_address_dict = {}

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_name(self)}/{base_coin.get_name()}'

    def find_address(self, coin: Coin) -> str:
        resp = requests.get('https://api.pancakeswap.info/api/v2/tokens')
        rjson = resp.json()['data']
        for address, data in rjson.items():
            if data['symbol'] == coin.get_upper_name(self):
                return address
        if coin.address:
            return coin.address
        raise CoinNotFound

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        target_base_amount = 510

        if coin.get_upper_name(self) in self.symbol_address_dict:
            address = self.symbol_address_dict[coin.get_upper_name(self)]
        else:
            address = self.find_address(coin)

        resp = requests.get(
            f'https://api.pancakeswap.info/api/v2/tokens/{address}')
        price = float(resp.json()['data']['price'])
        coin_amount = target_base_amount / price

        asks = [CupEntry(float(price), float(coin_amount)), ]
        bids = [CupEntry(float(price), float(coin_amount)), ]
        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        return 'https://pancakeswap.finance/swap'
