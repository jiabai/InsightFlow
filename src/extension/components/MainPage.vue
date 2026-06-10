<template>
  <div class="container">
        <!-- <div class="header">AI思考助手</div> -->
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
      <!-- 骨架屏和进度条 -->
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
      <!-- 问题列表 -->
      <div v-else-if="questions.length > 0" class="question-list">
        <div 
          v-for="(question, index) in questions" 
          :key="index" 
          class="question-item"
          @click="toggleQuestion(index)"
        >
          <!-- 问题标题和展开箭头 -->
          <div class="question-header">
            <span class="question-title" :title="question.question">{{ question.question }}</span>
            <div :class="['arrow', isExpanded[index] ? 'rotate' : '']"></div>
          </div>
          
          <!-- 答案详情区域 -->
          <div v-if="isExpanded[index]" class="question-answer">
            <div class="answer-content">
              <div v-if="isLoadingAnswer && loadingIndex === index" class="loading-text">加载中...</div>
              <div v-else v-html="displayedAnswers[index]"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 打印机动效容器 -->
      <div v-if="isPrinting" class="printer-animation">
        <div class="paper"></div>
        <div class="printer-head"></div>
      </div>
      
      <!-- 移除打印机动效容器 -->
      <!-- 回答显示区域 -->
      <div v-if="!isBlankPage && (displayedAnswer || typingCursor)" class="answer-content">
        <span>{{ displayedAnswer }}</span>
        <span v-if="typingCursor" class="typing-cursor">|</span>
      </div>
      
      <!-- 错误信息 -->
      <div v-else-if="error" class="error-message">
        <p>发生错误: {{ error.message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import './MainPage.css';
import { ref, onMounted } from 'vue';
import { generateQuestion, generateAnswer} from '../entrypoints/services/apiService';
import { useMarkdownConverter } from '@/hooks/useMarkdownConverter'
import type { GenerateAnswerResponse } from '../entrypoints/services/apiService';
import type { QuestionResponse,QuestionItem } from '@/lib/questionTypes';
import { browser } from 'wxt/browser';

// 响应式状态 - 添加明确的类型注解
const showSkeleton = ref<boolean>(false);
const showProgress = ref<boolean>(false);
const progress = ref<number>(0);
const questions = ref<QuestionItem[]>([]);
const error = ref<Error | null>(null);
let progressInterval: ReturnType<typeof setInterval> | null = null;

// 添加空白页状态响应式变量
const isBlankPage = ref<boolean>(false);

// 添加展开状态和每个问题对应的答案状态
const isExpanded = ref<boolean[]>([]);
const displayedAnswers = ref<string[]>([]);
const typingCursors = ref<boolean[]>([]);
let typingIntervals: (ReturnType<typeof setInterval> | null)[] = [];
let pollIntervalId: ReturnType<typeof setInterval> | null = null;
// 添加全局内容响应式变量
const content = ref<string>('');
const isContentLoaded = ref<boolean>(false);
const contentError = ref<Error | null>(null);
// 初始化问题状态数组
const initializeQuestionStates = (count: number) => {
  isExpanded.value = Array(count).fill(false);
  displayedAnswers.value = Array(count).fill('');
  typingCursors.value = Array(count).fill(false);
  typingIntervals = Array(count).fill(null);
};

// 获取Markdown转换器
const { convertToMarkdown } = useMarkdownConverter();

// 在组件挂载时提取内容
onMounted(async () => {
  try {
    // 立即提取内容
    const extractedContent = await convertToMarkdown();
    content.value = extractedContent || '';
    isContentLoaded.value = true;
    // 检查是否为空白页面
    isBlankPage.value = !content.value;
  } catch (err) {
    contentError.value = err instanceof Error ? err : new Error('内容提取失败');
    console.error('内容提取失败:', contentError.value);
    isContentLoaded.value = true;
    // 如果提取失败，视为空白页面
    isBlankPage.value = true;
  }
});

// 修改handleGenerate函数
const handleGenerate = async () => {
  // 立即显示骨架屏和进度条
  showSkeleton.value = true;
  showProgress.value = true;
  progress.value = 0;
  error.value = null; // 重置错误状态
  questions.value = []; // 清空问题列表
  // 立即启动进度条动画
  startProgressAnimation();

  try {
    // 使用全局content变量
    if (content.value) {
      let questionResponse:QuestionResponse = await generateQuestion(
        content.value,
        (id) => {
          // 保存轮询ID到组件状态
          pollIntervalId = id;
        }
      );
      // 确保 questionResponse 有值且存在 questions 属性后再赋值
      questions.value = questionResponse.questions || [];
      initializeQuestionStates(questions.value.length);

      // API调用成功，进度条平滑到100%
      completeProgressAnimation();
    } else {
      throw new Error('没有可处理的内容');
    }
  } catch (err) {
    error.value = err instanceof Error ? err : new Error('未知错误');
    console.error('API调用失败:', error.value);
    stopProgressAnimation();
  } finally {
    // 确保在任何情况下进度条都能被清理
    if (showProgress.value) {
      // 如果进度条仍在显示，强制隐藏
      setTimeout(() => {
        if (progress.value < 100) {
          stopProgressAnimation();
        }
      }, 10000); // 10秒后强制停止
    }
  }
};

// 进度条动画函数
const startProgressAnimation = () => {
  // 清除可能存在的旧定时器
  if (progressInterval) clearInterval(progressInterval);

  // 初始进度设为0
  progress.value = 0;

  progressInterval = setInterval(() => {
    if (progress.value < 90) { // 只到90%，留10%给完成动画
      // 计算增长值，实现平滑动画
      const increment = progress.value < 30 ? Math.random() * 1.5 : 
                      progress.value < 70 ? Math.random() * 1 : 
                      Math.random() * 0.5;

      progress.value = Math.min(progress.value + increment, 90);
    }
  }, 200);
};

// 添加完成进度条动画函数
const completeProgressAnimation = () => {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }

  // 平滑过渡到100%
  const duration = 1000; // 1秒内完成
  const start = progress.value;
  const end = 100;
  const steps = 50;
  const increment = (end - start) / steps;
  let currentStep = 0;
 // 清空displayedAnswer
  displayedAnswer.value = '';
  const animationInterval = setInterval(() => {
    currentStep++;
    progress.value = Math.min(start + (increment * currentStep), 100);

    if (currentStep >= steps || progress.value >= 100) {
      clearInterval(animationInterval);
      progress.value = 100;

      // 延迟后隐藏进度条
      setTimeout(() => {
        showProgress.value = false;
        showSkeleton.value = false;
      }, 500);
    }
  }, duration / steps);
};

// 添加停止进度条动画函数
const stopProgressAnimation = () => {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }

  // 显示错误状态一段时间后隐藏
  setTimeout(() => {
    showProgress.value = false;
    showSkeleton.value = false;
  }, 1500);
};
const handleExit = () => {
  // 只清除问题列表，保留答案缓存
  questions.value = [];
  
  // 停止任何正在进行的进度动画
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
  
  // 终止pollFileStatus轮询
  if (pollIntervalId) {
    clearInterval(pollIntervalId);
    pollIntervalId = null;
  }
  
  // 清空displayedAnswer
  displayedAnswer.value = '';
  
  // 仅重置UI状态，不清除answersCache
  showSkeleton.value = false;
  showProgress.value = false;
  progress.value = 0;
  error.value = null;
};

