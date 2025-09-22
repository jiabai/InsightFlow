import { ref } from 'vue'
import { browser } from 'wxt/browser'
import Turndown from 'turndown'
import { Readability } from '@mozilla/readability'
import { defaultTagsToRemove } from '@/lib/tagsToRemove'

export function useMarkdownConverter() {
	// 状态管理
	const status = ref('')
	const lastConvertedMarkdown = ref('')

	/**
	 * 检查剪贴板权限
	 */
	const checkClipboardPermission = async (): Promise<boolean> => {
		try {
			// 检查权限状态
			const permission = await navigator.permissions.query({ name: 'clipboard-write' as PermissionName })
			return permission.state === 'granted' || permission.state === 'prompt'
		} catch (error) {
			// 如果浏览器不支持permissions API，尝试直接访问
			try {
				await navigator.clipboard.writeText('test')
				return true
			} catch {
				return false
			}
		}
	}

	/**
	 * 使用备用方法复制到剪贴板
	 */
	const copyToClipboardFallback = async (text: string): Promise<boolean> => {
		try {
			// 方法1: 创建临时文本区域
			const textArea = document.createElement('textarea')
			textArea.value = text
			textArea.style.position = 'fixed'
			textArea.style.left = '-9999px'
			textArea.style.top = '-9999px'
			document.body.appendChild(textArea)
			textArea.focus()
			textArea.select()
			
			const successful = document.execCommand('copy')
			document.body.removeChild(textArea)
			
			if (successful) {
				return true
			}
			
			// 方法2: 使用新的异步剪贴板API
			if (navigator.clipboard && window.isSecureContext) {
				await navigator.clipboard.writeText(text)
				return true
			}
			
			return false
		} catch (error) {
			console.error('备用复制方法失败:', error)
			return false
		}
	}

	/**
	 * 确保页面获得焦点
	 */
	const ensureFocus = async (): Promise<void> => {
		return new Promise((resolve) => {
			if (document.hasFocus()) {
				resolve()
				return
			}
			
			// 尝试通过用户交互获得焦点
			const focusHandler = () => {
				resolve()
				window.removeEventListener('focus', focusHandler)
			}
			window.addEventListener('focus', focusHandler)
			
			// 如果3秒后仍未获得焦点，继续执行
			setTimeout(() => {
				resolve()
				window.removeEventListener('focus', focusHandler)
			}, 3000)
		})
	}

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
			
			// 检查是否为about:blank页面
			if (
				activeTab.url?.indexOf('about:blank') !== -1 ||
				activeTab.url?.indexOf('chrome://newtab/') !== -1
			) {
				console.log('当前为空白页面，不执行内容提取')
				status.value = '当前为空白页面，无法提取内容'
				return
			}
			
			if (!activeTab.id) {
				console.log('无法获取当前标签页')
				status.value = '无法获取当前标签页'
				return
			}
			
			// 注入脚本获取页面内容
			const results = await browser.scripting.executeScript({
				target: { tabId: activeTab.id! },
				func: () => document.body.outerHTML,
			})

			// 处理页面内容
			const htmlContent = results[0].result || ''
			let processedContent = htmlContent

			const doc = new Readability(
				new DOMParser().parseFromString(htmlContent, 'text/html')
			).parse()
			processedContent = doc?.content || htmlContent

			// 转换为Markdown
			const turndown = new Turndown({
				headingStyle: 'atx',
				codeBlockStyle: 'fenced',
			})

			// 添加这部分代码覆盖img标签处理
			turndown.addRule('removeImages', {
				filter: 'img',
				replacement: () => '',
			})

			defaultTagsToRemove.forEach(tag => turndown.remove(tag))
			const markdown = turndown.turndown(processedContent)
			
			// 保存markdown到状态
			lastConvertedMarkdown.value = markdown

			// 尝试复制到剪贴板
			let clipboardSuccess = false
			
			try {
				// 确保页面有焦点
				await ensureFocus()
				
				// 检查剪贴板权限
				const hasPermission = await checkClipboardPermission()
				if (hasPermission) {
					await navigator.clipboard.writeText(markdown)
					clipboardSuccess = true
				} else {
					console.warn('没有剪贴板权限，尝试备用方法')
					clipboardSuccess = await copyToClipboardFallback(markdown)
				}
			} catch (clipboardError) {
				console.error('剪贴板写入失败，尝试备用方法:', clipboardError)
				clipboardSuccess = await copyToClipboardFallback(markdown)
			}

			if (clipboardSuccess) {
				status.value = '转换成功！Markdown已复制到剪贴板'
			} else {
				status.value = '转换成功！由于权限限制，请点击下方按钮手动复制'
			}

			return markdown
		} catch (error) {
			console.error('转换失败:', error)
			status.value = `转换失败: ${
				error instanceof Error ? error.message : String(error)
			}`
		}
	}

	/**
	 * 手动复制最后转换的Markdown到剪贴板
	 */
	const copyLastMarkdown = async (): Promise<boolean> => {
		if (!lastConvertedMarkdown.value) {
			status.value = '没有可复制的Markdown内容'
			return false
		}

		try {
			await ensureFocus()
			const success = await copyToClipboardFallback(lastConvertedMarkdown.value)
			if (success) {
				status.value = 'Markdown已复制到剪贴板'
			} else {
				status.value = '复制失败，请手动选择并复制'
			}
			return success
		} catch (error) {
			console.error('手动复制失败:', error)
			status.value = '复制失败，请手动选择并复制'
			return false
		}
	}

	/**
	 * 获取最后转换的Markdown内容
	 */
	const getLastMarkdown = (): string => {
		return lastConvertedMarkdown.value
	}

	return { 
		convertToMarkdown, 
		copyLastMarkdown,
		getLastMarkdown,
		status 
	}
}
