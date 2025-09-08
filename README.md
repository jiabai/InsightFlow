# InsightFlow

InsightFlow 是一个帮助自媒体/知识工作者进行深度阅读与思考的项目，包含：
- 浏览器扩展（前端，WXT + Vue3）：提取网页主体内容，提供沉浸式阅读与侧边栏问题/回答面板
- 知识处理服务（后端，FastAPI）：接收 Markdown 文档，分块、调用 LLM 生成启发式问题，存储与查询

本 README 与仓库当前源码结构完全对齐（前端位于 src/fe，后端位于 src/be，前端使用 WXT 而非 Vite）。


## 目录结构

```
.
├─ src/
│  ├─ fe/                        # 浏览器扩展前端（WXT + Vue3）
│  │  ├─ entrypoints/
│  │  │  ├─ popup/               # 扩展弹窗
│  │  │  └─ services/
│  │  │     └─ apiService.ts     # 前端 API 封装（可切换模拟/真实后端）
│  │  ├─ public/                 # 扩展图标与静态资源（wxt.publicDir）
│  │  ├─ wxt.config.ts           # WXT 配置（清单、权限、CSP、别名等）
│  │  ├─ package.json            # 前端脚本（wxt dev/build/zip）
│  │  └─ ...                     # 组件、hooks、utils、extractors、immersive 等
│  │
│  └─ be/                        # 后端：FastAPI 知识处理服务
│     ├─ api_services/
│     │  ├─ api_services_main.py   # FastAPI 入口（uvicorn --app-dir src）
│     │  ├─ file_routes.py         # 文件/问题/LLM 流式等 REST 路由
│     │  └─ shared_resources.py    # 资源初始化（DB/Redis/存储/日志/异步任务）
│     ├─ common/                   # MySQL/Redis/存储 抽象与实现
│     │  ├─ database_manager.py    # MySQL 连接/模型/CRUD（注意：含硬编码连接）
│     │  ├─ redis_manager.py       # aioredis 连接与文件状态管理（可环境变量覆盖）
│     │  ├─ storage_manager.py     # 本地/OSS 存储选择（STORAGE_TYPE）
│     │  ├─ local_storage.py
│     │  └─ oss_storage.py
│     ├─ llm_knowledge_processing/ # 文档分块、LLM 生成问题、流水线服务
│     │  ├─ knowledge_processing_service.py
│     │  ├─ markdown_splitter.py
│     │  ├─ question_generator.py
│     │  ├─ llm_client.py
│     │  ├─ llm_config_manager.py
│     │  └─ config_manager.py
│     ├─ scripts/                  # OpenAPI 生成脚本
│     └─ tests/                    # 后端测试样例
│
├─ ai_sdk/                       # 可编辑安装的 SDK 子项目（pip install -e ai_sdk）
├─ requirements.txt              # 后端依赖
├─ README.md
└─ LICENSE
```

提示：WXT 构建产物默认位于 .output/ 下（按浏览器区分，如 .output/chrome-mv3）。


## 快速开始

### 后端（FastAPI）最小可运行

前置条件：
- Python 3.10+
- 可用的 MySQL、Redis 实例

重要默认值与注意：
- MySQL 连接在 src/be/common/database_manager.py 中硬编码为：
  mysql+aiomysql://root:123456@192.168.31.233/{DB_NAME}?charset=utf8mb4
  - 仅 DB_NAME 可通过环境变量覆盖（默认 insight_flow）
  - 如你的 MySQL 地址/账户/密码不同，请修改源码或提供相符环境
- Redis 连接默认 REDIS_HOST=192.168.31.233, REDIS_PORT=6379（可通过环境变量覆盖）
- 存储默认使用本地目录 ./upload_file（可通过 STORAGE_TYPE/LOCAL_STORAGE_BASE_DIR 调整）

安装依赖：
```bash
python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
# 可选：安装子项目 SDK（可编辑方式）
pip install -e ai_sdk
# 或者（如使用 uv）：
# uv pip install -r requirements.txt
# uv pip install -e ai_sdk
```

