from agent.utils.utils import (
    parse_tool_result,
)
from agent.utils.utils_tool_translation import (
    translate_chat_tool_result, 

)
from mcp_server.client import global_mcp_client

async def chat_action(message: str) -> bool:
    result_str = ""
    if message is not None:
        message = message.strip().replace('\n', '').replace('\r', '')
    args = {"message": message}
    call_result = await global_mcp_client.call_tool_directly("chat", args)
    is_success, result_content = parse_tool_result(call_result)
    result_str += translate_chat_tool_result(result_content)
    return is_success