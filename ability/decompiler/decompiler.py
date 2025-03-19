"""Smart contract bytecode decompiler."""
import subprocess
import tempfile
import os
from typing import Optional, List, Tuple


def decompile_bytecode(bytecode: str) -> str:
    """Decompile EVM bytecode to Solidity code.
    
    This function attempts to decompile EVM bytecode to Solidity using available tools.
    It tries various decompilers in order of preference:
    1. Heimdall-rs (if available)
    2. Panoramix (if available)
    3. ethersplay (if available)
    4. Finally falls back to enhanced opcode extraction with basic Solidity structure
    
    Args:
        bytecode: EVM bytecode as a hexadecimal string
        
    Returns:
        Decompiled Solidity code or a placeholder message if decompilation fails
    """
    try:
        # Try decompilers in order of preference
        
        # Try heimdall-rs decompiler
        decompiled = _decompile_with_heimdall(bytecode)
        if decompiled:
            return decompiled
            
        # Try panoramix
        decompiled = _decompile_with_panoramix(bytecode)
        if decompiled:
            return decompiled
            
        # Try ethersplay
        decompiled = _decompile_with_ethersplay(bytecode)
        if decompiled:
            return decompiled
        
        # Fall back to enhanced opcode extraction
        return _enhanced_solidity_fallback(bytecode)
    except Exception as e:
        return f"Decompilation failed: {str(e)}\nRaw bytecode: {bytecode[:100]}... (truncated)"


