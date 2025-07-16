# 领域树 (DomainTree) 代码提取

本文件夹包含从 easy-dataset 项目中提取的领域树相关代码，用于构建、管理和展示领域知识树结构。

## 文件结构

```
test/
├── README.md                           # 说明文档
├── domain-tree-core.js                 # 领域树核心处理模块
├── components/                          # React 组件
│   ├── DomainAnalysis.js               # 领域分析主组件
│   ├── DomainTreeView.js               # 领域树视图组件
│   └── DomainTreeActionDialog.js       # 领域树操作对话框
├── prompts/                             # LLM 提示词
│   ├── label.js                        # 标签生成提示词（中文）
│   └── labelRevise.js                  # 标签修订提示词
├── database/                            # 数据库操作
│   └── tags.js                         # 标签数据库操作
└── utils/                               # 工具函数
    └── file-utils.js                   # 文件处理工具
```

## 核心功能

### 1. 领域树处理核心 (`domain-tree-core.js`)

主要功能：
- **重建领域树** (`rebuild`): 基于文档目录结构重新生成完整的领域树
- **修订领域树** (`revise`): 在现有领域树基础上进行增量更新
- **保持不变** (`keep`): 保持现有领域树结构不变

核心函数：
```javascript
handleDomainTree({
  projectId,        // 项目ID
  action,          // 操作类型: 'rebuild', 'revise', 'keep'
  allToc,          // 所有文档的目录结构
  newToc,          // 新增文档的目录结构
  model,           // LLM模型信息
  language,        // 语言设置
  deleteToc,       // 删除的文档目录
  project          // 项目配置信息
})
```

### 2. LLM 提示词 (`prompts/`)

#### 标签生成提示词 (`label.js`)
- 用于首次生成领域树
- 基于文档目录结构分析核心主题
- 构建两级分类体系（一级5-10个，二级1-10个）
- 输出标准JSON格式

#### 标签修订提示词 (`labelRevise.js`)
- 用于增量更新现有领域树
- 支持新增内容和删除内容的处理
- 保持领域树结构稳定性
- 智能合并和调整标签

### 3. 数据库操作 (`database/tags.js`)

主要功能：
- `getTags(projectId)`: 获取项目的标签树
- `createTag(projectId, label, parentId)`: 创建单个标签
- `updateTag(label, id)`: 更新标签
- `deleteTag(id)`: 删除标签及其子标签
- `batchSaveTags(projectId, tags)`: 批量保存标签树

### 4. React 组件 (`components/`)

#### DomainAnalysis.js
- 领域分析主组件
- 包含标签树展示和目录结构展示
- 支持标签的增删改操作
- 提供交互式的树形界面

#### DomainTreeView.js
- 简化的树形视图组件
- 使用 Material-UI TreeView
- 支持展开/折叠操作

#### DomainTreeActionDialog.js
- 领域树操作选择对话框
- 提供三种操作选项：修订、重建、保持不变
- 根据是否首次上传显示不同选项

### 5. 工具函数 (`utils/file-utils.js`)

- `getFileMD5(filePath)`: 计算文件MD5值
- `filterDomainTree(tree)`: 过滤领域树，移除数据库字段

## 使用流程

### 1. 首次生成领域树

```javascript
const tags = await handleDomainTree({
  projectId: 'project-123',
  action: 'rebuild',
  allToc: documentToc,
  model: llmModel,
  language: '中文',
  project: { globalPrompt, domainTreePrompt }
});
```

### 2. 增量更新领域树

```javascript
const tags = await handleDomainTree({
  projectId: 'project-123',
  action: 'revise',
  allToc: allDocumentToc,
  newToc: newDocumentToc,
  deleteToc: deletedDocumentToc,
  model: llmModel,
  language: '中文',
  project: { globalPrompt, domainTreePrompt }
});
```

### 3. 前端展示

```jsx
import DomainAnalysis from './components/DomainAnalysis';

<DomainAnalysis
  projectId="project-123"
  toc={documentToc}
  loading={false}
/>
```

## 数据结构

### 领域树标签格式

```json
[
  {
    "label": "1 机器学习",
    "child": [
      {"label": "1.1 深度学习"},
      {"label": "1.2 强化学习"}
    ]
  },
  {
    "label": "2 数据处理"
  }
]
```

### 数据库标签结构

```javascript
{
  id: "tag-id",
  projectId: "project-id",
  label: "标签名称",
  parentId: "parent-tag-id", // 可选，顶级标签为null
  questionCount: 10,          // 关联问题数量
  child: []                   // 子标签数组
}
```

## 依赖说明

### 后端依赖
- Node.js
- Prisma (数据库ORM)
- LLM客户端 (用于调用大语言模型)

### 前端依赖
- React
- Material-UI (@mui/material, @mui/lab)
- react-i18next (国际化)
- axios (HTTP请求)

## 注意事项

1. **LLM模型要求**: 需要支持JSON格式输出的大语言模型
2. **数据库结构**: 需要预先创建 `tags` 和 `questions` 表
3. **权限控制**: 建议在生产环境中添加适当的权限验证
4. **错误处理**: 代码中包含基本错误处理，可根据需要扩展
5. **性能优化**: 对于大型项目，可考虑添加缓存机制

## 扩展建议

1. **多语言支持**: 添加更多语言的提示词模板
2. **可视化增强**: 集成更丰富的树形可视化组件
3. **导入导出**: 支持领域树的导入导出功能
4. **版本管理**: 添加领域树的版本控制功能
5. **协作编辑**: 支持多用户协作编辑领域树