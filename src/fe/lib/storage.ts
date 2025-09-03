import { browser } from 'wxt/browser'

/**
 * 应用配置选项的状态类型定义
 * 包含所有可配置的功能开关
 */
export type OptionsState = {
	useDeffudle: boolean          // 是否启用Deffudle功能
	useReadability: boolean       // 是否启用可读性优化
	wrapInTripleBackticks: boolean // 是否用三重反引号包裹输出
	showSuccessToast: boolean     // 是否显示操作成功的提示框
	showConfetti: boolean         // 是否显示庆祝效果
}

/**
 * 默认配置选项
 * 当存储中没有保存的配置时使用这些值
 */
export const defaultOptions: OptionsState = {
	useDeffudle: false,
	useReadability: true,
	wrapInTripleBackticks: false,
	showSuccessToast: false,
	showConfetti: false,
}

/**
 * 从浏览器存储中获取当前配置选项
 * 如果存储中没有配置，则返回默认配置
 * @returns 包含当前配置的Promise对象
 */
export async function getOptions(): Promise<OptionsState> {
	try {
		const result = await browser.storage.sync.get(Object.keys(defaultOptions))
		return { ...defaultOptions, ...result }
	} catch (error) {
		console.error('Error getting options:', error)
		return defaultOptions
	}
}

/**
 * 将配置选项保存到浏览器存储中
 * @param options 要保存的配置选项部分对象
 * @returns 保存操作的Promise对象
 */
export async function saveOptions(
	options: Partial<OptionsState>
): Promise<void> {
	try {
		await browser.storage.sync.set(options)
	} catch (error) {
		console.error('Error saving options:', error)
	}
}

/**
 * 重置所有配置选项到默认状态
 * 清除浏览器存储中的所有配置数据
 * @returns 重置操作的Promise对象
 */
export async function resetOptions(): Promise<void> {
	try {
		await browser.storage.sync.clear()
	} catch (error) {
		console.error('Error resetting options:', error)
	}
}