def _decompile_with_heimdall(bytecode: str) -> Optional[str]:
    """Try to decompile using heimdall-rs decompiler (if installed).
    
    Heimdall-rs is a Rust-based EVM decompiler with good Solidity output.
    
    Args:
        bytecode: EVM bytecode
        
    Returns:
        Decompiled Solidity code or None if heimdall is not available
    """
    try:
        # Check if heimdall is installed
        result = subprocess.run(
            ["which", "heimdall"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return None
            
        # Create a temporary file with the bytecode
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp:
            if bytecode.startswith("0x"):
                bytecode = bytecode[2:]
            temp.write(bytecode.encode())
            temp_path = temp.name
            
        try:
            # Run heimdall
            result = subprocess.run(
                ["heimdall", "decompile", temp_path, "--output-format", "solidity"],
                capture_output=True,
                text=True,
                timeout=120  # Timeout after 120 seconds
            )
            
            if result.returncode == 0 and result.stdout:
                return f"// Decompiled with heimdall-rs\n\n{result.stdout}"
            return None
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception:
        return None


def _decompile_with_panoramix(bytecode: str) -> Optional[str]:
    """Try to decompile using panoramix (if installed).
    
    Args:
        bytecode: EVM bytecode
        
    Returns:
        Decompiled code or None if panoramix is not available
    """
    try:
        # Check if panoramix is installed
        result = subprocess.run(
            ["which", "panoramix"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return None
            
        # Create a temporary file with the bytecode
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(bytecode.encode())
            temp_path = temp.name
            
        try:
            # Run panoramix
            result = subprocess.run(
                ["panoramix", temp_path],
                capture_output=True,
                text=True,
                timeout=60  # Timeout after 60 seconds
            )
            
            if result.returncode == 0 and result.stdout:
                return f"// Decompiled with Panoramix\n\n{result.stdout}"
            return None
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception:
        return None


def _decompile_with_ethersplay(bytecode: str) -> Optional[str]:
    """Try to decompile using ethersplay (if installed).
    
    Args:
        bytecode: EVM bytecode
        
    Returns:
        Decompiled code or None if ethersplay is not available
    """
    try:
        # Check if ethersplay is installed
        result = subprocess.run(
            ["which", "ethersplay"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return None
            
        # Create a temporary file with the bytecode
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp:
            if bytecode.startswith("0x"):
                bytecode = bytecode[2:]
            temp.write(bytes.fromhex(bytecode))
            temp_path = temp.name
            
        try:
            # Run ethersplay
            result = subprocess.run(
                ["ethersplay", temp_path],
                capture_output=True,
                text=True,
                timeout=60  # Timeout after 60 seconds
            )
            
            if result.returncode == 0 and result.stdout:
                return f"// Decompiled with ethersplay\n\n{result.stdout}"
            return None
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception:
        return None


def _enhanced_solidity_fallback(bytecode: str) -> str:
    """Create a Solidity-like representation from the bytecode.
    
    This is a fallback when no decompilers are available. It extracts opcodes
    and attempts to organize them into a basic Solidity contract structure.
    
    Args:
        bytecode: EVM bytecode
        
    Returns:
        Solidity-like representation of the bytecode
    """
    if bytecode.startswith("0x"):
        bytecode = bytecode[2:]
    
    # Try to identify function selectors (first 4 bytes of keccak256 hash of function signatures)
    function_selectors = _extract_function_selectors(bytecode)
    
    # Try to extract storage slots
    storage_slots = _extract_storage_slots(bytecode)
    
    # Basic disassembly of opcodes
    opcodes = _disassemble_opcodes(bytecode)
    
    # Format as Solidity-like code
    solidity_output = "// Fallback decompilation - simplified Solidity representation\n\n"
    solidity_output += "pragma solidity ^0.8.0;\n\n"
    solidity_output += "contract DecompiledContract {\n"
    
    # Add storage variables
    if storage_slots:
        solidity_output += "    // Detected storage variables\n"
        for i, slot in enumerate(storage_slots):
            solidity_output += f"    uint256 private _storage{i}; // slot: {slot}\n"
        solidity_output += "\n"
    
    # Add function selectors
    if function_selectors:
        solidity_output += "    // Detected function selectors\n"
        for selector, signature in function_selectors:
            if signature:
                solidity_output += f"    // Function: {signature}\n"
            solidity_output += f"    // Selector: 0x{selector}\n"
            solidity_output += f"    function func_{selector}() public {{\n"
            solidity_output += f"        // Implementation details not available\n"
            solidity_output += f"    }}\n\n"
    
    # Add fallback function
    solidity_output += "    // Fallback function\n"
    solidity_output += "    fallback() external payable {\n"
    solidity_output += "        // Implementation details not available\n"
    solidity_output += "    }\n\n"
    
    # Add receive function
    solidity_output += "    // Receive function\n"
    solidity_output += "    receive() external payable {}\n"
    
    solidity_output += "}\n\n"
    
    # Add disassembled opcodes as comment
    solidity_output += "/*\nDisassembled Opcodes (first 100):\n"
    solidity_output += "\n".join(opcodes[:100])
    if len(opcodes) > 100:
        solidity_output += "\n...(truncated)"
    solidity_output += "\n*/\n"
    
    return solidity_output


def _extract_function_selectors(bytecode: str) -> List[Tuple[str, Optional[str]]]:
    """Extract function selectors from bytecode.
    
    Args:
        bytecode: EVM bytecode without 0x prefix
        
    Returns:
        List of tuples containing (selector, signature if known)
    """
    # Look for PUSH4 opcodes followed by common selector comparison opcodes
    selectors = []
    i = 0
    
    # Common function signatures
    known_selectors = {
        "a9059cbb": "transfer(address,uint256)",
        "095ea7b3": "approve(address,uint256)",
        "23b872dd": "transferFrom(address,address,uint256)",
        "70a08231": "balanceOf(address)",
        "18160ddd": "totalSupply()",
        "313ce567": "decimals()",
        "06fdde03": "name()",
        "95d89b41": "symbol()",
        "dd62ed3e": "allowance(address,address)",
    }
    
    while i < len(bytecode) - 10:
        # PUSH4 opcode is 0x63
        if bytecode[i:i+2] == "63":
            # Next 8 chars (4 bytes) could be a function selector
            potential_selector = bytecode[i+2:i+10]
            
            # Only add if it seems like a valid selector
            if len(potential_selector) == 8 and all(c in "0123456789abcdef" for c in potential_selector):
                signature = known_selectors.get(potential_selector)
                selectors.append((potential_selector, signature))
            
            i += 10  # Skip past the PUSH4 and its data
        else:
            i += 2  # Move to next opcode
    
    return selectors


def _extract_storage_slots(bytecode: str) -> List[str]:
    """Extract potential storage slots from bytecode.
    
    Args:
        bytecode: EVM bytecode without 0x prefix
        
    Returns:
        List of storage slots as hex strings
    """
    # Look for SLOAD and SSTORE opcodes and preceding PUSH instructions
    storage_slots = []
    i = 0
    
    while i < len(bytecode) - 4:
        # SLOAD is 0x54, SSTORE is 0x55
        if bytecode[i:i+2] in ["54", "55"]:
            # Look back for a PUSH operation that might be pushing the slot
            # PUSH1 through PUSH32 opcodes are 0x60 through 0x7F
            back_index = i - 2
            while back_index >= 0 and back_index > i - 70:  # Don't look back too far
                opcode = bytecode[back_index:back_index+2]
                if opcode >= "60" and opcode <= "7f":
                    # Found a PUSH, extract the pushed value
                    push_size = int(opcode, 16) - 0x60 + 1  # Calculate size from opcode
                    slot = bytecode[back_index+2:back_index+2+(push_size*2)]
                    if slot and all(c in "0123456789abcdef" for c in slot):
                        storage_slots.append(slot)
                    break
                back_index -= 2
        i += 2
    
    # Remove duplicates and return
    return list(set(storage_slots))


def _disassemble_opcodes(bytecode: str) -> List[str]:
    """Disassemble bytecode into opcodes with simple descriptions.
    
    Args:
        bytecode: EVM bytecode without 0x prefix
        
    Returns:
        List of opcode descriptions
    """
    # Define common EVM opcodes
    opcodes = {
        "00": "STOP",
        "01": "ADD",
        "02": "MUL",
        "03": "SUB",
        "04": "DIV",
        "05": "SDIV",
        "06": "MOD",
        "07": "SMOD",
        "08": "ADDMOD",
        "09": "MULMOD",
        "0a": "EXP",
        "0b": "SIGNEXTEND",
        "10": "LT",
        "11": "GT",
        "12": "SLT",
        "13": "SGT",
        "14": "EQ",
        "15": "ISZERO",
        "16": "AND",
        "17": "OR",
        "18": "XOR",
        "19": "NOT",
        "1a": "BYTE",
        "1b": "SHL",
        "1c": "SHR",
        "1d": "SAR",
        "20": "SHA3",
        "30": "ADDRESS",
        "31": "BALANCE",
        "32": "ORIGIN",
        "33": "CALLER",
        "34": "CALLVALUE",
        "35": "CALLDATALOAD",
        "36": "CALLDATASIZE",
        "37": "CALLDATACOPY",
        "38": "CODESIZE",
        "39": "CODECOPY",
        "3a": "GASPRICE",
        "3b": "EXTCODESIZE",
        "3c": "EXTCODECOPY",
        "3d": "RETURNDATASIZE",
        "3e": "RETURNDATACOPY",
        "3f": "EXTCODEHASH",
        "40": "BLOCKHASH",
        "41": "COINBASE",
        "42": "TIMESTAMP",
        "43": "NUMBER",
        "44": "DIFFICULTY",
        "45": "GASLIMIT",
        "50": "POP",
        "51": "MLOAD",
        "52": "MSTORE",
        "53": "MSTORE8",
        "54": "SLOAD",
        "55": "SSTORE",
        "56": "JUMP",
        "57": "JUMPI",
        "58": "PC",
        "59": "MSIZE",
        "5a": "GAS",
        "5b": "JUMPDEST",
        "60": "PUSH1",
        "61": "PUSH2",
        "62": "PUSH3",
        "63": "PUSH4",
        "64": "PUSH5",
        "65": "PUSH6",
        "66": "PUSH7",
        "67": "PUSH8",
        "68": "PUSH9",
        "69": "PUSH10",
        "6a": "PUSH11",
        "6b": "PUSH12",
        "6c": "PUSH13",
        "6d": "PUSH14",
        "6e": "PUSH15",
        "6f": "PUSH16",
        "70": "PUSH17",
        "71": "PUSH18",
        "72": "PUSH19",
        "73": "PUSH20",
        "74": "PUSH21",
        "75": "PUSH22",
        "76": "PUSH23",
        "77": "PUSH24",
        "78": "PUSH25",
        "79": "PUSH26",
        "7a": "PUSH27",
        "7b": "PUSH28",
        "7c": "PUSH29",
        "7d": "PUSH30",
        "7e": "PUSH31",
        "7f": "PUSH32",
        "80": "DUP1",
        "81": "DUP2",
        "82": "DUP3",
        "83": "DUP4",
        "84": "DUP5",
        "85": "DUP6",
        "86": "DUP7",
        "87": "DUP8",
        "88": "DUP9",
        "89": "DUP10",
        "8a": "DUP11",
        "8b": "DUP12",
        "8c": "DUP13",
        "8d": "DUP14",
        "8e": "DUP15",
        "8f": "DUP16",
        "90": "SWAP1",
        "91": "SWAP2",
        "92": "SWAP3",
        "93": "SWAP4",
        "94": "SWAP5",
        "95": "SWAP6",
        "96": "SWAP7",
        "97": "SWAP8",
        "98": "SWAP9",
        "99": "SWAP10",
        "9a": "SWAP11",
        "9b": "SWAP12",
        "9c": "SWAP13",
        "9d": "SWAP14",
        "9e": "SWAP15",
        "9f": "SWAP16",
        "a0": "LOG0",
        "a1": "LOG1",
        "a2": "LOG2",
        "a3": "LOG3",
        "a4": "LOG4",
        "f0": "CREATE",
        "f1": "CALL",
        "f2": "CALLCODE",
        "f3": "RETURN",
        "f4": "DELEGATECALL",
        "f5": "CREATE2",
        "fa": "STATICCALL",
        "fd": "REVERT",
        "fe": "INVALID",
        "ff": "SELFDESTRUCT"
    }
    
    result = []
    i = 0
    while i < len(bytecode):
        opcode = bytecode[i:i+2].lower()
        if opcode not in opcodes:
            result.append(f"0x{opcode} (UNKNOWN)")
            i += 2
            continue
            
        opcode_name = opcodes[opcode]
        
        # For PUSH operations, include the pushed data
        if opcode >= "60" and opcode <= "7f":
            push_size = int(opcode, 16) - 0x60 + 1  # Size in bytes
            if i + 2 + (push_size * 2) <= len(bytecode):
                pushed_data = bytecode[i+2:i+2+(push_size*2)]
                result.append(f"0x{opcode} {opcode_name} 0x{pushed_data}")
                i += 2 + (push_size * 2)
            else:
                # Not enough data for the full push
                result.append(f"0x{opcode} {opcode_name} (incomplete)")
                i = len(bytecode)  # End loop
        else:
            result.append(f"0x{opcode} {opcode_name}")
            i += 2
            
    return result 