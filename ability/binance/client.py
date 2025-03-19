"""Binance Smart Chain client implementation."""
from typing import Any, Dict

from ability.ethereum.client import EthereumClient


class BinanceSmartChainClient(EthereumClient):
    """Client for interacting with Binance Smart Chain."""
    
    def __init__(self, node_url: str = "https://bsc-dataseed.binance.org/"):
        """Initialize the Binance Smart Chain client.
        
        Args:
            node_url: URL of the BSC node, defaults to a public endpoint
        """
        super().__init__(node_url)
        
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction data by hash.
        
        This method uses the same implementation as Ethereum, as BSC is
        EVM-compatible and has the same API.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Dictionary containing transaction data and related information
        """
        return super().get_transaction(tx_hash) 