import { ref } from 'vue';
import type { QuestionResponse, QuestionItem } from '@/lib/questionTypes';
import { generateQuestion } from '@/entrypoints/services/apiService';

/**
 * useContentPanel — manages the content lifecyle in the immersive reader.
 *
 * Handles: content extraction → question generation → progress animation.
 */
export function useContentPanel() {
  const showSkeleton = ref(false);
  const showProgress = ref(false);
  const progress = ref(0);
  const questions = ref<QuestionItem[]>([]);
  const error = ref<Error | null>(null);
  const isBlankPage = ref(false);

  // Content state
  const content = ref('');
  const isContentLoaded = ref(false);
  const contentError = ref<Error | null>(null);

  let progressInterval: ReturnType<typeof setInterval> | null = null;
  let pollIntervalId: ReturnType<typeof setInterval> | null = null;

  /** Start progress bar animation (0 → 90%). */
  function startProgressAnimation() {
    if (progressInterval) clearInterval(progressInterval);
    progress.value = 0;

    progressInterval = setInterval(() => {
      if (progress.value < 90) {
        const increment = progress.value < 30 ? Math.random() * 1.5
                       : progress.value < 70 ? Math.random() * 1
                       : Math.random() * 0.5;
        progress.value = Math.min(progress.value + increment, 90);
      }
    }, 200);
  }

  /** Smoothly complete the progress bar to 100% and hide. */
  function completeProgressAnimation() {
    if (progressInterval) {
      clearInterval(progressInterval);
      progressInterval = null;
    }

    const duration = 1000;
    const start = progress.value;
    const end = 100;
    const steps = 50;
    const increment = (end - start) / steps;
    let currentStep = 0;

    const animationInterval = setInterval(() => {
      currentStep++;
      progress.value = Math.min(start + increment * currentStep, 100);

      if (currentStep >= steps || progress.value >= 100) {
        clearInterval(animationInterval);
        progress.value = 100;
        setTimeout(() => {
          showProgress.value = false;
          showSkeleton.value = false;
        }, 500);
      }
    }, duration / steps);
  }

  /** Stop progress animation and show error state briefly. */
  function stopProgressAnimation() {
    if (progressInterval) {
      clearInterval(progressInterval);
      progressInterval = null;
    }
    setTimeout(() => {
      showProgress.value = false;
      showSkeleton.value = false;
    }, 1500);
  }

  /** Generate questions from extracted content. */
  async function handleGenerate() {
    showSkeleton.value = true;
    showProgress.value = true;
    progress.value = 0;
    error.value = null;
    questions.value = [];
    startProgressAnimation();

    try {
      if (content.value) {
        const response: QuestionResponse = await generateQuestion(
          content.value,
          (id) => { pollIntervalId = id; }
        );
        questions.value = response.questions || [];
        completeProgressAnimation();
      } else {
        throw new Error('没有可处理的内容');
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('未知错误');
      stopProgressAnimation();
    } finally {
      if (showProgress.value) {
        setTimeout(() => {
          if (progress.value < 100) stopProgressAnimation();
        }, 10000);
      }
    }
  }

  /** Reset UI state (preserve answers cache). */
  function resetState() {
    questions.value = [];
    if (progressInterval) {
      clearInterval(progressInterval);
      progressInterval = null;
    }
    if (pollIntervalId) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
    showSkeleton.value = false;
    showProgress.value = false;
    progress.value = 0;
    error.value = null;
  }

  return {
    // state
    showSkeleton,
    showProgress,
    progress,
    questions,
    error,
    isBlankPage,
    content,
    isContentLoaded,
    contentError,
    // actions
    handleGenerate,
    resetState,
  };
}
