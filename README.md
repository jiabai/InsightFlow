# InsightFlow

InsightFlow 是一个帮助自媒体/知识工作者进行深度阅读与思考的项目，包含：
- Chrome 扩展（前端）：提取网页主体内容，提供沉浸式阅读与侧边栏问题/回答面板
- 知识处理服务（后端，FastAPI）：接收 Markdown 文档，分块、调用 LLM 生成启发式问题，存储与查询

当前仓库状态说明（重要）：
- 前端代码位于 fe/*，但 Vite 构建配置与 npm 脚本默认指向 src/*。需按本文档“前端构建修复”章节调整后再构建。
- 前端默认使用“本地模拟 API”（fe/services/apiService.js），与后端解耦即可单独体验。如果需要联动后端，请参见“接入真实后端 API”。

## 目录结构

```
.
├─ fe/                       # Chrome 扩展前端源码（实际生效的前端目录）
│  ├─ background/            # Manifest V3 service_worker
│  ├─ content/               # 内容脚本：主体提取、沉浸式阅读、侧边栏
│  ├─ popup/                 # 扩展弹窗页面
│  ├─ assets/                # 图标与样式
│  └─ services/apiService.js # 默认：本地模拟问题/回答
│
├─ be/                       # 后端：FastAPI 知识处理服务
│  ├─ api_services/
│  │  ├─ api_services_main.py   # FastAPI 入口（uvicorn 可直接运行）
│  │  ├─ file_routes.py         # 文件/问题相关 REST 路由
│  │  ├─ shared_resources.py    # 数据库/Redis/存储初始化与生命周期
│  │  └─ fastapi_logger.py
│  ├─ common/                # MySQL/Redis/存储 抽象与实现
│  │  ├─ database_manager.py    # MySQL 连接/模型/CRUD（注意：含默认硬编码连接）
│  │  ├─ redis_manager.py       # aioredis 连接与文件状态管理（支持环境变量覆盖）
│  │  ├─ storage_manager.py     # 本地/OSS 存储选择（STORAGE_TYPE）
│  │  ├─ local_storage.py
│  │  └─ oss_storage.py
│  ├─ llm_knowledge_processing/ # 文档分块、LLM 生成问题、流水线服务
│  │  ├─ knowledge_processing_service.py
│  │  ├─ markdown_splitter.py
│  │  ├─ question_generator.py
│  │  ├─ llm_client.py
│  │  ├─ llm_config_manager.py  # LLM 提供商与模型配置（代码内）
│  │  └─ config_manager.py
│  ├─ scripts/               # OpenAPI 生成脚本
│  └─ tests/                 # 后端测试样例
│
├─ vite.config.js            # Vite 构建配置（需按“前端构建修复”调整为 fe/*）
├─ package.json              # npm scripts（需修复 copy-static 与静态资源拷贝）
├─ requirements.txt          # 后端依赖
├─ README.md
└─ upload_file/              # 本地存储模式的上传文件目录（默认）
```



## 快速开始

### 后端（FastAPI）最小可运行

前置条件：
- Python 3.10+（建议）
- MySQL 实例可用
- Redis 实例可用

重要默认值与注意：
- MySQL 连接在 be/common/database_manager.py 中硬编码为：
  mysql+aiomysql://root:123456@192.168.31.233/{DB_NAME}?charset=utf8mb4
  - 仅 DB_NAME 可通过环境变量覆盖（默认 insight_flow）
  - 如你的 MySQL 不在 192.168.31.233，或账户/密码不同，请修改该文件或将服务部署到相符环境
- Redis 连接默认 REDIS_HOST=192.168.31.233, REDIS_PORT=6379，可通过环境变量覆盖
- 存储默认使用本地目录 ./upload_file（可通过 STORAGE_TYPE/LOCAL_STORAGE_BASE_DIR 调整）

安装依赖：
```bash
python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

初始化与启动（自动建表，无需手工迁移）：
```bash
# 方式一（推荐开发态）：
python -m uvicorn be.api_services.api_services_main:app --host 0.0.0.0 --port 8000

# 方式二（直接运行入口模块）：
python be/api_services/api_services_main.py
```

验证：
- 打开 http://localhost:8000/docs 可见 Swagger UI
- 首次启动会自动创建 MySQL 表（file_metadata/chunks/questions）
- 日志写入 be/api_services/api_services_main.py 指定的 api_services.log（由 fastapi_logger 配置）



### 前端（Chrome 扩展）最小可运行

当前仓库的 Vite 配置与前端源码目录不一致（vite.config.js 指向 src/*；实际代码在 fe/*）。
请选择其一：

方案A（推荐）：修复构建配置
1) 修改 vite.config.js 的入口为 fe/*：
```js
// vite.config.js
import { defineConfig } from 'vite';
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        background: './fe/background/index.js',
        content: './fe/content/index.js'
      },
      output: { entryFileNames: `[name].js` }
    },
    minify: false
  }
});
```

2) 修改 package.json 的 scripts，正确拷贝静态资源与清单：
```json
{
  "scripts": {
    "build": "vite build && npm run copy-static",
    "copy-static": "cpx \\"fe/assets/**/*\\" dist/assets && cpx \\"fe/manifest.json\\" dist && cpx \\"fe/popup/popup.html\\" dist/popup"
  },
  "devDependencies": {
    "cpx": "^1.2.1",
    "vite": "^7.0.0",
    "rollup-plugin-copy": "^3.5.0"
  }
}
```

3) 构建并在 Chrome 加载扩展：
```bash
npm install
npm run build
# Chrome: chrome://extensions -> 开发者模式 -> 加载已解压扩展 -> 选择 dist 目录
```

方案B（临时）：将 fe/* 复制为 src/* 再构建
- 将 fe/background、fe/content、fe/popup、fe/assets 按相同结构复制到 src/*
- 将 fe/manifest.json 复制到 dist
- 将 fe/popup/popup.html 复制到 dist/popup/popup.html
- 构建：npm install && npm run build
该方案仅用于临时验证，后续仍建议按方案A修复脚本与配置



## 接入真实后端 API（替换默认本地模拟逻辑）

当前前端的 fe/services/apiService.js 使用“模拟 API”生成问题与答案，便于前端独立演示。若需要联动后端，请替换为真实请求，例如：

```javascript
// fe/services/apiService.js
const BASE_URL = "http://localhost:8000";

