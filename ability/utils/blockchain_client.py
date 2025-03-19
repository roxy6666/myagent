"""Base client for blockchain interactions."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import web3
from web3 import Web3
from web3.types import TxData, BlockData


class BlockchainClient(ABC):
    """Base class for blockchain clients."""
    
    def __init__(self, node_url: str):
        """Initialize the blockchain client.
        
        Args:
            node_url: URL of the blockchain node
        """
        self.node_url = node_url
        self.w3 = Web3(Web3.HTTPProvider(node_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to node at {node_url}")
    
    @abstractmethod
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction data by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction data
        """
        pass
    
    @abstractmethod
    def get_contract_code(self, address: str) -> str:
        """Get contract bytecode by address.
        
        Args:
            address: Contract address
            
        Returns:
            Contract bytecode
        """
        pass
    
    @abstractmethod
    def decompile_contract(self, bytecode: str) -> str:
        """Decompile contract bytecode.
        
        Args:
            bytecode: Contract bytecode
            
        Returns:
            Decompiled contract code
        """
        pass 