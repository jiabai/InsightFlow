import os
import re
import asyncio
import json
import inspect
import argparse
import tempfile
from dataclasses import asdict, is_dataclass
from typing import Any, Callable
from ai_sdk import generate_object, openai

from .config import (
    ZAI_PROVIDER,
    ZAI_API_TOKEN,
    ZAI_MODEL_URL,
    TEMPERATURE,
    TOPIC,
    RESULT_PROMPT
)

from .schemas import Articles
from .tools_web_search import extract_contents
from .plan_service import generate_research_plan_and_budget
from .research_agent import execute_research_agent

def safe_slug(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[\s/\\:<>\"|?*]+", "-", s)  # 替换常见非法字符
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "topic"

def atomic_write_json(path: str, obj: Any) -> None:
    dir_ = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp.", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)  # 原子替换
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def load_urls_ckpt(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [u.strip() for u in data if isinstance(u, str) and u.strip()]
    except Exception as e:
        print(f"[warn] failed to load checkpoint {path}: {e}; will redo web search")
        try:
            os.remove(path)  # 删除损坏的 checkpoint
        except Exception:
            pass
    return []

def save_urls_ckpt(path: str, urls: list[str]) -> None:
    deduped = list(dict.fromkeys([u.strip() for u in urls if isinstance(u, str) and u.strip()]))
    atomic_write_json(path, deduped)

def remove_ckpt_silent(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# 用途：把任意 Python 对象安全地转换为 JSON 字符串，便于作为 entries 传参
def _ensure_json_str(data: Any) -> str:
    # 1) 已经是字符串，简单做个 JSON 合法性探测；若失败则按“普通文本”处理
    if isinstance(data, str):
        try:
            json.loads(data)  # 能够 parse 说明已经是 JSON 字符串
            return data
        except Exception:
            # 不是 JSON，就按普通文本装箱为 JSON（通常不建议；你也可以直接返回原字符串）
            return json.dumps({"content": data}, ensure_ascii=False)

    # 2) 是 bytes，尝试 decode
    if isinstance(data, (bytes, bytearray)):
        text = data.decode("utf-8", errors="replace")
        try:
            json.loads(text)
            return text
        except Exception:
            return json.dumps({"content": text}, ensure_ascii=False)

    # 3) dataclass 转字典
    if is_dataclass(data) and not inspect.isclass(data):
        data = asdict(data)

    if not inspect.isclass(data):
        model_dump = getattr(data, "model_dump", None)
        if isinstance(model_dump, Callable):
            try:
                data = model_dump()
            except Exception:
                pass
        else:
            dict_method = getattr(data, "dict", None)
            if isinstance(dict_method, Callable):
                try:
                    data = dict_method()
                except Exception:
                    pass

    # 5) 主序列化分支
    # - ensure_ascii=False 以保留中文
    # - separators 压缩体积；若你希望可读性可改为 indent=2
    # - default=str 用于兜底处理 datetime/Decimal/set 等不可序列化对象
    try:
        return json.dumps(
            data,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
    except TypeError:
        # 仍失败则强制转字符串再装箱
        return json.dumps({"content": str(data)}, ensure_ascii=False)

def main() -> None:
    parser = argparse.ArgumentParser(description='AI SDK Generate - 研究主题生成工具')
    _ = parser.add_argument(
        '--topic', 
        type=str, 
        default=TOPIC,
        help=f'研究主题 (默认: {TOPIC})'
    )
    _ = parser.add_argument(
        '--interactive', 
        action='store_true',
        help='交互式输入主题'
    )
    args = parser.parse_args()

    # 获取topic
    if args.interactive:
        topic = input("请输入研究主题: ").strip()
        if not topic:
            topic = TOPIC
            print(f"使用默认主题: {topic}")
    else:
        topic = args.topic

    slug = safe_slug(topic)
    ckpt_path = f"{slug}.json"
    out_md_path = f"{slug}.md"

    print(f"当前研究主题: {topic}")

    # 从 tool_results 中提取 URL，并调用 extract_contents 抽取内容
    extracted_contents: list[dict[Any, Any]] = []
    urls: list[str] = []
    # 如果topic.json文件存在，就从文件中读取URL
    if os.path.exists(ckpt_path):
        urls = load_urls_ckpt(ckpt_path)
    else:
        # 生成研究计划和预算
        plan_result = generate_research_plan_and_budget(topic)
        if plan_result is None:
            return

        plan_dict, budget = plan_result

        # 执行研究代理
        result = execute_research_agent(topic, plan_dict, budget)
        print(f"result: {result}")
        print("--------------------------------------")

        if getattr(result, "tool_results", None):
            for item in result.tool_results:
                data = getattr(item, "result", None)
                if not data:
                    continue

                # 情况1：标准字典返回，优先解析 hits 列表
                if isinstance(data, dict):
                    hits = data.get("hits")
                    if isinstance(hits, list):
                        for h in hits:
                            if isinstance(h, dict):
                                u = h.get("url")
                                if isinstance(u, str) and u.strip():
                                    urls.append(u.strip())
                    # 情况2：兼容直接的单个 url 字段
                    u_single = data.get("url")
                    if isinstance(u_single, str) and u_single.strip():
                        urls.append(u_single.strip())
                # 情况3：兼容字符串形式的 URL
                elif isinstance(data, str):
                    s = data.strip()
                    if s.startswith(("http://", "https://")):
                        urls.append(s)

        # 先去重再保存 checkpoint（原子写）
        save_urls_ckpt(ckpt_path, urls)

    # 去重（冗余保险，checkpoint 已去重）
    if urls:
        deduped_urls = list(dict.fromkeys(urls))
        try:
            extracted_contents = asyncio.run(extract_contents(deduped_urls))
        except Exception as e:
            print(f"[ai_sdk_generate] extract error: {e}")

    if not extracted_contents or len(extracted_contents) == 0:
        print("警告：没有提取到有效内容，跳过生成步骤")
        return

    total_content_length = sum(len(str(item.get('main_content', ''))) for item in extracted_contents)
    if total_content_length < 100:  # 内容太少
        print(f"警告：内容长度不足 ({total_content_length} 字符)，可能影响生成质量")

    print(f"collected_urls: {urls}")
    print(f"unique_urls: {list(dict.fromkeys(urls))}")
    print(f"extracted_contents_count: {len(extracted_contents)}")
    # Only print first two items from extracted_contents
    print(f"extracted_contents (first 2 items): {extracted_contents[:2]}")
    print("--------------------------------------")

    # 在传递给AI模型前过滤错误数据
    valid_contents = []
    for item in extracted_contents:
        # 跳过标记为错误的数据项
        if item.get('error', False):
            print(f"跳过错误数据项: {item.get('title', 'Unknown')}")
            continue
        # 确保必要字段存在
        if 'main_content' in item and str(item['main_content']).strip():
            valid_contents.append(item)
        else:
            print(f"跳过无效内容: {item.get('title', 'Unknown')}")

    print(f"有效数据项: {len(valid_contents)}/{len(extracted_contents)}")

    if len(valid_contents) == 0:
        print("没有有效数据，无法生成报告")
        return
    print("--------------------------------------")

    article = generate_object(
        model=openai(
            model=ZAI_PROVIDER,
            api_key=ZAI_API_TOKEN,
            base_url=ZAI_MODEL_URL,
            temperature=TEMPERATURE,
        ),
        schema=Articles,
        prompt=topic,
        system=RESULT_PROMPT.format(entries=_ensure_json_str(valid_contents)),
    )

    article_obj = getattr(article, "object", None)
    if article_obj is None:
        print("[error] article.object is None (schema mismatch or provider error)")
        return

    try:
        data = article_obj.model_dump()
    except Exception:
        data = article_obj.dict() if hasattr(article_obj, "dict") else str(article_obj)

    print(f"article: {data}")
    print("--------------------------------------")

    # 安全写出为文本：data 若非字符串，则转为 JSON 文本
    if isinstance(data, (dict, list)):
        out_text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        out_text = str(data)

    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write(out_text)

    # 成功后删除 checkpoint（如需保留可改为受参数控制）
    remove_ckpt_silent(ckpt_path)

if __name__ == "__main__":
    main()
