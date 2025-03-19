from typing import Dict, Any, List, Optional
import json
import re
import subprocess
import tempfile
import os
from eth_abi.codec import ABICodec
from eth_abi.registry import registry
from eth_utils.abi import function_signature_to_4byte_selector
from eth_utils.hexadecimal import encode_hex

class InputDecoder:
    """Decoder for Ethereum transaction input data."""
    
    def __init__(self):
        self.abi_codec = ABICodec(registry)
        # 常见的函数选择器映射
        self.function_selectors = {
            "0xa9059cbb": {
                "name": "transfer",
                "inputs": [
                    {"type": "address", "name": "recipient"},
                    {"type": "uint256", "name": "amount"}
                ]
            },
            "0x6a761202": {
                "name": "execTransaction",
                "inputs": [
                    {"type": "address", "name": "to"},
                    {"type": "uint256", "name": "value"},
                    {"type": "bytes", "name": "data"},
                    {"type": "uint8", "name": "operation"},
                    {"type": "uint256", "name": "safeTxGas"},
                    {"type": "uint256", "name": "baseGas"},
                    {"type": "uint256", "name": "gasPrice"},
                    {"type": "address", "name": "gasToken"},
                    {"type": "address", "name": "refundReceiver"},
                    {"type": "bytes", "name": "signatures"}
                ]
            }
        }

    def decode_input(self, input_data: str, contract_source: Optional[str] = None) -> Dict[str, Any]:
        """解析交易输入数据
        
        Args:
            input_data: 交易输入数据的十六进制字符串
            contract_source: 可选的合约源代码（Solidity代码或ABI JSON字符串）
            
        Returns:
            解析后的数据字典，包含调用的函数名和参数
        """
        if not input_data.startswith('0x'):
            input_data = '0x' + input_data
            
        if len(input_data) < 10:
            return {"error": "Invalid input data"}
            
        # 获取函数选择器
        function_selector = input_data[2:10]
        
        # 如果提供了合约源代码，尝试解析并添加到函数选择器映射中
        if contract_source:
            try:
                self._parse_contract_source(contract_source)
            except Exception as e:
                return {
                    "error": f"Failed to parse contract source: {str(e)}",
                    "raw_input": input_data,
                    "function_selector": function_selector
                }
        
        # 尝试解析函数调用
        try:
            result = self._decode_function_call(input_data)
            
            # 如果是execTransaction，进一步解析其data字段
            if result.get("function") == "execTransaction":
                nested_data = result.get("params", {}).get("data")
                if nested_data and nested_data != "0x":
                    result["nested_call"] = self._decode_function_call(nested_data)
                    
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to decode input: {str(e)}",
                "raw_input": input_data,
                "function_selector": function_selector
            }

    def _parse_contract_source(self, contract_source: str) -> None:
        """解析合约源代码，提取函数签名并添加到选择器映射中
        
        Args:
            contract_source: 合约源代码（Solidity代码或ABI JSON字符串）
        """
        # 首先尝试作为JSON解析（可能是ABI）
        try:
            abi = json.loads(contract_source)
            self._process_abi(abi)
            return
        except json.JSONDecodeError:
            # 不是JSON，尝试作为Solidity源代码处理
            pass
            
        # 检查是否看起来像Solidity代码
        if "contract" in contract_source and "function" in contract_source:
            # 编译Solidity代码获取ABI
            abi = self._compile_solidity(contract_source)
            if abi:
                self._process_abi(abi)
                return
                
        raise ValueError("Unable to parse contract source. Provide either valid ABI JSON or Solidity code.")
    
    def _compile_solidity(self, source_code: str) -> List[Dict]:
        """编译Solidity源代码并返回ABI
        
        Args:
            source_code: Solidity源代码
            
        Returns:
            编译生成的ABI
        """
        # 提取Solidity版本
        solidity_version = self._extract_solidity_version(source_code)
        
        # 创建临时文件保存源代码
        with tempfile.NamedTemporaryFile(suffix='.sol', delete=False) as temp_file:
            temp_file.write(source_code.encode('utf-8'))
            temp_file_path = temp_file.name
            
        try:
            # 获取临时文件的绝对路径和目录
            abs_file_path = os.path.abspath(temp_file_path)
            file_dir = os.path.dirname(abs_file_path)
            file_name = os.path.basename(abs_file_path)
            
            # 使用Docker运行solc
            cmd = [
                'docker', 'run', '--rm',
                '-v', f"{file_dir}:/sources",
                f"ethereum/solc:{solidity_version}",
                '--combined-json', 'abi',
                f"/sources/{file_name}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 解析编译结果
            output = json.loads(result.stdout)
            
            # 从输出中提取ABI
            all_abis = []
            for contract_path, contract_data in output.get('contracts', {}).items():
                contract_abi = json.loads(contract_data.get('abi', '[]'))
                all_abis.extend(contract_abi)
                
            return all_abis
            
        except subprocess.SubprocessError as e:
            raise ValueError(f"Failed to compile Solidity code: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse compiler output: {str(e)}")
        finally:
            # 删除临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    def _extract_solidity_version(self, source_code: str) -> str:
        """从Solidity源代码中提取编译器版本
        
        Args:
            source_code: Solidity源代码
            
        Returns:
            Solidity版本字符串，格式为x.y.z
        """
        # 使用正则表达式提取pragma声明
        pragma_match = re.search(r'pragma\s+solidity\s+([^;]+);', source_code)
        
        if not pragma_match:
            # 没有找到版本声明，使用默认版本
            return '0.8.17'  # 使用一个较新的稳定版本作为默认值
            
        version_constraint = pragma_match.group(1).strip()
        
        # 处理各种版本约束格式
        # 例如: ^0.8.0, >=0.7.0 <0.9.0, 0.8.7
        if '^' in version_constraint:
            # ^0.8.0 格式 -> 取0.8.0
            version = version_constraint.replace('^', '').strip()
        elif '>=' in version_constraint and '<' in version_constraint:
            # >=0.7.0 <0.9.0 格式 -> 取中间值，如0.8.0
            min_version = re.search(r'>=\s*(\d+\.\d+\.\d+)', version_constraint)
            if min_version:
                version = min_version.group(1)
            else:
                version = '0.8.17'  # 默认值
        else:
            # 简单版本，如0.8.7
            version_match = re.search(r'(\d+\.\d+\.\d+)', version_constraint)
            if version_match:
                version = version_match.group(1)
            else:
                version = '0.8.17'  # 默认值
                
        return version
    
    def _process_abi(self, abi: List[Dict]) -> None:
        """处理ABI，提取函数签名并生成选择器
        
        Args:
            abi: 合约ABI
        """
        for item in abi:
            if item.get('type') == 'function':
                # 构建函数签名
                name = item.get('name', '')
                inputs = item.get('inputs', [])
                
                # 生成签名字符串，如: "transfer(address,uint256)"
                input_types = [inp.get('type', '') for inp in inputs]
                signature = f"{name}({','.join(input_types)})"
                
                # 计算4字节选择器
                selector = function_signature_to_4byte_selector(signature)
                selector_hex = encode_hex(selector)
                
                # 保存到函数选择器映射中
                self.function_selectors[selector_hex] = {
                    "name": name,
                    "inputs": inputs
                }

    def _decode_function_call(self, input_data: str) -> Dict[str, Any]:
        """解析函数调用数据
        
        Args:
            input_data: 函数调用数据
            
        Returns:
            解析后的函数调用信息
        """
        if input_data.startswith('0x'):
            input_data = input_data[2:]
            
        function_selector = input_data[:8]
        parameters = input_data[8:]
        
        # 查找函数定义
        function_def = self.function_selectors.get(f"0x{function_selector}")
        
        if not function_def:
            return {
                "function_selector": f"0x{function_selector}",
                "raw_parameters": parameters
            }
            
        try:
            # 解码参数
            decoded = self._decode_parameters(parameters, function_def["inputs"])
            
            return {
                "function": function_def["name"],
                "params": decoded
            }
            
        except Exception as e:
            return {
                "function": function_def["name"],
                "error": f"Parameter decoding failed: {str(e)}",
                "raw_parameters": parameters
            }

    def _decode_parameters(self, parameters: str, inputs: List[Dict[str, str]]) -> Dict[str, Any]:
        """解码函数参数
        
        Args:
            parameters: 参数数据
            inputs: 参数定义列表
            
        Returns:
            解码后的参数字典
        """
        result = {}
        offset = 0
        parameter_data = bytes.fromhex(parameters)
        
        for input_def in inputs:
            param_type = input_def["type"]
            param_name = input_def["name"]
            
            if param_type == "address":
                value = "0x" + parameter_data[offset:offset+32][-20:].hex()
                offset += 32
                result[param_name] = value
                
            elif param_type == "uint256" or param_type == "uint8":
                value = int.from_bytes(parameter_data[offset:offset+32], "big")
                offset += 32
                result[param_name] = value
                
            elif param_type == "bytes":
                # 获取动态数据的偏移量
                data_offset = int.from_bytes(parameter_data[offset:offset+32], "big")
                offset += 32
                
                # 获取bytes的长度
                length = int.from_bytes(parameter_data[data_offset:data_offset+32], "big")
                # 获取实际数据
                value = "0x" + parameter_data[data_offset+32:data_offset+32+length].hex()
                result[param_name] = value
                
            else:
                result[param_name] = f"Unsupported type: {param_type}"
                
        return result

    def format_decoded_input(self, decoded: Dict[str, Any], indent: int = 2) -> str:
        """格式化解码后的输入数据为可读字符串
        
        Args:
            decoded: 解码后的数据字典
            indent: 缩进空格数
            
        Returns:
            格式化后的字符串
        """
        return json.dumps(decoded, indent=indent) 