from market_base import Coin
from coin_db.db_config import DB_NAME
from ZODB import DB
import transaction

# Coin.new_coin('Btc')
Coin.new_coin('dff')
print(len(Coin._all_coins))
Coin.update_cash_from_db()
for coin in Coin.get_all_coins():
    print(coin.get_name())
