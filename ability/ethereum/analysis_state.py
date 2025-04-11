from typing import Optional, Dict, Any, Literal
import json
import os

# Define valid status values
StatusType = Literal["doing", "done"]

class AnalysisState:
    """Class for managing analysis state in memory"""
    def __init__(self):
        """Initialize an empty analysis state"""
        self.tx: str = ""  # 必填
        self.chainname: str = ""  # 必填
        self._status: StatusType = "doing"  # 设置默认状态
        self.terendlyresult: Dict[str, Any] = {}  # 初始化为空字典
        self.result: str = ""  # HTML content as string
        self.from_address: str = ""  # 必填
        self.to_address: str = ""  # 必填
        self.data: str = ""  # 必填
        self.value: int = 0  # 交易金额，使用整数类型
        self.block_number: int = 0  # 区块号，必填
        self.risk: bool = False  # 是否存在风险
        self.reason: list[str] = []  # 风险原因数组
        self.contract_id: list[str] = []  # 对应的合约ID数组
    @property
    def status(self) -> StatusType:
        """
        获取当前状态
        """
        return self._status
    
    @status.setter
    def status(self, value: StatusType) -> None:
        """
        设置状态，只允许 'doing' 或 'done'
        :param value: 状态值
        :raises ValueError: 当状态值无效时抛出
        """
        if value not in ["doing", "done"]:
            raise ValueError(f"Invalid status value: {value}. Must be 'doing' or 'done'")
        self._status = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the state to a dictionary"""
        return {
            "tx": self.tx,
            "chainname": self.chainname,
            "status": self._status,
            "terendlyresult": self.terendlyresult,
            "result": self.result,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "data": self.data,
            "value": self.value,
            "block_number": self.block_number,
            "risk": self.risk,
            "reason": self.reason,
            "contract_id": self.contract_id
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load state from a dictionary"""
        self.tx = data.get("tx")
        self.chainname = data.get("chainname")
        self.status = data.get("status")  # This will use the setter with validation
        self.terendlyresult = data.get("terendlyresult")
        self.result = data.get("result")
        self.from_address = data.get("from_address")
        self.to_address = data.get("to_address")
        self.data = data.get("data")
        self.value = data.get("value")
        self.block_number = data.get("block_number")
        self.risk = data.get("risk")
        self.reason = data.get("reason")
        self.contract_id = data.get("contract_id")
        
    def validate(self) -> bool:
        """
        验证所有必填字段是否都已填写
        """
        return all([
            self.tx,
            self.chainname,
            self._status,
            isinstance(self.terendlyresult, dict),
            self.result is not None,
            self.from_address,
            self.to_address,
            self.data,
            isinstance(self.value, int),
            isinstance(self.block_number, int) and self.block_number > 0
        ])


class StateStorage:
    """Class for managing persistence of analysis states"""
    def __init__(self, directory: str):
        """
        Initialize the storage with a directory path.
        
        Args:
            directory (str): The directory path where states will be stored
        """
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
    
    def save(self, state: AnalysisState) -> None:
        """
        Save an analysis state to a JSON file.
        
        Args:
            state (AnalysisState): The state to save
        """
        if not state.tx:
            raise ValueError("Transaction hash (tx) must be set before saving")
            
        file_path = os.path.join(self.directory, f"{state.tx}.json")
        with open(file_path, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)
    
    def get(self, tx: str) -> Optional[AnalysisState]:
        """
        Load state from a JSON file for a specific transaction.
        
        Args:
            tx (str): The transaction hash to load
            
        Returns:
            Optional[AnalysisState]: The loaded state or None if not found
        """
        file_path = os.path.join(self.directory, f"{tx}.json")
        
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'r') as f:
                state_data = json.load(f)
                
            state = AnalysisState()
            state.from_dict(state_data)
            return state
        except Exception:
            return None 