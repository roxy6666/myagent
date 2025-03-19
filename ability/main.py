"""Main module for accessing blockchain transaction data and smart contract code."""
from typing import Dict, Any, Literal, Union, Optional

from ability.ethereum import EthereumClient
from ability.binance import BinanceSmartChainClient


def get_transaction_data(
    tx_hash: str, 
    blockchain: Literal["ethereum", "binance"] = "ethereum",
    node_url: Optional[str] = None
) -> Dict[str, Any]:
    """Get transaction data and related smart contract information.
    
    Args:
        tx_hash: Transaction hash
        blockchain: Blockchain to use ("ethereum" or "binance")
        node_url: Optional custom node URL
        
    Returns:
        Dictionary containing transaction data and related information
        
    Raises:
        ValueError: If blockchain type is not supported
    """
    if blockchain.lower() == "ethereum":
        client = EthereumClient(node_url) if node_url else EthereumClient()
    elif blockchain.lower() == "binance":
        client = BinanceSmartChainClient(node_url) if node_url else BinanceSmartChainClient()
    else:
        raise ValueError(f"Unsupported blockchain: {blockchain}. Use 'ethereum' or 'binance'.")
    
    return client.get_transaction(tx_hash) 