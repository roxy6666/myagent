import json
import os
import hashlib
import logging
import requests
from typing import Dict, Any, Optional, Union, cast
from web3 import Web3
from web3.types import _Hash32
from hexbytes import HexBytes


logger = logging.getLogger(__name__)


def generate_query_hash(**kwargs: Any) -> str:
    """
    生成查询哈希值用于缓存

    参数:
    **kwargs: 需要纳入哈希计算的键值对

    返回:
    str: 查询哈希值
    """
    # 按键排序以确保相同参数生成相同哈希
    sorted_items = sorted(kwargs.items())
    # 将参数转换为字符串并连接
    param_str = "-".join([f"{k}:{v}" for k, v in sorted_items])
    return hashlib.sha256(param_str.encode()).hexdigest()


class TenderlySimulator:
    def __init__(
        self, 
        api_key: str, 
        account_id: str, 
        project_slug: str, 
        cache_dir: Optional[str] = None
    ):
        """
        参数:
        api_key: Tenderly API密钥
        account_id: Tenderly 账户ID
        project_slug: Tenderly 项目标识
        cache_dir: 缓存目录，默认为None
        """
        self.api_key = api_key
        self.base_url = f"https://api.tenderly.co/api/v1/account/{account_id}/project/{project_slug}/simulate"
        self.headers = {"X-Access-Key": api_key, "Content-Type": "application/json"}
        self.cache_dir = cache_dir
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def simulate_transaction(
        self,
        network_id: str,
        from_address: str,
        to_address: str,
        input_data: str,
        value: str = "0x0",
        block_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        模拟以太坊交易并返回原始响应

        参数:
        from_address: 发送交易的地址
        to_address: 接收交易的地址
        network_id: 网络ID (例如: 1 为以太坊主网)
        input_data: 交易输入数据
        value: 交易金额(以wei为单位)，默认为"0x0"
        block_number: 区块号，默认为None表示最新区块
        
        返回:
        Dict[str, Any]: 模拟结果
        """

        simulation_body = {
            "network_id": network_id,
            "from": from_address,
            "to": to_address,
            "input": input_data,
            "value": value,
            "block_number": block_number,
            "simulation_type": "full",
            "save": False,
        }

        # 生成查询哈希
        query_hash = generate_query_hash(
            **{k: v for k, v in simulation_body.items() if v is not None}
        )

        query_cache_file_path = os.path.join(self.cache_dir or "", f"{query_hash}.json")
        if self.cache_dir and os.path.exists(query_cache_file_path):
            with open(query_cache_file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        response = requests.post(
            self.base_url, headers=self.headers, json=simulation_body
        )
        response.raise_for_status()
        # 直接返回原始响应
        data = response.json()
        if self.cache_dir:
            logger.info(f"Cache query result to {query_cache_file_path}")
            with open(query_cache_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        return data


def get_transaction_params_by_hash(rpc_url: str, tx_hash: Union[str, HexBytes]) -> Dict[str, Any]:
    """
    通过交易哈希获取交易参数

    参数:
    rpc_url: 以太坊RPC节点URL
    tx_hash: 交易哈希值

    返回:
    Dict[str, Any]: 交易参数字典
    """
    # 初始化web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    # 获取交易信息
    # 确保交易哈希格式正确
    if isinstance(tx_hash, str):
        if not tx_hash.startswith('0x'):
            tx_hash = f'0x{tx_hash}'
        tx_hash = HexBytes(tx_hash)
    
    # 将 HexBytes 转为 _Hash32 类型
    hash32_tx_hash = cast(_Hash32, tx_hash)
    tx = w3.eth.get_transaction(hash32_tx_hash)
    
    if not tx:
        raise ValueError(f"Transaction with hash {tx_hash} not found.")
    # 获取链ID
    chain_id = w3.eth.chain_id
    # 构造参数字典
    tx_params = {
        "from_address": tx.get("from"),
        "to_address": tx.get("to"),
        "network_id": chain_id,
        "input_data": "0x" + tx.get("input", b"").hex(),
        "value": hex(tx.get("value", 0)),  # 转换为hex字符串
        "block_number": tx.get("blockNumber"),
        # "gas": tx["gas"],
        # "gas_price": hex(tx["gasPrice"]),  # 转换为hex字符串
    }
    # print(tx_params)
    return tx_params


