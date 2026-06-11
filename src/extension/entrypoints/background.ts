import { generateQuestion } from '@/entrypoints/services/apiService';
import { SITE_RULES, isReadableUrl } from '@/extractor/siteRules.cjs';
import { startReadingSession, type ReadingSessionResult } from '@/immersive/readingSession.cjs';
import type { QuestionItem } from '@/lib/questionTypes';
import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';

type GenerateQuestionsMessage = {
  type: 'INSIGHTFLOW_GENERATE_QUESTIONS';
  content: string;
};

type GenerateQuestionsResponse =
  | { ok: true; questions: QuestionItem[] }
  | { ok: false; error: string };

export default defineBackground(() => {
  browser.action.onClicked.addListener(async (tab) => {
    const tabId = tab.id;

    if (typeof tabId !== 'number' || !isInjectableUrl(tab.url)) {
      await notifyFailure(getMessage('unsupportedPage', 'Current page does not support Reading Sessions'));
      return;
    }

    if (!isReadableUrl(tab.url || '', SITE_RULES)) {
      await notifyFailure(getMessage('unreadableSite', 'This site is not supported for Reading Sessions'));
      return;
    }

    try {
      const [injection] = await browser.scripting.executeScript({
        target: { tabId },
        func: startReadingSession,
        args: [SITE_RULES],
      });
      const result = injection?.result as ReadingSessionResult | undefined;

      if (!result?.ok) {
        throw new Error(result?.error || getMessage('extractContentFailed', 'Could not extract readable content'));
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error('Failed to start Reading Session:', error);
      await notifyFailure(`${getMessage('enterReadingSessionFailed', 'Unable to enter Reading Session')}: ${message}`);
    }
  });

  browser.runtime.onMessage.addListener((message) => {
    if (!isGenerateQuestionsMessage(message)) return undefined;
    return handleGenerateQuestions(message.content);
  });
});

function isInjectableUrl(url?: string): boolean {
  return Boolean(url && /^https?:\/\//i.test(url));
}

function isGenerateQuestionsMessage(message: unknown): message is GenerateQuestionsMessage {
  return Boolean(
    message &&
      typeof message === 'object' &&
      (message as GenerateQuestionsMessage).type === 'INSIGHTFLOW_GENERATE_QUESTIONS' &&
      typeof (message as GenerateQuestionsMessage).content === 'string',
  );
}

async function handleGenerateQuestions(content: string): Promise<GenerateQuestionsResponse> {
  try {
    const response = await generateQuestion(content);
    return {
      ok: true,
      questions: response.questions || [],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('Failed to generate questions:', error);
    return { ok: false, error: message };
  }
}

async function notifyFailure(message: string): Promise<void> {
  try {
    await browser.notifications.create({
      type: 'basic',
      iconUrl: 'icon/48.png',
      title: 'InsightFlow',
      message,
    });
  } catch (error) {
    console.warn('Failed to show notification:', error);
  }
}

function getMessage(key: string, fallback: string): string {
  try {
    const extensionGlobal = globalThis as typeof globalThis & {
      chrome?: { i18n?: { getMessage?: (name: string) => string } };
    };
    return extensionGlobal.chrome?.i18n?.getMessage?.(key) || fallback;
  } catch {
    return fallback;
  }
}
