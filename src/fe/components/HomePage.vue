<template>
	<!-- 添加点击按钮并绑定事件处理函数 -->
	<div class="container">
		<button @click="convertToMarkdown" class="convert-btn">
			将页面转换为Markdown
		</button>
		<div v-if="status" class="status-message">{{ status }}</div>
	</div>
</template>

<script lang="ts" setup>
	import { useMarkdownConverter } from '@/hooks/useMarkdownConverter'

	// 使用自定义Hook
	const { convertToMarkdown, status } = useMarkdownConverter()
	setTimeout(() => {
		convertToMarkdown()
	}, 5000);
</script>

<style scoped>
	.container {
		padding: 16px;
		min-width: 300px;
	}
	.convert-btn {
		background: #42b983;
		color: white;
		border: none;
		padding: 8px 16px;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
	}
	.status-message {
		margin-top: 12px;
		font-size: 12px;
		color: #666;
	}
</style>
