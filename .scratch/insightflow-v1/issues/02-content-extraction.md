# 02 — 扩展 - 内容提取

Status: ready-for-agent

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

InsightFlow 的入口：用户点击扩展图标后，Content Script 从当前浏览的网页中智能提取主内容并转换为 Markdown。

- 通过 CSS 选择器（`main`, `article`, `#main-content`, `.post-content` 等）+ 启发式分析定位页面主内容区域
- 移除导航栏、广告、侧边栏等干扰元素
- 使用 Turndown 库将提取的 HTML 转换为干净的 Markdown
- 兼容主流网站结构（新闻、博客、技术文档、论坛）
- 提取结果传入下一阶段的沉浸式阅读模式

## Acceptance criteria

- [ ] 能在标准博客文章（如 Medium）上正确提取主内容
- [ ] 能在技术文档页面（如 MDN、官方文档）上正确提取
- [ ] 能在知乎、微信公众号等中文平台页面上正确提取
- [ ] 提取结果中不包含导航栏、页脚、广告、侧边栏内容
- [ ] 提取结果为完整的 Markdown 格式（保留标题层级、列表、链接）
- [ ] 无法提取内容时返回明确的错误描述（而非空结果或崩溃）

## Blocked by

- `01-test-infra` — 需要在测试基础设施就绪后进行
