import requests
from .market_base import Market, Coin, Cup, CupEntry, CoinNotFound


class Raydium(Market):

    def __init__(self) -> None:
        super().__init__('Raydium')
        self.symbol_address_dict = {}

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_upper_name(self)}-{base_coin.get_upper_name()}'

    def find_pair(self, coin: Coin, base_coin: Coin) -> str:
        resp = requests.get('https://api.raydium.io/v2/main/pairs')
        rjson = resp.json()
        pair_name = self.make_name_for_market(coin, base_coin)
        for data in rjson:
            if data['name'] == pair_name:
                return data
        raise CoinNotFound

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        pair_data = self.find_pair(coin, base_coin)

        # цена
        price = float(pair_data['price'])
        # все монеты, который продаются
        coin_amount = float(pair_data['tokenAmountCoin'])
        # все доллары которые продаются
        base_amount = float(pair_data['tokenAmountPc'])

        asks = [CupEntry(price, coin_amount), ]
        bids = [CupEntry(price, base_amount / price), ]
        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        return 'https://raydium.io/swap'
