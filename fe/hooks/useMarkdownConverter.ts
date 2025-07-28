import { ref } from 'vue'
import { browser } from 'wxt/browser'
import Turndown from 'turndown'
import { Readability } from '@mozilla/readability'
import Defuddle from 'defuddle'
import { getOptions } from '@/lib/storage'
import { defaultTagsToRemove } from '@/lib/tagsToRemove'

/**
 * 用于将网页内容转换为Markdown格式并复制到剪贴板的自定义Hook
 * @returns 包含转换函数和状态的对象
 */
export function useMarkdownConverter() {
	// 状态管理
	const status = ref('')

	/**
	 * 将当前页面转换为Markdown并复制到剪贴板
	 */
	const convertToMarkdown = async () => {
		status.value = '处理中...'
		try {
			// 获取当前活动标签页
			const [activeTab] = await browser.tabs.query({
				active: true,
				currentWindow: true,
			})
			if (!activeTab.id) throw new Error('无法获取当前标签页')

			// 注入脚本获取页面内容
			const results = await browser.scripting.executeScript({
				target: { tabId: activeTab.id! },
				func: () => document.body.outerHTML,
			})

			// 处理页面内容
			const htmlContent = results[0].result || ''
			const options = await getOptions()
			let processedContent = htmlContent

			// 根据配置选择内容处理方式
			if (options.useReadability) {
				const doc = new Readability(
					new DOMParser().parseFromString(htmlContent, 'text/html')
				).parse()
				processedContent = doc?.content || htmlContent
			} else if (options.useDeffudle) {
				processedContent = new Defuddle(htmlContent).toString()
			}

			// 转换为Markdown
			const turndown = new Turndown({
				headingStyle: 'atx',
				codeBlockStyle: 'fenced',
			})
			defaultTagsToRemove.forEach(tag => turndown.remove(tag))
			const markdown = turndown.turndown(processedContent)

			// 复制到剪贴板
			await navigator.clipboard.writeText(markdown)
			status.value = '转换成功！Markdown已复制到剪贴板'

			return markdown
		} catch (error) {
			console.error('转换失败:', error)
			status.value = `转换失败: ${
				error instanceof Error ? error.message : String(error)
			}`
		}
	}

	return { convertToMarkdown, status }
}