// 添加新的响应式状态
// 修改缓存结构
const answersCache = ref<Record<string, { 
  answer: string; 
  reasoning_content?: string;
  timestamp: number 
}>>({});
const isPrinting = ref<boolean>(false);
const isLoadingAnswer = ref<boolean>(false);

// 添加打字机效果相关状态
const displayedAnswer = ref<string>('');
const typingCursor = ref<boolean>(false);

// 更新打字机效果函数以支持回调和样式
const typeWriterEffect = (index: number, text: string, speed: number = 30, callback?: () => void) => {
  return new Promise<void>((resolve) => {
    let charIndex = 0;
    displayedAnswers.value[index] = '';
    typingCursors.value[index] = true;

    // 清除可能存在的旧定时器
    if (typingIntervals[index]) clearInterval(typingIntervals[index]);

    // 处理换行符，将\n转换为HTML换行
    const formattedText = text.replace(/\n/g, '<br>');

    typingIntervals[index] = setInterval(() => {
      if (charIndex < formattedText.length) {
        // 逐个添加字符
        displayedAnswers.value[index] += formattedText.charAt(charIndex);
        charIndex++;
      } else {
        clearInterval(typingIntervals[index]!);
        typingCursors.value[index] = false;
        typingIntervals[index] = null;
        // 执行回调函数
        if (callback) callback();
        resolve();
      }
    }, speed);
  });
};

