          
# InsightFlow

InsightFlow是一个Chrome浏览器扩展，旨在通过生成启发式问题和深度回答，帮助自媒体从业者根据热门网页内容更深入地思考并产生新的话题点。该扩展提供沉浸式阅读体验，并能基于页面内容智能生成相关问题，促进批判性思考和深度理解。

## 项目组成

本项目由两部分组成：

1.  **前端Chrome扩展** (`fe` 目录): 一个Chrome浏览器扩展，负责提取网页内容、提供沉浸式阅读模式，并与后端服务交互以展示生成的问题。
2.  **后端知识处理服务** (`be` 目录): 一个Python服务，负责处理Markdown文件，将其分割成块，使用LLM（大语言模型）为每个块生成问题，并将结果存储在数据库中。

## 主要功能

### 前端

- **智能内容提取**: 自动识别并提取网页主要内容，过滤无关信息。
- **沉浸式阅读**: 提供无干扰的阅读环境，优化排版和视觉体验。
- **启发式问题生成**: 基于页面内容生成高质量思考问题，促进深度理解。
- **用户友好界面**: 简洁直观的操作界面，在侧边栏展示问题与回答。

### 后端

- **文件轮询处理**: 自动监控指定目录，对新上传的Markdown文件进行处理。
- **文本分块**: 将大型Markdown文件分割成适合LLM处理的较小文本块。
- **问题生成**: 调用大语言模型（例如Qwen）为文本块生成深刻的问题。
- **状态管理**: 使用Redis跟踪每个文件的处理状态（如处理中、已完成、失败）。
- **数据持久化**: 使用MySQL存储文件元数据、文本块和生成的问题。

## 技术栈

- **前端**:
    - JavaScript (ES6+)
    - Chrome Extension API (Manifest V3)
    - Vite
- **后端**:
    - Python
    - SQLAlchemy (MySQL)
    - Redis
    - SiliconFlow (for LLM access)

## 安装与使用

### 后端服务

1.  **环境配置**: 确保Python环境已安装，并设置好MySQL和Redis服务。
2.  **安装依赖**: `pip install -r requirements.txt`。
3.  **运行服务**: `python be/llm_knowledge_processing/knowledge_processing_service.py`

### 前端扩展

1.  **安装依赖**: `npm install`
2.  **构建项目**: `npm run build`
3.  **加载扩展**:
    - 打开Chrome，访问 `chrome://extensions/`
    - 启用“开发者模式”
    - 点击“加载已解压的扩展程序”，选择 `dist` 目录。

## 项目结构

```
insight-flow/
├── be/                   # 后端服务
│   ├── llm_knowledge_processing/ # 核心知识处理逻辑
│   └── ...
├── fe/                   # 前端源码 (Vite项目)
│   ├── background/       # Service Worker
│   ├── content/          # 内容脚本
│   └── popup/            # 弹出页面
├── src/                  # 旧的前端源码 (可能需要清理)
├── dist/                 # 构建输出目录
├── package.json          # 前端依赖和脚本
├── vite.config.js        # Vite构建配置
└── README.md             # 本文档
```

## 注意事项

- 后端服务中的LLM API密钥需要替换为您自己的有效密钥。
