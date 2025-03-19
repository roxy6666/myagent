"""Ethereum blockchain client implementation."""
from typing import Any, Dict, cast, Optional, List

from web3 import Web3
from web3.exceptions import TransactionNotFound
from hexbytes import HexBytes

from ability.utils.blockchain_client import BlockchainClient
from ability.decompiler.decompiler import decompile_bytecode


class EthereumClient(BlockchainClient):
    """Client for interacting with Ethereum blockchain."""
    
    def __init__(self, node_url: Optional[str] = None):
        """Initialize the Ethereum client.
        
        Args:
            node_url: URL of the Ethereum node, defaults to using INFURA_API_KEY from environment variables
        """
        import os
        if node_url is None:
            infura_api_key = os.environ.get('INFURA_API_KEY')
            if not infura_api_key:
                raise ValueError("INFURA_API_KEY environment variable is not set")
            node_url = f"https://mainnet.infura.io/v3/{infura_api_key}"
        
        super().__init__(node_url)
    
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction data by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Dictionary containing transaction data, addresses of involved contracts,
            and decompiled contract code if available
        
        Raises:
            TransactionNotFound: If the transaction doesn't exist
        """
        # Convert to checksum address if needed
        if not tx_hash.startswith('0x'):
            tx_hash = '0x' + tx_hash
            
        try:
            # Convert string hash to HexBytes before passing to web3
            tx_hash_bytes = HexBytes(tx_hash)
            
            # Get transaction data
            tx = self.w3.eth.get_transaction(tx_hash_bytes)
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash_bytes)
            
            # Get block data - use get() to safely access blockNumber
            block_number = getattr(tx, 'blockNumber', None)
            if block_number is None:
                raise ValueError(f"Transaction {tx_hash} has no blockNumber (might be pending)")
                
            # Convert to dict for easier handling
            tx_dict = dict(tx)
            tx_receipt_dict = dict(tx_receipt)
            
            # Convert Web3.py objects to primitive types
            for key, value in tx_dict.items():
                if isinstance(value, (bytes, bytearray)):
                    tx_dict[key] = value.hex()
            
            # Initialize list to store contract addresses and decompiled code
            contract_addresses: List[str] = []
            decompiled_contracts: Dict[str, str] = {}
            
            # Check if this transaction is a contract deployment
            if tx_receipt_dict.get('contractAddress'):
                # Contract creation
                contract_address = cast(str, tx_receipt_dict['contractAddress'])
                contract_code = self.get_contract_code(contract_address)
                if contract_code and contract_code != '0x':
                    contract_addresses.append(contract_address)
                    # Decompile the deployed contract
                    try:
                        decompiled_code = self.decompile_contract(contract_code)
                        decompiled_contracts[contract_address] = decompiled_code
                    except Exception as e:
                        decompiled_contracts[contract_address] = f"Decompilation failed: {str(e)}"
            
            # Check if this transaction interacts with an existing contract
            if tx_dict.get('to'):
                to_address = cast(str, tx_dict['to'])
                contract_code = self.get_contract_code(to_address)
                if contract_code and contract_code != '0x':
                    # This is a contract interaction
                    contract_addresses.append(to_address)
                    # Decompile the target contract
                    try:
                        decompiled_code = self.decompile_contract(contract_code)
                        decompiled_contracts[to_address] = decompiled_code
                    except Exception as e:
                        decompiled_contracts[to_address] = f"Decompilation failed: {str(e)}"
            
            # Parse transaction input data
            input_data = tx_dict.get('input', '0x')
            if not isinstance(input_data, str):
                input_data = str(input_data)
            decoded_input = self._decode_transaction_input(input_data, tx_dict)
            
            # Create result dictionary with transaction, contract addresses and decompiled code
            result: Dict[str, Any] = {
                'transaction': tx_dict,
                'contracts': contract_addresses,
                'decompiled_contracts': decompiled_contracts,
                'decoded_input': decoded_input
            }
            
            return result
            
        except TransactionNotFound:
            raise TransactionNotFound(f"Transaction with hash {tx_hash} not found")
        except Exception as e:
            raise Exception(f"Error retrieving transaction data: {str(e)}")
    
    def _decode_transaction_input(self, input_data: str, tx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Decode transaction input data to a more human-readable format.
        
        Args:
            input_data: Hex string of transaction input data
            tx_dict: Transaction dictionary
            
        Returns:
            Dictionary with decoded input information
        """
        if not input_data or input_data == '0x' or input_data == '0x0':
            return {
                'type': 'transfer',
                'description': 'Simple ETH transfer with no additional data'
            }
            
        # Check if it's a contract creation (no function selector)
        if tx_dict.get('to') is None:
            return {
                'type': 'contract_creation',
                'description': 'Contract creation transaction',
                'bytecode': input_data
            }
            
        # Otherwise it's a contract interaction
        # Extract function signature (first 4 bytes of the hash)
        function_selector = input_data[:10]  # '0x' + 8 chars
        parameters = input_data[10:]
            
        # Common function selectors (this is just a small example, could be expanded)
        known_selectors = {
            # ERC20 Standard
            '0xa9059cbb': {
                'name': 'transfer',
                'signature': 'transfer(address,uint256)',
                'description': 'ERC20 token transfer',
                'param_types': ['address', 'uint256'],
                'param_names': ['to', 'value']
            },
            '0x095ea7b3': {
                'name': 'approve',
                'signature': 'approve(address,uint256)',
                'description': 'ERC20 token approval',
                'param_types': ['address', 'uint256'],
                'param_names': ['spender', 'value']
            },
            '0x23b872dd': {
                'name': 'transferFrom',
                'signature': 'transferFrom(address,address,uint256)',
                'description': 'ERC20 transferFrom',
                'param_types': ['address', 'address', 'uint256'],
                'param_names': ['from', 'to', 'value']
            },
            '0x70a08231': {
                'name': 'balanceOf',
                'signature': 'balanceOf(address)',
                'description': 'ERC20 balance query',
                'param_types': ['address'],
                'param_names': ['account']
            },
            '0x18160ddd': {
                'name': 'totalSupply',
                'signature': 'totalSupply()',
                'description': 'ERC20 total supply query',
                'param_types': [],
                'param_names': []
            },
            '0x06fdde03': {
                'name': 'name',
                'signature': 'name()',
                'description': 'ERC20 token name',
                'param_types': [],
                'param_names': []
            },
            '0x95d89b41': {
                'name': 'symbol',
                'signature': 'symbol()',
                'description': 'ERC20 token symbol',
                'param_types': [],
                'param_names': []
            },
            '0x313ce567': {
                'name': 'decimals',
                'signature': 'decimals()',
                'description': 'ERC20 token decimals',
                'param_types': [],
                'param_names': []
            },
            
            # ERC721 Standard
            '0x42842e0e': {
                'name': 'safeTransferFrom',
                'signature': 'safeTransferFrom(address,address,uint256)',
                'description': 'ERC721 safe transfer',
                'param_types': ['address', 'address', 'uint256'],
                'param_names': ['from', 'to', 'tokenId']
            },
            '0xb88d4fde': {
                'name': 'safeTransferFrom',
                'signature': 'safeTransferFrom(address,address,uint256,bytes)',
                'description': 'ERC721 safe transfer with data',
                'param_types': ['address', 'address', 'uint256', 'bytes'],
                'param_names': ['from', 'to', 'tokenId', 'data']
            },
            '0x6352211e': {
                'name': 'ownerOf',
                'signature': 'ownerOf(uint256)',
                'description': 'ERC721 token owner query',
                'param_types': ['uint256'],
                'param_names': ['tokenId']
            },
            '0x081812fc': {
                'name': 'getApproved',
                'signature': 'getApproved(uint256)',
                'description': 'ERC721 get approved address',
                'param_types': ['uint256'],
                'param_names': ['tokenId']
            },
            '0x8462151c': {
                'name': 'tokenURI',
                'signature': 'tokenURI(uint256)',
                'description': 'ERC721 token URI',
                'param_types': ['uint256'],
                'param_names': ['tokenId']
            },
            
            # Uniswap/DEX
            '0x7ff36ab5': {
                'name': 'swapExactETHForTokens',
                'signature': 'swapExactETHForTokens(uint256,address[],address,uint256)',
                'description': 'Uniswap V2: Swap ETH for tokens',
                'param_types': ['uint256', 'address[]', 'address', 'uint256'],
                'param_names': ['amountOutMin', 'path', 'to', 'deadline']
            },
            '0x38ed1739': {
                'name': 'swapExactTokensForTokens',
                'signature': 'swapExactTokensForTokens(uint256,uint256,address[],address,uint256)',
                'description': 'Uniswap V2: Swap tokens for tokens',
                'param_types': ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                'param_names': ['amountIn', 'amountOutMin', 'path', 'to', 'deadline']
            },
        }
            
        result: Dict[str, Any] = {
            'type': 'contract_interaction',
            'function_selector': function_selector
        }
            
        # If we know this function selector, add the information
        if function_selector in known_selectors:
            func_info = known_selectors[function_selector]
            for key, value in func_info.items():
                if key not in ['param_types', 'param_names']:
                    result[key] = value
            
            # Try to decode parameters based on param_types
            try:
                param_types = func_info.get('param_types', [])
                param_names = func_info.get('param_names', [])
                
                if param_types and isinstance(param_types, list):
                    decoded_params = self._decode_parameters(parameters, param_types)
                    if isinstance(param_names, list):
                        formatted_params = self._format_parameters(decoded_params, param_types, param_names)
                        result['parameters'] = formatted_params
                    else:
                        result['raw_parameters'] = parameters
            except Exception as e:
                # If parameter decoding fails, add the raw parameters
                result['raw_parameters'] = parameters
                result['decoding_error'] = str(e)
        else:
            # Unknown function
            result['description'] = 'Unknown function call'
            result['raw_parameters'] = parameters
                
        return result

    def _decode_parameters(self, parameters: str, param_types: List[str]) -> List[Any]:
        """Decode raw parameters based on their types.
        
        Args:
            parameters: Hex string of parameters
            param_types: List of parameter types
            
        Returns:
            List of decoded parameters
        """
        decoded_params = []
        offset = 0
        
        for param_type in param_types:
            if param_type == 'address':
                # Addresses are 32 bytes (64 chars) padded, but we only need the last 20 bytes (40 chars)
                if offset + 64 <= len(parameters):
                    address = '0x' + parameters[offset:offset+64][-40:]
                    try:
                        # Try to convert to checksum address
                        address = Web3.to_checksum_address(address)
                    except:
                        pass
                    decoded_params.append(address)
                    offset += 64
                else:
                    decoded_params.append(None)
            
            elif param_type.startswith('uint'):
                # Uint values are 32 bytes (64 chars)
                if offset + 64 <= len(parameters):
                    value = int(parameters[offset:offset+64], 16)
                    decoded_params.append(value)
                    offset += 64
                else:
                    decoded_params.append(None)
            
            elif param_type == 'bool':
                if offset + 64 <= len(parameters):
                    value = parameters[offset:offset+64]
                    decoded_params.append(value != '0' * 64)
                    offset += 64
                else:
                    decoded_params.append(None)
            
            elif param_type == 'bytes':
                # Variable length bytes have an offset and then the data
                if offset + 64 <= len(parameters):
                    # Get the offset to the data
                    data_offset = int(parameters[offset:offset+64], 16) * 2  # Convert byte offset to char offset
                    offset += 64
                    
                    if data_offset + 64 <= len(parameters):
                        # Get the length of the bytes
                        length = int(parameters[data_offset:data_offset+64], 16) * 2  # Convert byte length to char length
                        data_offset += 64
                        
                        if data_offset + length <= len(parameters):
                            bytes_data = '0x' + parameters[data_offset:data_offset+length]
                            decoded_params.append(bytes_data)
                        else:
                            decoded_params.append(None)
                    else:
                        decoded_params.append(None)
                else:
                    decoded_params.append(None)
            
            elif param_type.endswith('[]'):  # Array type
                # Arrays have an offset and then the data
                base_type = param_type[:-2]  # Remove the [] to get the base type
                
                if offset + 64 <= len(parameters):
                    # Get the offset to the array data
                    array_offset = int(parameters[offset:offset+64], 16) * 2  # Convert byte offset to char offset
                    offset += 64
                    
                    if array_offset + 64 <= len(parameters):
                        # Get the length of the array
                        array_length = int(parameters[array_offset:array_offset+64], 16)
                        array_offset += 64
                        
                        array_items = []
                        current_offset = array_offset
                        
                        # Process each item in the array
                        for _ in range(array_length):
                            if base_type == 'address':
                                if current_offset + 64 <= len(parameters):
                                    addr = '0x' + parameters[current_offset:current_offset+64][-40:]
                                    try:
                                        addr = Web3.to_checksum_address(addr)
                                    except:
                                        pass
                                    array_items.append(addr)
                                    current_offset += 64
                                else:
                                    array_items.append(None)
                            
                            elif base_type.startswith('uint'):
                                if current_offset + 64 <= len(parameters):
                                    val = int(parameters[current_offset:current_offset+64], 16)
                                    array_items.append(val)
                                    current_offset += 64
                                else:
                                    array_items.append(None)
                            
                            else:
                                # For other types, we'd need more specific handlers
                                array_items.append('0x' + parameters[current_offset:current_offset+64])
                                current_offset += 64
                        
                        decoded_params.append(array_items)
                    else:
                        decoded_params.append([])
                else:
                    decoded_params.append([])
            
            else:
                # For other types, just add the raw hex chunk
                if offset + 64 <= len(parameters):
                    decoded_params.append('0x' + parameters[offset:offset+64])
                    offset += 64
                else:
                    decoded_params.append(None)
        
        return decoded_params

    def _format_parameters(self, params: List[Any], param_types: List[str], param_names: List[str]) -> Dict[str, Any]:
        """Format decoded parameters with their names.
        
        Args:
            params: List of decoded parameter values
            param_types: List of parameter types
            param_names: List of parameter names
            
        Returns:
            Dictionary of named parameters
        """
        result = {}
        
        # Make sure we have names for all parameters
        while len(param_names) < len(param_types):
            param_names.append(f"param{len(param_names)}")
        
        for value, name, param_type in zip(params, param_names, param_types):
            # Format based on type
            if param_type == 'uint256' and isinstance(value, int):
                # For token amounts, show both raw and formatted value
                result[name] = {
                    'raw': value,
                    'formatted': self._format_token_amount(value)
                }
            elif param_type.endswith('[]') and isinstance(value, list):
                # For arrays, format each element
                base_type = param_type[:-2]
                if base_type == 'address':
                    result[name] = [{'address': addr} for addr in value if addr is not None]
                elif base_type.startswith('uint'):
                    result[name] = [
                        {'raw': val, 'formatted': self._format_token_amount(val)}
                        for val in value if val is not None
                    ]
                else:
                    result[name] = value
            else:
                result[name] = value
        
        return result

    def _format_token_amount(self, amount: int) -> str:
        """Format a token amount in a human-readable way.
        
        Args:
            amount: Raw token amount
            
        Returns:
            Formatted amount string
        """
        if amount == 0:
            return "0"
        
        # Assume 18 decimals which is standard for most tokens
        if amount >= 10**18:
            # Convert to whole units
            whole_units = amount / 10**18
            if whole_units.is_integer():
                return f"{int(whole_units)}"
            return f"{whole_units:.6f}"
        else:
            # Show the fraction
            fraction = amount / 10**18
            return f"{fraction:.18f}".rstrip('0').rstrip('.')
    
    def get_contract_code(self, address: str) -> str:
        """Get contract bytecode by address.
        
        Args:
            address: Contract address
            
        Returns:
            Contract bytecode, or empty string if not a contract
        """
        try:
            # Ensure address is checksum format
            address = Web3.to_checksum_address(address)
            
            # Get contract code
            code = self.w3.eth.get_code(address).hex()
            return code
        except Exception as e:
            raise Exception(f"Error retrieving contract code: {str(e)}")
    
    def decompile_contract(self, bytecode: str) -> str:
        """Decompile contract bytecode.
        
        Args:
            bytecode: Contract bytecode
            
        Returns:
            Decompiled contract code
        """
        return decompile_bytecode(bytecode) 