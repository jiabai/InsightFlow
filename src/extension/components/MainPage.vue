<template>
  <div class="container">
    <div class="btn-group">
      <button 
        id="generateBtn" 
        class="circle-btn green" 
        data-tooltip="自动生成问题" 
        @click="handleGenerate"
      >
        <span>+</span>
      </button>
      <button 
        id="exitBtn" 
        class="circle-btn red" 
        data-tooltip="退出沉浸阅读模式"         
        @click="handleExit"
      >
        <span>&times;</span>
      </button>
    </div>

    <div id="contentArea">
      <!-- Skeleton + progress bar -->
      <div v-if="showSkeleton" class="skeleton-container">
        <div class="skeleton">
          <div class="skeleton-row" v-for="i in 3" :key="i">
            <div class="skeleton-content full-width">
              <div class="skeleton-title"></div>
              <div class="skeleton-paragraph" v-for="j in 2" :key="j"></div>
              <div class="skeleton-paragraph short"></div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="showProgress" class="progress-container">
        <div class="loading-text"></div>
        <div class="progress-bar blue-gradient">
          <div class="progress-inner" :style="{ width: progress + '%' }"></div>
        </div>
      </div>

      <!-- Question list -->
      <div v-else-if="questions.length > 0" class="question-list">
        <div 
          v-for="(question, index) in questions" 
          :key="index" 
          class="question-item"
          @click="toggleQuestion(index)"
        >
          <div class="question-header">
            <span class="question-title" :title="question.question">{{ question.question }}</span>
            <div :class="['arrow', isExpanded[index] ? 'rotate' : '']"></div>
          </div>
          
          <div v-if="isExpanded[index]" class="question-answer">
            <div class="answer-content">
              <div v-if="isLoadingAnswer && loadingIndex === index" class="loading-text">加载中...</div>
              <div v-else v-html="displayedAnswers[index]"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Error message -->
      <div v-else-if="error" class="error-message">
        <p>发生错误: {{ error.message }}</p>
      </div>

      <!-- Empty state -->
      <div v-else class="empty-state">
        <template v-if="isBlankPage">
          <div class="empty-icon">📄</div>
          <p class="empty-title">内容提取失败</p>
          <p class="empty-hint">{{ extractionStatus }}</p>
          <p class="empty-debug">检测到: {{ detectedUrl }}</p>
        </template>
        <template v-else-if="content">
          <div class="empty-icon">✨</div>
          <p class="empty-title">内容已就绪</p>
          <p class="empty-hint">点击左上角 <strong>+</strong> 生成问题</p>
          <p class="empty-debug">{{ extractionStatus }}</p>
        </template>
        <template v-else>
          <div class="empty-icon">🔍</div>
          <p class="empty-title">未检测到可提取的内容</p>
          <p class="empty-hint">请尝试其他网页</p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import './MainPage.css';
import { ref, onMounted } from 'vue';
import { useMarkdownConverter } from '@/hooks/useMarkdownConverter';
import { useContentPanel } from '@/hooks/composables/useContentPanel';
import { useQuestionList } from '@/hooks/composables/useQuestionList';
import { browser } from 'wxt/browser';

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const {
  showSkeleton, showProgress, progress, questions, error,
  isBlankPage, content, isContentLoaded, contentError,
  handleGenerate, resetState,
} = useContentPanel();

const {
  isExpanded, displayedAnswers, loadingIndex, isLoadingAnswer,
  toggleQuestion,
} = useQuestionList(questions);

const { convertToMarkdown, status } = useMarkdownConverter();

// Debug state
const extractionStatus = ref('正在提取...');
const detectedUrl = ref('');

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
onMounted(async () => {
  showSkeleton.value = true;
  showProgress.value = true;
  progress.value = 0;

  try {
    const [activeTab] = await browser.tabs.query({ active: true, currentWindow: true });
    detectedUrl.value = activeTab.url || '(无URL)';
    console.log('🔍 检测到标签页:', activeTab.url, 'tabId:', activeTab.id);

    const isBlank = !activeTab.url
      || activeTab.url === 'about:blank'
      || activeTab.url.startsWith('chrome://newtab')
      || activeTab.url.startsWith('chrome-extension://');
    isBlankPage.value = isBlank;

    if (!isBlank) {
      extractionStatus.value = '正在提取页面内容...';
      const extracted = await convertToMarkdown();
      
      if (extracted) {
        content.value = extracted;
        extractionStatus.value = `提取成功 (${extracted.length} 字符)`;
      } else {
        extractionStatus.value = '提取失败: ' + (status.value || '未知错误');
        isBlankPage.value = true;
      }
    } else {
      extractionStatus.value = '当前页面不支持内容提取';
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    extractionStatus.value = '提取异常: ' + msg;
    contentError.value = err instanceof Error ? err : new Error(msg);
    isBlankPage.value = true;
  } finally {
    isContentLoaded.value = true;
    showProgress.value = false;
    showSkeleton.value = false;
  }
});

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------
function handleExit() {
  resetState();
}
</script>
