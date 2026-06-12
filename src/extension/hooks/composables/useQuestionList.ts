import { ref, watch, type Ref } from 'vue';
import type { QuestionItem } from '@/lib/questionTypes';
import { generateAnswer } from '@/entrypoints/services/apiService';
import type { GenerateAnswerResponse } from '@/entrypoints/services/apiService';

/**
 * useQuestionList — manages questions and their answers in the immersive reader.
 *
 * Handles: question expansion, answer caching, streaming answers, typewriter effect.
 */
export function useQuestionList(questions: Ref<QuestionItem[]>) {
  // Expansion state
  const isExpanded = ref<boolean[]>([]);
  const displayedAnswers = ref<string[]>([]);
  const typingCursors = ref<boolean[]>([]);
  const loadingIndex = ref<number | null>(null);
  const isLoadingAnswer = ref(false);

  let typingIntervals: (ReturnType<typeof setInterval> | null)[] = [];

  // Answer cache: question text → { answer, timestamp }
  const answersCache = ref<Record<string, { answer: string; timestamp: number }>>({});
  const CACHE_DURATION = 3600000; // 1 hour

  /** Initialize state arrays for N questions. */
  function initialize(count: number) {
    isExpanded.value = Array(count).fill(false);
    displayedAnswers.value = Array(count).fill('');
    typingCursors.value = Array(count).fill(false);
    typingIntervals = Array(count).fill(null);
  }

  // Keep the per-question state arrays sized to the current question list.
  // Without this, isExpanded stays [] and toggleQuestion's `.map` over an
  // empty array never expands anything.
  watch(
    questions,
    (newQuestions) => initialize(newQuestions?.length ?? 0),
    { immediate: true }
  );

  /** Toggle question expansion and load answer if needed. */
  async function toggleQuestion(index: number) {
    const currentlyExpanded = isExpanded.value[index];

    // Collapse all others, toggle current
    isExpanded.value = isExpanded.value.map((_, i) => i === index && !currentlyExpanded);

    if (!currentlyExpanded && !displayedAnswers.value[index]) {
      await loadAnswer(index);
    }
  }

  /** Load answer for a question (with cache). */
  async function loadAnswer(index: number) {
    const q = questions.value[index];
    if (!q) return;

    const cached = answersCache.value[q.question];
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      displayedAnswers.value[index] = cached.answer;
      return;
    }

    loadingIndex.value = index;
    isLoadingAnswer.value = true;

    try {
      const response: GenerateAnswerResponse = await generateAnswer(
        q.question_id,
        q.chunk_id,
        (partial) => { displayedAnswers.value[index] = partial; }
      );

      answersCache.value[q.question] = {
        answer: response.answer,
        timestamp: Date.now(),
      };

      displayedAnswers.value[index] = response.answer;
      isLoadingAnswer.value = false;
      await typewriterEffect(index, response.answer);
    } catch (err) {
      isLoadingAnswer.value = false;
      await typewriterEffect(index, '获取回答失败，请重试');
      console.error('生成回答失败:', err);
    } finally {
      loadingIndex.value = null;
    }
  }

  /** Typewriter animation for displaying answer text. */
  function typewriterEffect(index: number, text: string, speed = 30): Promise<void> {
    return new Promise((resolve) => {
      let charIndex = 0;
      displayedAnswers.value[index] = '';
      typingCursors.value[index] = true;

      if (typingIntervals[index]) clearInterval(typingIntervals[index]);

      const formatted = text.replace(/\n/g, '<br>');

      typingIntervals[index] = setInterval(() => {
        if (charIndex < formatted.length) {
          displayedAnswers.value[index] += formatted.charAt(charIndex);
          charIndex++;
        } else {
          clearInterval(typingIntervals[index]!);
          typingCursors.value[index] = false;
          typingIntervals[index] = null;
          resolve();
        }
      }, speed);
    });
  }

  return {
    isExpanded,
    displayedAnswers,
    typingCursors,
    loadingIndex,
    isLoadingAnswer,
    initialize,
    toggleQuestion,
  };
}
