## HARMONY TX TOOL 

### Overview
Currently, Harmony ONE's block explorer does not support bulk exporting of non-native token transactions. This means that any potentially taxable HRC-20 or HRC 1155 transactions will be omitted from an export. 

Moreover, retrieval of these transactions is not supported from Harmony's RPC endpoints, so automated tax reporting software does not support API imports of such transactions. In short, accurate tax reporting requires a great deal of manual, tedious labor from a responsible user.

This project eliminates this tedium and can collect all unsupported transactions directly from the Harmony blockchain into a CSV that can then be imported into [Koinly](https://koinly.io/) or [TokenTax](https://tokentax.co/) with no intermediate steps. 

### Features

Transaction Interpretation
- As transactions are parsed, their purpose and potential liability is interpreted. Complex transactions with many intermediate or confusing steps (see a [random example](https://explorer.harmony.one/tx/0x7652ad98b7ee3186a68a9e83b3f661f2561e02533dccd39011e60cf0667145b9)) are reduced to only the internal transactions relevant to the user's wallet. 
- We perform the 'interpretation' of transactions by deciphering the Smart Contract's original method signature and inferring inputs and outputs based on documentation of common forks. 
- Note that note of the labels assigned to a transaction should be interpreted as legal, tax, financial, or any other kind of advice. In no capacity, should this project be a substitute for a tax professional.

Price reporting
- Prices of LP tokens can be retrieved directly from DEXes. LP Tokens are typically not listed on any price tracking directories, and their price calculation may even be impossible without pulling some data from a transaction receipt. If an LP token is listed in the [ViperSwap explorer](https://info.viper.exchange/), we can retrieve its price to the closest block when the transaction occurred.
- For non-LP tokens, prices can be retrieved with CoinGecko to the closest available millisecond or can be omitted from export. Omitting the prices from export is useful in cases where [Koinly](https://koinly.io/) automatically populates historical prices.
- Additionally for adding and removing Liquidity of LP tokens, the cost of each 'side' of the pool, e.g. Token A/Token B is calculated upon split. This removes the need for any manual transaction input. Even 3-way, or n-way splits are supported, e.g. CURVE-FI's 3Pool. 

### Integrations

Tax Softwares (not endorsed or affiliated)
- Koinly 
- TokenTax

Protocol Integrations (not endorsed or affiliated)
- UniswapV2 Forks
    - [SushiSwap](https://app.sushi.com/en/swap)
    - [ViperSwap](https://viper.exchange/)
    - [DefiKingdoms](https://www.defikingdoms.com/) (the DEX component)
  
- [Tranquil Finance](https://www.tranquil.finance/)
- [Euphoria](https://euphoria.money/)
- [Horizon Bridge](https://bridge.harmony.one/)
- [Curve](https://harmony.curve.fi/)

### Contributing
If you would like to create an interpreter / editor for a currently unsupported protocol, you may create one using any of these as a starting point: [Services Code](https://github.com/tempoxylophone/Harmony-Tx-Tool/tree/main/txtool/activity/services)

Be sure to register your interpreter in [interpreter.py](https://github.com/tempoxylophone/Harmony-Tx-Tool/blob/main/txtool/activity/interpreter.py):
````python
EDITORS = [
    # ViperSwap
    ViperSwapClaimRewardsEditor(),
    ViperSwapXRewardsEditor(),
    ViperSwapLiquidityEditor(),
    # SushiSwap
    SushiSwapLiquidityEditor(),
    # ...
    # your interpreter class here
    # ...
    # Curve
    Curve3PoolLiquidityEditor(),
    CurveUSDBTCETHLiquidityEditor(),
]
````
Currently, interpreters work by examining the to/from addresses of a transaction. If a transaction has an address that no interpreter is equipped to parse, the transaction / transaction group will be exported as is. This is true even if these transactions came from a protocol for which we have a generic interpreter that implements common functions, e.g. a UniswapV2 fork. A new interpreter class must be created for that new protocol, even if there is already a base class. 

You may set up a development environment with:
```bash
make install-dev
```
This will install all dev-dependencies. Ensure that you have [pipenv](https://pipenv.pypa.io/en/latest/) installed on your system. 

You may run unit tests with the command:
```bash
make test
```

You may run linters and formatters with:
```bash
make lint
```
Linters include: 
- [mypy](https://mypy.readthedocs.io/en/stable/)
- [black](https://black.readthedocs.io/en/stable/)
- [pylint](https://pylint.pycqa.org/en/latest/)
- [flake8](https://flake8.pycqa.org/en/latest/) (with [bugbear](https://pypi.org/project/flake8-bugbear/))

See the [Makefile](https://github.com/tempoxylophone/Harmony-Tx-Tool/blob/main/Makefile) for more commands.

Testing
- to help speed up tests and thereby developer velocity, we use a custom serializer with [vcrpy](https://vcrpy.readthedocs.io/en/latest/)
- our [serializer](https://github.com/tempoxylophone/Harmony-Tx-Tool/blob/main/tests/utils/vcr_conf.py) was created to handle nested-bytes in the response from RPC endpoints, which would throw a unicode decode error in the standard serializer
- a developer can easily persist on disk, the entire request/response log of a test with three lines of code:
```python
from .utils import get_vcr # line 1
vcr = get_vcr(__file__) # line 2
# ...
@vcr.use_cassette() # line 3
def test_my_test() -> None:
    # just an example pytest setup
    assert get_server_data()['response']['hello'] == 'world'
```

### Usage
Navigate to the directory in which you cloned the repository. 

You may run with the following command:
```bash
python run.py HEX_WALLET_ADDRESS -s START_DATE -e END_DATE -l LOG_LEVEL
```

For example,
```bash
python run.py 0x0000000000000000000000000000000000000000 -s 1970-01-01 -e 2022-01-15 -l info
```

You may need to edit the save directory. See the code for this here [run.py](https://github.com/tempoxylophone/Harmony-Tx-Tool/blob/main/run.py)

### Attributions
This began as a fork of [Lila's Ledger](https://dfkreport.cognifact.com/home.py). This project was split into a separate repository with original author's permission, as they are significantly different in scope, purpose, and code.  (source
code for original: [LINK](https://github.com/pwillworth/dfkreport)) Special thanks to [Paul Willworth](https://github.com/pwillworth).
