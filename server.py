import os,time,json
from bottle import Bottle, run, template, request, static_file, response
from ability.ethereum.client import EthereumClient
from ability.ethereum.analysis_state import AnalysisState, StateStorage
from ability.tenderly import TenderlySimulator
from threading import Thread, Lock
from typing import Dict
from openai import OpenAI
from ability.binance.client import BinanceSmartChainClient

running_tasks: Dict[str, Thread] = {}
task_lock = Lock()

# 确保环境变量存在，否则使用默认值或抛出错误
api_key = os.getenv("TENDERLY_API_KEY")
if api_key is None:
    raise ValueError("TENDERLY_API_KEY environment variable is not set")

account_id = os.getenv("TENDERLY_ACCOUNT_SLUG")
if account_id is None:
    raise ValueError("TENDERLY_ACCOUNT_SLUG environment variable is not set")

project_slug = os.getenv("TENDERLY_PROJECT_SLUG")
if project_slug is None:
    raise ValueError("TENDERLY_PROJECT_SLUG environment variable is not set")

trt = TenderlySimulator(
    api_key=api_key,
    account_id=account_id,
    project_slug=project_slug,
    cache_dir=os.path.join(os.path.dirname(__file__), "tenderly")
)

state_storage = StateStorage(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'states'))
# Configure template directory

openAI_api_key = os.getenv("OPENAI_API_KEY")
if openAI_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

openAI_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openAI_api_key,
)

app = Bottle()
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views')
template.default_template_dir = template_dir

prompt_system = '''
        你是一个区块链的分析师, 下面是某个合约的模拟交易在用户真正执行交易之前去分析对Slot影响这个步骤.
        你的回答是需要是Json, 你的输出会直接送到下一个工序中显示给用户. 
        你要回答如下的JSON格式, 注意输出的时候**不要**加上Markdown语法:

        {
            "stop": true,
            "reason": "reason"
        }

        字段解释: stop 是提醒用户要不要交易. 
        reason是, 提示用户为什么要停止交易. 说清楚交易后果, 给不懂技术的人看也要能看懂, 比如说钱被转走了, 或者失去资产控制权, 要非常清晰简短. 使用英文!
'''

def render_prompt(state_change: str, source_code: str, state_define: str) -> str:
    return f"""
下面是执行模拟交易之后合约中的状态变化: 
{state_change}

下面是合约的源代码: 
{source_code}

下面是合约的state定义: 
{state_define}
"""

def update_result_and_save(analysis: AnalysisState):
    result = ''
    analysis.status = 'done'
    if analysis.risk:
        result = '''
        <div class='risk-alert danger'>
            ⚠️ Potential Risk Detected
        </div>
        '''
    else:
        result = '''
        <div class='risk-alert success'>
            ✅ No Potential Risk Found
        </div>
        '''
    if analysis.reason and analysis.contract_id:
        for i in range(len(analysis.reason)):
            result += f'''
                <h5>Contract ID: {analysis.contract_id[i]}</h5>
                <p>Risk Reason: {analysis.reason[i]}</p>
        '''
    analysis.result = result
    state_storage.save(analysis)

def analysis_thread_handler(tx_hash: str):
    # 先检查任务是否在运行
    with task_lock:
        if tx_hash in running_tasks:
            # 检查线程是否还活着
            thread = running_tasks[tx_hash]
            if thread.is_alive():
                print(f"Transaction {tx_hash} is already running")
                return
            else:
                # 如果线程已经结束，清理它
                del running_tasks[tx_hash]

        analysis = state_storage.get(tx_hash)
        if not analysis:
            print(f"Transaction {tx_hash} not found")
            return
        if analysis.status == 'done':
            print(f"Transaction {tx_hash} is already done")
            return
            
        # 创建新线程
        thread = Thread(target=analysis_thread, args=(analysis,))
        thread.start()
        running_tasks[tx_hash] = thread

