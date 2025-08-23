import asyncio
import json
from fastmcp import Client

async def ask_question():
    # 使用你的Metaso配置
    config = {
        "mcpServers": {
            "zhipu-web-search-sse": {
                "url": "https://open.bigmodel.cn/api/mcp/web_search/sse?Authorization=<API_KEY>"
            }
        }
    }

    try:
        async with Client(config) as client:
            print("正在连接到 Sogou 搜索服务器...")

            # 首先列出可用的工具，找到合适的问答工具
            # tools = await client.list_tools()
            # for tool in tools:
            #     print(f"工具名称: {tool.name}")
            #     print(f"工具参数: {tool.inputSchema}")
            #     print(f"工具描述: {tool.description}")
            #     print("-----------------")

            question = "AI大语言模型相关的最新研究"
            args = {
                "search_query": question,
                "count": 20,  # 返回20条结果
                "search_recency_filter": "oneMonth",
                "content_size": "high"  # 高详细度摘要
            }

            # 尝试调用问答工具
            result = await client.call_tool("webSearchSogou", args)
            print(f"问题: {question}")
            # print(f"回答: {result.data}")
            text_result = result.content[0].text
            # 第一步：解析外层字符串
            unescaped_json = json.loads(text_result)
            # 第二步：解析内层 JSON 字符串
            data = json.loads(unescaped_json)
            # 第三步：打印解析后的 JSON 数据
            for item in data:
                print(f"标题: {item['title']}")
                print(f"链接: {item['link']}")
                print(f"来源: {item['media']}")
                print(f"发布日期: {item['publish_date']}")
                print(f"内容: {item['content']}")
                print('-----------------')

    except Exception as e:  
        print(f"调用失败: {e}")

if __name__ == "__main__":  
    asyncio.run(ask_question())
