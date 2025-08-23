import asyncio
import json
import re
from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
# In-memory server (ideal for testing)
server = FastMCP("TestServer")
client = Client(server)

# HTTP server
client = Client("https://metaso.cn/api/mcp",auth=BearerAuth("<API_KEY>"))

async def main():
    async with client:
        # Basic server interaction
        await client.ping()

        # List available operations
        # tools = await client.list_tools()
        # resources = await client.list_resources()
        # prompts = await client.list_prompts()
        # print(tools)
        # print(resources)
        # print(prompts)
        # Execute operations
        result = await client.call_tool(
            "metaso_chat",
            {"message": "请解释一下量子计算的基本原理", "model": "fast"}
        )

        # 正确的方式：解析JSON字符串然后访问content字段
        response_data = json.loads(result.content[0].text)
        content = response_data["content"]
        
        # 去除引用标识（如[[1]]、[[2]]等）
        clean_content = re.sub(r'\[\[\d+\]\]', '', content)
        print(clean_content)

        # result = await client.call_tool(
        #     "metaso_web_search", 
        #     {"q": "量子计算的基本原理"}
        # )
        # print(result)

asyncio.run(main())