def analysis_thread(analysis: AnalysisState):
    try:
        analysis.result= '<div class="step">simulation transaction...</div>'
        state_storage.save(analysis)
        network_id = '1'
        if analysis.chainname == 'BSC':
            network_id = '56'
        simres = trt.simulate_transaction(
            network_id=network_id,
            from_address=analysis.from_address,
            to_address=analysis.to_address,
            input_data=analysis.data,
            value=hex(analysis.value),
            block_number=analysis.block_number-1
        )
        # Get state changes from simulation result
        state_change = simres.get('transaction', {}).get('transaction_info', {}).get('state_diff', {})
        
        if isinstance(state_change, list):
            filtered_changes = []
            for state in state_change:
                if state.get('soltype'):
                    if state['soltype'].get('name') == 'nonce':
                        continue
                filtered_changes.append(state)
            state_change = filtered_changes
        # Get contracts from simulation result
        contracts = simres.get('contracts', [])
        for contract in contracts:
            analysis.result= '<div class="step">llm analysis contract '+contract.get('contract_id')+'...</div>'
            state_storage.save(analysis)
            state_define = contract.get('data',{}).get('states')
            source_code = contract.get('data', {}).get('contract_info', [{}])[0].get('source')
            prompt = render_prompt(
                json.dumps(state_change, indent=2),
                source_code,
                json.dumps(state_define, indent=2)
            )
            completion = openAI_client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {
                        "role": "system",
                        "content": prompt_system
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            llm_json_result = completion.choices[0].message.content
            if llm_json_result is None:
                raise ValueError("LLM response is None")
            # Parse the JSON string result from LLM
            # Remove code block markers if present
            if llm_json_result.startswith('```json'):
                llm_json_result = llm_json_result[7:]
            elif llm_json_result.startswith('```'):
                # Check if there's a language specifier after ```
                first_newline = llm_json_result.find('\n')
                if first_newline > 3:  # Has content after ```
                    llm_json_result = llm_json_result[first_newline + 1:]
                else:
                    llm_json_result = llm_json_result[3:]
            
            if llm_json_result.endswith('```'):
                llm_json_result = llm_json_result[:-3]
            
            # Strip any leading/trailing whitespace
            llm_json_result = llm_json_result.strip()
            try:
                llm_result = json.loads(llm_json_result)
                analysis.risk = llm_result.get('stop', False)
                reason = llm_result.get('reason', "")
                analysis.reason.append(reason)
                analysis.contract_id.append(contract.get('contract_id'))
                state_storage.save(analysis)
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {str(e)}")
                print(f"LLM response: {llm_json_result}")
        update_result_and_save(analysis)
    finally:
        # 清理运行状态
        with task_lock:
            if analysis.tx in running_tasks:
                del running_tasks[analysis.tx]

# Serve static files
@app.route('/static/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='./static')

@app.route('/')
def index():
    # Example transactions for demonstration
    example_txs = [
        {'chain': 'ETH', 'name': 'Bybit Exploit', 'tx': '0xbe42ca77d43686c822a198c3641f3dadd1edcb5fde22fbc1738b3298a9c25ddb'},
        {'chain': 'BSC', 'name': 'BSC: USDT normal transfer', 'tx': '0x180cab3c4237d34d4965d586b2f6bd44897c26c9375ead5a778d6ce21407e19a'},
        {'chain': 'ETH', 'name': 'Poly Network Hack', 'tx': '0x789...ghi'},
    ]
    return template('index', example_txs=example_txs)

@app.route('/sign')
def sign():
    try:
        network = request.query.get('network', 'ETH')
        if network not in ['ETH', 'BSC']:
            return template('error', error_message="Network must be either 'ETH' or 'BSC'")

        tx: str = request.query.get('tx')
        if not tx:
            return template('error', error_message="Transaction hash is required")
        if not tx.startswith('0x'):
            return template('error', error_message="Transaction hash must start with '0x'")
        if not len(tx) == 66:  # 0x + 64 hex chars
            return template('error', error_message="Invalid transaction hash length")
        if not all(c in '0123456789abcdefABCDEF' for c in tx[2:]):
            return template('error', error_message="Transaction hash contains invalid characters")
        
        txscope = {}
        if network == 'ETH':
            client = EthereumClient()
            transaction = client.get_transaction(tx)
            txscope = transaction.get('transaction')
        elif network == 'BSC':
            client = BinanceSmartChainClient()
            txscope = client.get_transaction(tx)
            # Convert hex value and blockNumber to integers
            txscope['value'] = int(txscope['value'], 16)
            txscope['blockNumber'] = int(txscope['blockNumber'], 16)

        # Check if transaction data exists
        if not txscope:
            return template('error', error_message="Transaction data not found")
            
        # Mock transaction information
        tx_info: Dict[str, str] = {
            'network': network,  # Use the actual network parameter
            'from_address': txscope.get('from', ''), # Provide default value
            'to_address': txscope.get('to', ''),     # Provide default value
            'data': txscope.get('input', ''),       # Provide default value
            'tx': tx,
        }

        analysis = AnalysisState()
        analysis.from_address = txscope['from']
        analysis.to_address = txscope['to']
        analysis.data = txscope['input']
        analysis.value = int(txscope['value'])
        analysis.block_number = int(txscope['blockNumber'])
        analysis.tx = tx
        analysis.chainname = network
        analysis.status = 'doing'
        # 验证所有字段
        if not analysis.validate():
            raise ValueError("Missing required fields in analysis state")
        
        state_storage.save(analysis)
  
        analysis_thread_handler(tx)
        
        # Ensure the template directory is correct
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views')
        print(f"Template directory: {template_dir}")
        
        return template('sign', tx_info=tx_info, analysis=analysis)
    except Exception as e:
        print(f"Error in sign route: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return f"Error: {str(e)}"

# 添加一个装饰器来处理 WSGI server 的响应流
def stream_response(callback):
    def wrapper(*args, **kwargs):
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'  # Disable buffering for Nginx
        return callback(*args, **kwargs)
    return wrapper

# 使用装饰器的版本
@app.route('/analysis-stream')
@stream_response
def analysis_stream():
    # 获取并验证 tx 参数
    tx = request.query.get('tx')
    if not tx:
        yield "event: message\ndata: <div class='step'>Transaction hash is required</div>\n\n"
        return
    
    if not tx.startswith('0x') or len(tx) != 66 or not all(c in '0123456789abcdefABCDEF' for c in tx[2:]):
        yield "event: message\ndata: <div class='step'>Invalid transaction hash format</div>\n\n"
        return
    
    
    while True:
        analysis = state_storage.get(tx)
        if not analysis:
            yield "event: message\ndata: <div class='step'>Transaction not found</div>\n\n"
            return
            
        if analysis.result:
            data = analysis.result.replace('\n', '')
            yield f"event: message\ndata: {data}\n\n"
            
        # 关键改动：检查分析是否完成
        if analysis.status == 'done':
            return  # 分析完成，退出循环
            
        time.sleep(1)

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8080, debug=True) 