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
            <span>{{ question }}</span>
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
      <div v-if="displayedAnswer || typingCursor" class="answer-content">
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
import { generateQuestion, generateAnswer } from '../entrypoints/services/apiService';
// 由于找不到模块，可能是文件扩展名问题，尝试移除 .js 扩展名
import { convertToMarkdown,getCurrentTabContent } from '../utils/stringUtils';
import type { GenerateQuestionResponse, GenerateAnswerResponse } from '../entrypoints/services/apiService';
// 定义问题接口
interface Question {
  id: number;
  text: string;
}

// 响应式状态 - 添加明确的类型注解
const showSkeleton = ref<boolean>(false);
const showProgress = ref<boolean>(false);
const progress = ref<number>(0);
const questions = ref<string[]>([]);
const error = ref<Error | null>(null);
let progressInterval: ReturnType<typeof setInterval> | null = null;

// 添加展开状态和每个问题对应的答案状态
const isExpanded = ref<boolean[]>([]);
const displayedAnswers = ref<string[]>([]);
const typingCursors = ref<boolean[]>([]);
let typingIntervals: (ReturnType<typeof setInterval> | null)[] = [];

// 初始化问题状态数组
const initializeQuestionStates = (count: number) => {
  isExpanded.value = Array(count).fill(false);
  displayedAnswers.value = Array(count).fill('');
  typingCursors.value = Array(count).fill(false);
  typingIntervals = Array(count).fill(null);
};

// 修改handleGenerate以初始化状态
const handleGenerate = async () => {
  // 立即显示骨架屏和进度条
  showSkeleton.value = true;
  showProgress.value = true;
  progress.value = 0;
  
  // 立即启动进度条动画
  startProgressAnimation();

  try {
    // 确保提供text参数
    const result: GenerateQuestionResponse = await generateQuestion('需要分析的文本内容');
    questions.value = result.questions || [];
    initializeQuestionStates(questions.value.length); // 初始化状态数组
  } catch (err) {
    error.value = err instanceof Error ? err : new Error('未知错误');
    console.error('API调用失败:', error.value);
  } finally {
    // API调用完成后关闭加载状态
    clearInterval(progressInterval!);
    showProgress.value = false;
    showSkeleton.value = false;
  }
};

// 进度条动画函数
const startProgressAnimation = () => {
  // 清除可能存在的旧定时器
  if (progressInterval) clearInterval(progressInterval);
  
  // 初始进度设为0
  progress.value = 0;
  
  progressInterval = setInterval(() => {
    if (progress.value < 95) {
      // 计算增长值，实现平滑动画
      const increment = progress.value < 30 ? Math.random() * 1.5 : 
                      progress.value < 70 ? Math.random() * 1 : 
                      Math.random() * 0.5;
                        
      progress.value = Math.min(progress.value + increment, 95);
    }
  }, 200);
};
const handleExit = () => {
  // 只清除问题列表，保留答案缓存
  questions.value = [];
  
  // 停止任何正在进行的进度动画
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
  
  // 仅重置UI状态，不清除answersCache
  showSkeleton.value = false;
  showProgress.value = false;
  progress.value = 0;
  error.value = null;
};

// 添加新的响应式状态
const answersCache = ref<Record<string, { answer: string; timestamp: number }>>({});
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

// 修改loadAnswerForQuestion方法
const loadAnswerForQuestion = async (index: number, question: string) => {
  // 检查缓存
  const cachedAnswer = answersCache.value[question];
  const CACHE_DURATION = 3600000; // 1小时缓存有效期

  if (cachedAnswer && Date.now() - cachedAnswer.timestamp < CACHE_DURATION) {
    displayedAnswers.value[index] = cachedAnswer.answer;
    return;
  }

  // 设置当前加载索引并显示loading-text
  loadingIndex.value = index;
  isLoadingAnswer.value = true;
  
  try {
    const response: GenerateAnswerResponse = await generateAnswer(question);
    const fullAnswer = response.answer;

    // 更新缓存
    answersCache.value[question] = {
      answer: fullAnswer,
      timestamp: Date.now()
    };

    // 隐藏loading-text并使用打字机效果显示答案
    isLoadingAnswer.value = false;
    await typeWriterEffect(index, fullAnswer);
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
    // 1. 获取当前预览的网页数据内容
    const content = await getCurrentTabContent();
    if (!content) {
      // 处理空内容情况（包括about:blank）
      displayedAnswer.value = '当前页面无可用内容';
      return;
    }

    // 2. 调用convertToMarkdown生成Markdown
    const markdownContent = await convertToMarkdown(content);

    // 3. 在contentArea显示Markdown
    displayedAnswer.value = markdownContent;
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
</script>