启动（推荐使用 --app-dir 确保 src 在 sys.path 中）：
```bash
# 开发：
python -m uvicorn be.api_services.api_services_main:app --app-dir src --host 0.0.0.0 --port 8000

# 或直接运行入口模块（同样需要保证 PythonPath 包含 src）：
# PYTHONPATH=src python src/be/api_services/api_services_main.py  # macOS/Linux
# $env:PYTHONPATH="src"; python src/be/api_services/api_services_main.py  # Windows PowerShell
```

验证：
- 打开 http://localhost:8000/docs 可见 Swagger UI
- 首次启动会自动创建 MySQL 表（file_metadata / chunks / questions）
- 日志由 shared_resources/fastapi_logger 配置（查看相关 log 输出）

### 前端（浏览器扩展，WXT + Vue3）

前端位于 src/fe，使用 WXT 脚本（非 Vite）。常用脚本如下：
- dev：启动开发模式（自动打开浏览器并加载扩展）
- build：构建产物到 .output/ 下
- zip：打包为可分发 zip

步骤：
```bash
cd src/fe
npm install
npm run dev        # 开发：WXT 会自动启动并加载扩展
# 或构建后手动加载：
npm run build
# Chrome: chrome://extensions -> 开发者模式 -> 加载已解压扩展 -> 选择 .output/chrome-mv3 目录
# Firefox（如启用 build:firefox）：about:debugging#/runtime/this-firefox -> 临时加载附加组件
```

WXT 权限与清单在 src/fe/wxt.config.ts 中维护：
- permissions: activeTab, scripting, storage, tabs, notifications
- host_permissions: <all_urls>, about:blank
- CSP 对开发端口做了放开，便于调试


## 接入真实后端 API（替换默认本地模拟逻辑）

前端 API 封装位于：
- src/fe/entrypoints/services/apiService.ts

