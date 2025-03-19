# My Agent


## ability prompt

帮我实现一个ability包， 里面有两大类需求需要实现： 实现语言用python3

1. 输入一个 Tx 则： 调用Ethereum的public node 获取某个交易Tx 下面的所有的原始数据， 并且如果交易是与一个智能合约交互，那就获取智能合约代码。 如果没有Verified 智能合约你要反编译
2. 同上不过是Binance Smart Chain
3. 帮我写个.gitignore 来避免提交没必要的文件到git
4. 别忘了在项目根目录下面写个 require.txt 来解决python3的依赖声明

非功能需求：

1. 帮我做好必要的测试。
2. 配置好 Pyright 我特别喜欢静态类型。 

# Ability Package

A Python package for analyzing blockchain transactions and smart contracts.

## Features

- Retrieve transaction data from Ethereum and Binance Smart Chain
- Get smart contract code associated with transactions
- Decompile smart contract bytecode when source code is not available

## Installation

```bash
pip install -r requirements.txt
# Alternatively for development:
pip install -e .
```

## Usage

### Basic Usage

```python
from ability import get_transaction_data

# Get Ethereum transaction data
eth_result = get_transaction_data("0x123abc...", blockchain="ethereum")
print(eth_result)

# Get Binance Smart Chain transaction data
bsc_result = get_transaction_data("0x456def...", blockchain="binance")
print(bsc_result)
```

### Using the CLI Example

```bash
# Ethereum transaction
python example.py 0x123abc...

# Binance Smart Chain transaction
python example.py 0x456def... binance
```

### Advanced Usage

```python
from ability import EthereumClient, BinanceSmartChainClient

# Use custom Ethereum node
eth_client = EthereumClient(node_url="https://your-ethereum-node.com")
eth_result = eth_client.get_transaction("0x123abc...")

# Use custom Binance Smart Chain node
bsc_client = BinanceSmartChainClient(node_url="https://your-bsc-node.com")
bsc_result = bsc_client.get_transaction("0x456def...")
```

## Tests

```bash
# Run the tests
pytest tests/

# Run with coverage
pytest --cov=ability tests/
```

## Type Checking

This project uses Pyright for static type checking:

```bash
# Install the pyright package
pip install pyright

# Run type checking
pyright
``` 