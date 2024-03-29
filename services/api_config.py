from .api_huobi import Huobi
from .api_ftx import Ftx
from .api_kraken import Kraken
from .api_bybit import ByBit
from .api_crypto import Crypto
from .api_kucoin import Kucoin
from .api_mexc import Mexc
from .api_gate import Gate
from .api_bitmart import BitMart
from .api_bitrue import Bitrue
from .api_lbank import Lbank

from .api_raydium import Raydium
from .api_oneinch import Oneinch
from .api_jupyter import Jupyter
from .api_pancakeswap import Pancakeswap

# Initialization all Markets
Huobi()
Ftx(
    api_key='VXCjc-Mc-pF142F92NKtvK1MAey9Iilt3dD176pX',
    api_secret='Bo9SvZpZotPAyJ5WaPtOi1mepiP3QIXtlvD0imqe'
)

Kraken()
ByBit()
Crypto()
Kucoin()
Mexc()
Gate()
BitMart()
Bitrue()
Lbank()

Raydium()
Oneinch()
Jupyter()
Pancakeswap()