// 添加切换展开/收起的方法
const toggleQuestion = async (index: number) => {
  const question = questions.value[index];
  const currentlyExpanded = isExpanded.value[index];
  
  // 先关闭所有其他项
  isExpanded.value = isExpanded.value.map((_, i) => i === index && !currentlyExpanded);
  
  // 如果要展开且答案未加载，则加载答案
  if (!currentlyExpanded && !displayedAnswers.value[index]) {
    await loadAnswerForQuestion(index, question);
  }
};

// 添加加载索引状态
const loadingIndex = ref<number | null>(null);

// 修改 loadAnswerForQuestion 方法
const loadAnswerForQuestion = async (index: number, question: QuestionItem) => {
  // 检查缓存，使用问题文本作为缓存键
  const cachedAnswer = answersCache.value[question.question];
  const CACHE_DURATION = 3600000; // 1小时缓存有效期

  if (cachedAnswer && Date.now() - cachedAnswer.timestamp < CACHE_DURATION) {
    displayedAnswers.value[index] = cachedAnswer.answer;
    return;
  }

  // 设置当前加载索引并显示loading-text
  loadingIndex.value = index;
  isLoadingAnswer.value = true;
  
  try {
    // 使用基础调用，不传递 onProgress 回调
    const response: GenerateAnswerResponse = await generateAnswer(
      question.question_id, 
      question.chunk_id,
      (partialAnswer) => {
        // 实时更新显示
        displayedAnswers.value[index] = partialAnswer;
      }
    );

    // 更新缓存 - 修复错误的 reasoning_content 赋值
    answersCache.value[question.question] = {
      answer: response.answer,
      timestamp: Date.now()
    };

    // 将处理后的答案添加到 displayedAnswers 数组中
    displayedAnswers.value[index] = response.answer;

    // 隐藏loading-text并使用打字机效果显示答案
    isLoadingAnswer.value = false;
    await typeWriterEffect(index, response.answer);
  } catch (err) {
    // 隐藏loading-text并显示错误信息
    isLoadingAnswer.value = false;
    await typeWriterEffect(index, '获取回答失败，请重试');
    console.error('生成回答失败:', err);
  } finally {
    // 清除加载索引
    loadingIndex.value = null;
  }
};


onMounted(async () => {
  // 显示骨架屏和进度条
  showSkeleton.value = true;
  showProgress.value = true;
  progress.value = 0;
  startProgressAnimation();

  try {
    // 获取当前标签页信息
    const [activeTab] = await browser.tabs.query({
      active: true,
      currentWindow: true
    });

    // 检查是否为空白页面
    isBlankPage.value = activeTab.url === 'about:blank';

    if (!isBlankPage.value) {
      // 使用自定义Hook
      const { convertToMarkdown, status } = useMarkdownConverter();
      // 1. 获取当前预览的网页数据内容
      const content = await convertToMarkdown();
      if (content) {
        displayedAnswer.value = content;
      } else {
        displayedAnswer.value = status.value;
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err : new Error('处理失败: ' + String(err));
    console.error('内容处理失败:', error.value);
  } finally {
    // 隐藏加载状态
    clearInterval(progressInterval!);
    showProgress.value = false;
    showSkeleton.value = false;
  }
});
// 完成进度条动画，平滑到100%
// 移除重复声明，下方代码为多余内容，应删除，此处仅保留声明
  if (progressInterval) {
    clearInterval(progressInterval);
  }

  const duration = 1000; // 1秒内完成
  const start = progress.value;
  const end = 100;
  const increment = (end - start) / (duration / 20);
  let current = start;

  const completeInterval = setInterval(() => {
    current += increment;
    if (current >= end) {
      progress.value = end;
      clearInterval(completeInterval);
      // 延迟隐藏进度条，让用户看到完成状态
      setTimeout(() => {
        showProgress.value = false;
        showSkeleton.value = false;
      }, 500);
    } else {
      progress.value = current;
    }
  }, 20);

// 停止进度条动画并显示错误状态
// 由于函数已在上方定义，此处移除重复声明
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }

  // 保持当前进度，显示一段时间后隐藏
  setTimeout(() => {
    showProgress.value = false;
    showSkeleton.value = false;
  }, 1000);
</script>
