          
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
    - JavaScript (ES6+) 模块化开发
    - Chrome Extension API (Manifest V3)
    - Vite 构建工具
    - 智能内容提取算法
    - 沉浸式阅读界面
- **后端**:
    - Python 3.x
    - SQLAlchemy (MySQL数据库ORM)
    - Redis (状态管理和缓存)
    - FastAPI (Web框架)
    - 多LLM提供商支持 (OpenAI, Ollama, 智谱AI, SiliconFlow)
    - 文件存储管理 (本地存储/OSS)

## 安装与使用

### 后端服务

1.  **环境配置**: 确保Python环境已安装，并设置好MySQL和Redis服务。
2.  **安装依赖**: `pip install -r requirements.txt`。
3.  **运行服务**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker be.api_services.api_services_main:app --bind 0.0.0.0:8000 --daemon`

### 前端扩展

1.  **安装依赖**: `npm install`
2.  **构建项目**: `npm run build`
3.  **加载扩展**:
    - 打开Chrome，访问 `chrome://extensions/`
    - 启用“开发者模式”
    - 点击“加载已解压的扩展程序”，选择 `dist` 目录。

## 核心特性

### 智能内容提取
- 支持多种网页结构的内容识别
- 自动过滤广告、导航等无关内容
- 保持原文格式和结构完整性

### 沉浸式阅读体验
- 全屏无干扰阅读模式
- 优化的字体和排版
- 可自定义的阅读环境

### 多LLM提供商支持
- OpenAI GPT系列
- Ollama 本地模型
- 智谱AI (GLM系列)
- SiliconFlow 云服务
- 可扩展的LLM配置管理

### 高效的知识处理
- 智能Markdown文档分块
- 基于内容的问题生成
- Redis缓存加速处理
- MySQL持久化存储

### 知识库功能（todo）
- **知识存储与管理**: 将上传的Markdown文件、生成的话题点和深度回答统一导入知识库进行存储和管理。
- **内容关联与检索**: 支持对知识库中的内容进行高效的关联和检索，方便用户快速查找相关信息。
- **知识复用**: 促进已生成内容的复用，为后续的话题探索提供基础。

### 联网搜索功能（todo）
- **深度话题探索**: 针对特定话题点，提供联网搜索能力，获取最新、最全面的信息。
- **信息整合**: 自动整合搜索结果，辅助用户进行更深入的分析和思考。
- **实时信息获取**: 确保用户在探索新话题时能够获取到实时的外部信息支持。

### 内网穿透式部署（todo）
- 使用一台低配云主机直通外网，服务部署在家庭电脑上，与云主机联通构成内网穿透，成本超级低，数据安全有保障

## 配置说明

### 环境变量配置
```bash
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# MySQL配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=insight_flow
DB_USER=your_username
DB_PASSWORD=your_password

# LLM配置 (在代码中配置)
LLM_PROVIDER=siliconflow  # openai, ollama, zhipu, siliconflow
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=Qwen/Qwen3-30B-A3B
```

### Chrome扩展权限
- `activeTab`: 访问当前活动标签页
- `scripting`: 执行内容脚本
- `storage`: 本地数据存储
- `notifications`: 显示通知
- `tabs`: 标签页管理

## 开发指南

### 前端开发
```bash
# 安装依赖
npm install

# 开发模式构建
npm run build

# 复制静态文件
npm run copy-static
```

### 后端开发
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r be/requirements.txt

# 运行测试
pytest be/tests/

# 启动API服务
gunicorn -w 4 -k uvicorn.workers.UvicornWorker be.api_services.api_services_main:app --bind 0.0.0.0:8000 --daemon

# 启动知识处理服务
python -m be.llm_knowledge_processing.knowledge_processing_main
```

### 调试技巧
- 使用Chrome开发者工具调试扩展
- 查看 `be/logs/app.log` 获取后端日志
- 使用Redis CLI监控缓存状态
- 通过MySQL客户端检查数据存储

## API接口

### 文件管理API
- `POST /upload/{user_id}` - 上传Markdown文件
- `GET /files/{user_id}/{file_id}` - 获取文件信息
- `DELETE /files/{user_id}/{file_id}` - 删除文件
- `GET /file_status/{file_id}` - 获取处理状态

### 问题生成API
- `GET /questions/{file_id}` - 获取生成的问题
- `POST /questions/generate/{file_id}` - 手动触发问题生成

## 注意事项

- 后端服务中的LLM API密钥需要替换为您自己的有效密钥
- 确保MySQL和Redis服务正常运行
- Chrome扩展需要在开发者模式下加载
- 建议使用Python 3.8+版本
- 首次运行前需要初始化数据库表结构

## 贡献指南

欢迎提交Issue和Pull Request来改进项目！

### 提交规范
- 使用清晰的提交信息
- 遵循现有的代码风格
- 添加必要的测试用例
- 更新相关文档

## 许可证

本项目采用 ISC 许可证，详见 [LICENSE](LICENSE) 文件。
