"""Binance Smart Chain client implementation."""
from typing import Any, Dict
import json
import requests

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
        """Get transaction data by hash using BSC JSON-RPC API.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Dictionary containing transaction data and related information
            
        Raises:
            Exception: If the transaction cannot be retrieved
        """
        # Ensure tx_hash has 0x prefix
        if not tx_hash.startswith('0x'):
            tx_hash = '0x' + tx_hash
            
        # Prepare the JSON-RPC request
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getTransactionByHash",
            "params": [tx_hash],
            "id": 1
        }
        
        try:
            # Make the request
            response = requests.post(
                self.node_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            if "error" in result:
                raise Exception(f"BSC node error: {result['error']}")
                
            if "result" not in result or result["result"] is None:
                raise Exception(f"Transaction {tx_hash} not found")
                
            # Get the transaction data
            tx_data = result["result"]
            
            # Get additional transaction receipt data
            receipt_payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1
            }
            
            receipt_response = requests.post(
                self.node_url,
                json=receipt_payload,
                headers={"Content-Type": "application/json"}
            )
            receipt_response.raise_for_status()
            receipt_result = receipt_response.json()
            
            if "result" in receipt_result and receipt_result["result"]:
                tx_data["receipt"] = receipt_result["result"]
            
            return tx_data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch transaction data: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse response: {str(e)}")
        except Exception as e:
            raise Exception(f"Error retrieving transaction data: {str(e)}") 