async function uploadMarkdown(userId, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/upload/${encodeURIComponent(userId)}`, {
    method: "POST",
    body: form
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function triggerGenerate(userId, fileId) {
  const res = await fetch(`${BASE_URL}/questions/generate/${encodeURIComponent(userId)}/${encodeURIComponent(fileId)}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function getFileStatus(fileId) {
  const res = await fetch(`${BASE_URL}/file_status/${encodeURIComponent(fileId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { file_id, status }
}

async function getQuestions(fileId) {
  const res = await fetch(`${BASE_URL}/questions/${encodeURIComponent(fileId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { file_id, questions: [{question,label,chunk_id}, ...] }
}

export { uploadMarkdown, triggerGenerate, getFileStatus, getQuestions };
```

前端流程参考：
1) 选择/拖拽上传 Markdown（调用 uploadMarkdown）
2) 返回 file_id 后，手动触发生成（调用 triggerGenerate）
3) 轮询 file_status 为 Completed（调用 getFileStatus）
4) 获取问题列表（调用 getQuestions）并展示



## 架构与数据流

原理（简述）：
- 前端：内容脚本提取页面主体，提供沉浸式阅读，并在侧栏展示问题/回答。当前默认用本地模拟问题/回答。
- 后端：接收 Markdown，保存到存储，记录元数据到 MySQL，通过后台任务调用 LLM 按分块生成问题，入库并使用 Redis 记录处理进度，供前端轮询。

架构图：
```mermaid
flowchart TD
  subgraph Chrome_Extension
    A[Content Script] --> B[Sidebar UI]
    C[Background SW]
  end
  A -->|提取/上传| D[FastAPI API]
  B -->|触发生成/查询| D
  C -->|通知| B

  D -->|异步任务| E[KnowledgeProcessingService]
  E --> F[LLM Provider]
  E --> G[(MySQL)]
  E --> H[(Redis 状态)]
  E --> I[(本地/OSS 存储)]

  H -->|状态轮询| B
  G -->|问题结果| B

  classDef dark fill:#0b3d91,stroke:#f5f5f5,color:#ffffff;
  class A,B,C,D,E,F,G,H,I dark;
```

处理流水线时序：
```mermaid
sequenceDiagram
  participant CS as Content Script
  participant API as FastAPI
  participant KPS as KnowledgeProcessingService
  participant R as Redis
  participant DB as MySQL
  participant ST as Storage
  participant LLM as LLM

  CS->>API: POST /upload/{user_id} (multipart file)
  API->>ST: 保存原文件
  API->>DB: 保存元数据
  API->>R: set status=Pending
  CS->>API: POST /questions/generate/{user_id}/{file_id}
  API->>KPS: 启动后台任务
  KPS->>ST: 读取文件
  KPS->>KPS: Markdown 分块
  KPS->>LLM: 为每个分块生成问题
  KPS->>DB: 保存 chunks & questions
  KPS->>R: set status=Completed
  CS->>API: GET /file_status/{file_id}
  API-->>CS: {status: Completed}
  CS->>API: GET /questions/{file_id}
  API-->>CS: {questions: [...]}
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
  - 返回: { file_id, questions: [{question,label,chunk_id}, ...] }

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
  - 其余：在 be/common/database_manager.py 中硬编码（host=192.168.31.233, user=root, password=123456），请按需修改源码或提供相符环境
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
- LLM 提供商与模型（代码内配置）
  - 参见 be/llm_knowledge_processing/llm_config_manager.py 与 config_manager.py
  - 支持多提供商（如 OpenAI、Ollama、智谱、SiliconFlow 等），在代码中设置 API Key / Base URL / 模型名称

前端权限（manifest.json）：
- permissions: notifications, activeTab, scripting, storage, tabs
- content_scripts: matches ["<all_urls>"]
- background: service_worker background/index.js
- action/popup: popup/popup.html



## 开发与调试

后端：
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（开发）
python -m uvicorn be.api_services.api_services_main:app --host 0.0.0.0 --port 8000

# 启动服务（生产）
gunicorn -w 4 -k uvicorn.workers.UvicornWorker be.api_services.api_services_main:app --bind 0.0.0.0:8000

# 查看交互文档
open http://localhost:8000/docs
```

前端：
```bash
npm install
npm run build
# 加载 dist 到 Chrome（开发者模式）
```

调试建议：
- 后端日志：be/api_services/api_services_main.py 中 fastapi_logger 输出到 api_services.log
- Redis：使用 CLI 观察 file_id 对应状态键
- MySQL：检查三张表 file_metadata / chunks / questions
- CORS：后端已允许 *（GET/POST，allow_credentials=False）



## 常见问题（Troubleshooting）

- 前端构建后加载扩展报“缺少 service_worker/content 脚本”
  - 说明静态资源或入口未正确复制，按“前端构建修复”修改 vite.config.js 与 package.json 的 copy-static
- /questions/{file_id} 返回 500 或空
  - 需等 /file_status/{file_id} 为 Completed 后再请求
  - 确认数据库中 chunks 与 questions 已生成
- MySQL 连接失败
  - 默认硬编码地址/账号可能与你环境不符，修改 be/common/database_manager.py 中 database_url
- Redis 连接失败
  - 通过 REDIS_HOST/REDIS_PORT 环境变量覆盖默认 192.168.31.233:6379
- 本地存储无权限/路径不存在
  - 修改 LOCAL_STORAGE_BASE_DIR 或确保进程有写权限
- Windows 复制脚本
  - 示例使用 cpx 跨平台复制；如使用 copy/xcopy，注意转义与目标路径存在性
- 生产部署
  - 建议使用反向代理（Nginx）+ 守护进程（如 systemd/supervisor）运行 uvicorn 多 worker
  - gunicorn 未在 requirements.txt 中固定，需自行添加后再使用 gunicorn -k uvicorn.workers.UvicornWorker



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
   - 预期：返回 {file_id, questions:[{question,label,chunk_id}...]}，长度≥1

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

9. 前端模拟 API 功能验证
   - 操作：在任意页面选中文本，侧边栏生成问题并点选问题生成回答
   - 预期：5~7 个问题随机，回答非空（由本地匹配/随机逻辑产生）

10. 前端接入真实后端（改造后）
   - 操作：选择本地 Markdown，上传→触发→轮询→展示问题
   - 预期：侧边栏展示来自后端 DB 的问题数据，状态变化与后端一致



## 贡献

- 欢迎提交 Issue / PR
- 变更前请先运行基本测试（后端 pytest），并更新相关文档
- 代码风格保持简单清晰，优先最小必要修改



## 许可证

本项目使用 ISC 许可证，详见 [LICENSE](LICENSE)



## 变更记录（相对旧版 README 的主要修订）

- 修正后端启动方式为 uvicorn（仓库未固定 gunicorn 依赖）
- 标注 MySQL/Redis 默认连接的真实来源（含硬编码风险）
- 指出前端构建脚本与目录不一致问题，提供推荐修复方案
- 明确前端默认为“本地模拟 API”，并提供接入后端的示例实现
- 新增架构与时序 mermaid 图、API 样例、故障排查与测试用例