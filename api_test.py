import logging

from services.market_base import Market, Coin
import services.api_config

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('api_test')

btc_coin = Coin('btc')

for market in Market.all_markets:
    try:
        cup = market.get_cup(
            coin=btc_coin,
            base_coin=Market.usdt_coin,
            depth=10
        )
        log.info(f'get_cup() for {market.name} returned something')
    except Exception:
        log.error(f'get_cup() for {market.name} does not work')

    try:
        best_price = market.get_price(
            coin=btc_coin,
            base_coin=Market.usdt_coin
        )
        log.info(
            f'get_price() for {market.name} returned: {best_price.best_ask.number}')
    except Exception:
        log.error(f'get_price() for {market.name} does not work')

    print('------')
