from typing import Any, Dict, List, Union

def truncate_long_strings(
    data: Union[Dict, List, str, Any], 
    max_length: int = 200
) -> Union[Dict, List, str, Any]:
    """
    递归处理JSON数据，截断过长的字符串值，并过滤掉 src_map 键值对
    
    Args:
        data: 任意JSON数据（字典、列表、字符串等）
        max_length: 字符串最大长度，默认200
    
    Returns:
        处理后的数据
    """
    # 如果是字典，递归处理每个值，并过滤掉 src_map
    if isinstance(data, dict):
        return {
            key: truncate_long_strings(value, max_length) 
            for key, value in data.items() 
            if key != 'src_map'
        }
    
    # 如果是列表，递归处理每个元素
    elif isinstance(data, list):
        return [truncate_long_strings(item, max_length) for item in data]
    
    # 如果是字符串，检查长度并在需要时截断
    elif isinstance(data, str):
        if len(data) > max_length:
            return data[:max_length] + "..."
        return data
    
    # 其他类型（数字、布尔值等）直接返回
    else:
        return data

# 使用示例
if __name__ == "__main__":
    import argparse
    import json
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='截断 JSON 文件中的长字符串')
    parser.add_argument('input_file', help='输入的 JSON 文件路径')
    parser.add_argument('--max-length', type=int, default=200, help='字符串最大长度 (默认: 200)')
    parser.add_argument('--output-file', help='输出的 JSON 文件路径 (默认: 打印到控制台)')
    
    args = parser.parse_args()
    
    # 读取 JSON 文件
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{args.input_file}'")
        exit(1)
    except json.JSONDecodeError:
        print(f"错误: '{args.input_file}' 不是有效的 JSON 文件")
        exit(1)
    
    # 处理数据
    result = truncate_long_strings(input_data, args.max_length)
    
    # 输出结果
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"处理后的数据已保存到: {args.output_file}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))