可根据需要，将其从“模拟/本地逻辑”改为请求后端：
```ts
// 示例（可按需调整）
const BASE_URL = "http://localhost:8000";

export async function uploadMarkdown(userId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/upload/${encodeURIComponent(userId)}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function triggerGenerate(userId: string, fileId: string) {
  const res = await fetch(`${BASE_URL}/questions/generate/${encodeURIComponent(userId)}/${encodeURIComponent(fileId)}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getFileStatus(fileId: string) {
  const res = await fetch(`${BASE_URL}/file_status/${encodeURIComponent(fileId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { file_id, status }
}

export async function getQuestions(fileId: string) {
  const res = await fetch(`${BASE_URL}/questions/${encodeURIComponent(fileId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { file_id, questions: [...] }
}
```

前端联动流程参考：
1) 选择/拖拽上传 Markdown（uploadMarkdown）
2) 返回 file_id 后，手动触发生成（triggerGenerate）
3) 轮询 file_status 为 Completed（getFileStatus）
4) 获取问题列表（getQuestions）并展示


## 架构与数据流

原理（简述）：
- 前端（WXT 扩展）：内容脚本提取页面主体，提供沉浸式阅读，并在侧栏展示问题/回答。默认可使用本地/模拟问题/回答以便独立演示。
- 后端：接收 Markdown，保存到存储，记录元数据到 MySQL，通过后台任务调用 LLM 按分块生成问题，入库并使用 Redis 记录处理进度，供前端轮询。

架构图：
```mermaid
flowchart TD
  subgraph Browser_Extension[Browser Extension (WXT)]
    A[Content/Popup UI] --> B[Sidebar/Services]
  end
  B -->|上传/触发/查询| D[FastAPI API]
  A -->|通知/交互| B

  D -->|异步任务| E[KnowledgeProcessingService]
  E --> F[LLM Provider]
  E --> G[(MySQL)]
  E --> H[(Redis 状态)]
  E --> I[(本地/OSS 存储)]

  H -->|状态轮询| B
  G -->|问题结果| B

  classDef dark fill:#0b3d91,stroke:#f5f5f5,color:#ffffff;
  class A,B,D,E,F,G,H,I dark;
```

处理流水线时序：
```mermaid
sequenceDiagram
  participant FE as Extension UI/Service
  participant API as FastAPI
  participant KPS as KnowledgeProcessingService
  participant R as Redis
  participant DB as MySQL
  participant ST as Storage
  participant LLM as LLM

  FE->>API: POST /upload/{user_id} (multipart file)
  API->>ST: 保存原文件
  API->>DB: 保存元数据
  API->>R: set status=Pending
  FE->>API: POST /questions/generate/{user_id}/{file_id}
  API->>KPS: 启动后台任务
  KPS->>ST: 读取文件
  KPS->>KPS: Markdown 分块
  KPS->>LLM: 为每个分块生成问题
  KPS->>DB: 保存 chunks & questions
  KPS->>R: set status=Completed
  FE->>API: GET /file_status/{file_id}
  API-->>FE: {status: Completed}
  FE->>API: GET /questions/{file_id}
  API-->>FE: {questions: [...]}
```


## API 一览（后端实际实现）

- POST /upload/{user_id}
  - form-data: file (UploadFile)
  - 返回: { file_id, filename, size, type, upload_time, stored_filename, status }
- GET /files/
  - 返回: FileMetadataResponse[]
- GET /files/{user_id}
  - query: skip, limit
  - 返回: FileMetadataResponse[]
- GET /files/{user_id}/{file_id}
  - 返回: FileMetadataResponse
- DELETE /delete/{user_id}/{file_id}
  - 返回: { message }
- GET /file_status/{file_id}
  - 返回: { file_id, status }
- GET /download/{user_id}/{file_id}
  - 返回: 文件流（Content-Disposition 附件）
- POST /questions/generate/{user_id}/{file_id}
  - 返回: { message }
- GET /questions/{file_id}
  - 前置：Redis 中状态需为 Completed
  - 返回: { file_id, questions: [{question_id,question,label,chunk_id}, ...] }
- POST /llm/query
  - body: { question_id, chunk_id }
  - 返回: 上游 OpenAI 格式 JSON
- POST /llm/query/stream
  - body: { question_id, chunk_id }
  - 返回: text/event-stream（OpenAI chunk 兼容）

示例（cURL）：
```bash
# 上传文件
curl -F "file=@./README.md" http://localhost:8000/upload/demo_user

# 触发生成
curl -X POST http://localhost:8000/questions/generate/demo_user/<file_id>

# 查询状态
curl http://localhost:8000/file_status/<file_id>

# 获取问题
curl http://localhost:8000/questions/<file_id>

# 删除文件及其数据
curl -X DELETE http://localhost:8000/delete/demo_user/<file_id>
```


## 配置与环境变量

后端主要配置项：
- MySQL（注意：存在硬编码默认值）
  - DB_NAME：数据库名（默认 insight_flow）
  - 其余：在 src/be/common/database_manager.py 中硬编码（host=192.168.31.233, user=root, password=123456）
- Redis
  - REDIS_HOST（默认 192.168.31.233）
  - REDIS_PORT（默认 6379）
  - 状态 TTL 由代码控制（set_file_status 默认 7 天）
- 存储
  - STORAGE_TYPE：local 或 oss（默认 local）
  - LOCAL_STORAGE_BASE_DIR：本地存储根目录（默认 ./upload_file）
  - 若使用 OSS：
    - OSS_ACCESS_KEY_ID
    - OSS_ACCESS_KEY_SECRET
    - OSS_ENDPOINT（默认 http://oss-cn-hangzhou.aliyuncs.com）
    - OSS_BUCKET_NAME
- LLM 提供商与模型（在代码/环境变量中配置）
  - 参考 src/be/llm_knowledge_processing/llm_config_manager.py 与 config_manager.py
  - 示例环境：
    - LLM_API_URL（默认 https://api.siliconflow.cn/v1/）
    - LLM_API_KEY（需自行提供）
    - LLM_MODEL、LLM_TEMPERATURE、OPENAI_MAX_TOKENS 等

前端（WXT）清单/权限：
- 位于 src/fe/wxt.config.ts 的 manifest 块
- 默认 permissions: notifications, activeTab, scripting, storage, tabs
- host_permissions: ["<all_urls>", "about:blank"]
- 扩展页面 CSP 已放开本地开发端口脚本加载限制


## 开发与调试

后端：
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（开发）
python -m uvicorn be.api_services.api_services_main:app --app-dir src --host 0.0.0.0 --port 8000

# 查看交互文档
open http://localhost:8000/docs   # macOS
# Windows: start http://localhost:8000/docs
```

前端（WXT）：
```bash
cd src/fe
npm install
npm run dev
# 或构建后在 Chrome 加载 .output/chrome-mv3 目录
```

调试建议：
- 后端日志：shared_resources/fastapi_logger 输出；必要时提高日志级别
- Redis：使用 CLI 观察 file_id 对应状态键
- MySQL：检查 file_metadata / chunks / questions 三张表
- CORS：后端已允许 *（GET/POST，allow_credentials=False）
- Python 导入：使用 uvicorn --app-dir src 或设置 PYTHONPATH=src，避免 be.* 导入失败


## 常见问题（Troubleshooting）

- ImportError: No module named 'be.api_services...'
  - 使用 uvicorn --app-dir src 或设置 PYTHONPATH=src 再启动
- /questions/{file_id} 返回 500 或空
  - 需等 /file_status/{file_id} 为 Completed 后再请求
  - 确认数据库中 chunks 与 questions 已生成
- MySQL 连接失败
  - 默认硬编码地址/账号可能与你环境不符，修改 src/be/common/database_manager.py 中 database_url 或提供相符环境
- Redis 连接失败
  - 通过 REDIS_HOST/REDIS_PORT 环境变量覆盖默认 192.168.31.233:6379
- 本地存储无权限/路径不存在
  - 调整 LOCAL_STORAGE_BASE_DIR 或确保进程有写权限
- 浏览器扩展加载异常（资源/脚本找不到）
  - WXT 模式下无需手工复制静态资源；使用 npm run dev 或从 .output/ 目录加载
- 生产部署
  - 建议：Nginx 反向代理 + 多 worker（uvicorn/gunicorn）+ 进程守护（systemd/supervisor）
  - 如使用 gunicorn：需自行加入依赖（requirements 未固定），并使用 -k uvicorn.workers.UvicornWorker


## 10 组测试用例（含预期结果）

1. 上传同一用户的同名文件两次
   - 操作：POST /upload/{user} 两次，文件相同
   - 预期：第二次返回 status=File Already exists，file_id 与第一次一致

2. 上传后立即获取状态
   - 操作：POST /upload → GET /file_status/{file_id}
   - 预期：status=Pending 或 Processing

3. 触发生成任务并轮询至完成
   - 操作：POST /questions/generate → 间隔 2s GET /file_status
   - 预期：最终 status=Completed

4. 生成完成后获取问题
   - 操作：GET /questions/{file_id}
   - 预期：返回 {file_id, questions:[{question_id,question,label,chunk_id}...]}，长度≥1

5. 获取指定用户的文件清单
   - 操作：GET /files/{user_id}?skip=0&limit=50
   - 预期：返回该用户上传过的文件元数据数组，字段齐全

6. 获取所有文件清单（全局）
   - 操作：GET /files/
   - 预期：返回所有文件的元数据数组

7. 下载文件
   - 操作：GET /download/{user}/{file_id}
   - 预期：响应 200，包含附件头 Content-Disposition，流长度>0

8. 删除文件及数据
   - 操作：DELETE /delete/{user}/{file_id}
   - 预期：返回 message=File ... deleted successfully；数据库中对应 chunks/questions 级联清理；Redis 状态删除

9. 前端 WXT 开发模式验证
   - 操作：src/fe 运行 npm run dev，打开扩展 UI，进行上传/触发/轮询/获取问题的端到端流程（后端需先启动）
   - 预期：UI 可见状态变化，问题列表非空

10. 前端接入真实后端（修改 apiService.ts）
   - 操作：将 BASE_URL 指向后端；上传→触发→轮询→展示问题
   - 预期：侧边栏/弹窗展示来自后端 DB 的问题数据，状态变化与后端一致


## 贡献

- 欢迎提交 Issue / PR
- 变更前请先运行基本测试（后端 pytest），并更新相关文档
- 代码风格保持简单清晰，优先最小必要修改


## 许可证

本项目使用 ISC 许可证，详见 [LICENSE](LICENSE)


## 变更记录（相对旧版 README 的主要修订）

- 将前端构建说明从 Vite/cpx 更正为 WXT（src/fe 下的 wxt.config.ts 与 npm scripts）
- 修正后端启动命令，推荐 uvicorn --app-dir src 以保证 be.* 导入
- 明确 MySQL/Redis 默认连接的硬编码位置与环境变量覆盖范围
- 补充 LLM 同步/流式查询接口说明
- 更新目录结构、架构与时序 mermaid 图、故障排查与测试用例