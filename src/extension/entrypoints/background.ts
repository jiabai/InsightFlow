import { generateQuestion } from '@/entrypoints/services/apiService';
import { SITE_RULES, isReadableUrl } from '@/extractor/siteRules.cjs';
import { startReadingSession, type ReadingSessionResult } from '@/immersive/readingSession.cjs';
import {
  AUTO_ENTER_INJECT_OPTS,
  isEnterCandidateEvent,
  isNavigationResetEvent,
} from '@/lib/autoEnter';
import { getOptions } from '@/lib/storage';
import type { QuestionItem } from '@/lib/questionTypes';
import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';

const DEBUG_PREFIX = '[InsightFlow:bg]';
const GENERATE_PORT_NAME = 'insightflow-generate-questions';
const LEGACY_GENERATE_TYPE = 'INSIGHTFLOW_GENERATE_QUESTIONS';
const PORT_GENERATE_START_TYPE = 'INSIGHTFLOW_GENERATE_QUESTIONS_START';

type GenerateQuestionsMessage = {
  type: typeof LEGACY_GENERATE_TYPE;
  requestId?: string;
  contentLength?: number;
  content: string;
};

type GenerateQuestionsPortMessage = {
  type: typeof PORT_GENERATE_START_TYPE;
  requestId: string;
  contentLength?: number;
  content: string;
};

type GenerateQuestionsResponse =
  | { ok: true; requestId: string; questions: QuestionItem[] }
  | { ok: false; requestId: string; error: string };

type RuntimePort = {
  name: string;
  onDisconnect: {
    addListener(listener: () => void): void;
  };
  onMessage: {
    addListener(listener: (message: unknown) => void): void;
  };
  postMessage(message: unknown): void;
  disconnect(): void;
};

type RuntimeApi = {
  lastError?: { message?: string };
  onConnect: {
    addListener(listener: (port: RuntimePort) => void): void;
  };
  onMessage: {
    addListener(
      listener: (
        message: unknown,
        sender: unknown,
        sendResponse: (response?: unknown) => void,
      ) => boolean | void,
    ): void;
  };
};

type ChromeGlobal = {
  runtime?: RuntimeApi;
};

export default defineBackground(() => {
  debugLog('startup', { portName: GENERATE_PORT_NAME });

  browser.action.onClicked.addListener(async (tab) => {
    const tabId = tab.id;
    debugLog('action:clicked', {
      tabId,
      urlOrigin: getUrlOrigin(tab.url),
      urlSupported: isInjectableUrl(tab.url),
    });

    if (typeof tabId !== 'number' || !isInjectableUrl(tab.url)) {
      await notifyFailure(getMessage('unsupportedPage', 'Current page does not support Reading Sessions'));
      return;
    }

    if (!isReadableUrl(tab.url || '', SITE_RULES)) {
      await notifyFailure(getMessage('unreadableSite', 'This site is not supported for Reading Sessions'));
      return;
    }

    await injectReadingSession(tabId, 'manual');
  });

  setupAutoEnterReadingMode();
  setupGenerateQuestionsPort();
  setupLegacyGenerateQuestionsMessage();
});

type InjectReadingSessionMode = 'manual' | 'auto';

async function injectReadingSession(tabId: number, mode: InjectReadingSessionMode): Promise<void> {
  const options = mode === 'auto' ? AUTO_ENTER_INJECT_OPTS : {};

  try {
    const [injection] = await browser.scripting.executeScript({
      target: { tabId },
      func: startReadingSession,
      args: [SITE_RULES, options],
    });
    const result = injection?.result as ReadingSessionResult | undefined;

    if (!result?.ok) {
      if (mode === 'manual') {
        throw new Error(result?.error || getMessage('extractContentFailed', 'Could not extract readable content'));
      }
      debugLog('reading-session:auto-skip', { tabId, reason: result?.reason ?? result?.error });
      return;
    }

    debugLog('reading-session:injected', {
      tabId,
      mode,
      contentLength: result.length,
      method: result.method,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    debugError('reading-session:inject-error', error, { tabId, mode });
    if (mode === 'manual') {
      await notifyFailure(`${getMessage('enterReadingSessionFailed', 'Unable to enter Reading Session')}: ${message}`);
    }
  }
}

function setupAutoEnterReadingMode(): void {
  const enteredThisNav = new Map<number, boolean>();

  browser.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    // 新导航开始（整页加载或 SPA 改 URL）→ 允许本次导航再自动进入一次。
    if (isNavigationResetEvent(changeInfo)) {
      enteredThisNav.delete(tabId);
    }

    if (!isEnterCandidateEvent(changeInfo)) return;
    if (enteredThisNav.get(tabId)) return;

    const url = tab.url;
    if (!isInjectableUrl(url) || !isReadableUrl(url || '', SITE_RULES)) return;

    const { autoEnterReadingMode } = await getOptions();
    if (!autoEnterReadingMode) return;

    // await 之后再核对一次，防止同一次加载的多个 complete 事件重复注入。
    if (enteredThisNav.get(tabId)) return;
    enteredThisNav.set(tabId, true);

    await injectReadingSession(tabId, 'auto');
  });

  browser.tabs.onRemoved.addListener((tabId) => {
    enteredThisNav.delete(tabId);
  });
}

function isInjectableUrl(url?: string): boolean {
  return Boolean(url && /^https?:\/\//i.test(url));
}

function setupGenerateQuestionsPort(): void {
  const runtime = getChromeRuntime();
  if (!runtime) {
    debugLog('port:unavailable', { reason: 'chrome.runtime missing' });
    return;
  }

  runtime.onConnect.addListener((port: RuntimePort) => {
    if (port.name !== GENERATE_PORT_NAME) return;

    const connectionId = createRequestId();
    debugLog('port:connected', { connectionId, portName: port.name });

    port.onDisconnect.addListener(() => {
      debugLog('port:disconnect', {
        connectionId,
        portName: port.name,
        error: runtime.lastError?.message,
      });
    });

    port.onMessage.addListener((message: unknown) => {
      if (!isGenerateQuestionsPortMessage(message)) {
        debugLog('port:message', {
          connectionId,
          accepted: false,
          type: getMessageType(message),
        });
        postPortMessage(port, {
          ok: false,
          requestId: getRequestId(message),
          error: 'Invalid generate questions port message',
        });
        return;
      }

      const requestId = normalizeRequestId(message.requestId);
      debugLog('port:message', {
        connectionId,
        requestId,
        type: message.type,
        contentLength: message.content.length,
        declaredContentLength: message.contentLength,
      });

      void handleGenerateQuestions(message.content, requestId).then((response) => {
        postPortMessage(port, response);
      });
    });
  });
}

function setupLegacyGenerateQuestionsMessage(): void {
  const runtime = getChromeRuntime();
  if (!runtime) {
    debugLog('legacy-message:unavailable', { reason: 'chrome.runtime missing' });
    return;
  }

  runtime.onMessage.addListener((message: unknown, _sender: unknown, sendResponse: (response?: unknown) => void) => {
    if (!isGenerateQuestionsMessage(message)) return false;

    const requestId = normalizeRequestId(message.requestId);
    debugLog('legacy-message:start', {
      requestId,
      contentLength: message.content.length,
      declaredContentLength: message.contentLength,
    });

    void handleGenerateQuestions(message.content, requestId)
      .then((response) => {
        if (response.ok) {
          debugLog('legacy-message:success', {
            requestId,
            questionsCount: response.questions.length,
          });
        } else {
          debugLog('legacy-message:error', {
            requestId,
            error: response.error,
          });
        }
        sendResponse(response);
      })
      .catch((error) => {
        debugError('legacy-message:error', error, { requestId });
        sendResponse({
          ok: false,
          requestId,
          error: getErrorMessage(error),
        });
      });

    return true;
  });
}

function isGenerateQuestionsMessage(message: unknown): message is GenerateQuestionsMessage {
  return Boolean(
    message &&
      typeof message === 'object' &&
      (message as GenerateQuestionsMessage).type === LEGACY_GENERATE_TYPE &&
      typeof (message as GenerateQuestionsMessage).content === 'string',
  );
}

function isGenerateQuestionsPortMessage(message: unknown): message is GenerateQuestionsPortMessage {
  return Boolean(
    message &&
      typeof message === 'object' &&
      (message as GenerateQuestionsPortMessage).type === PORT_GENERATE_START_TYPE &&
      typeof (message as GenerateQuestionsPortMessage).requestId === 'string' &&
      typeof (message as GenerateQuestionsPortMessage).content === 'string',
  );
}

async function handleGenerateQuestions(content: string, requestId: string): Promise<GenerateQuestionsResponse> {
  debugLog('generate:start', { requestId, contentLength: content.length });

  try {
    const response = await generateQuestion(content, undefined, requestId);
    const questions = response.questions || [];
    debugLog('generate:success', {
      requestId,
      fileId: response.file_id,
      questionsCount: questions.length,
    });
    return {
      ok: true,
      requestId,
      questions,
    };
  } catch (error) {
    debugError('generate:error', error, { requestId });
    return { ok: false, requestId, error: getErrorMessage(error) };
  }
}

function postPortMessage(port: RuntimePort, response: GenerateQuestionsResponse): void {
  try {
    port.postMessage(response);
  } catch (error) {
    debugError('port:post-error', error, { requestId: response.requestId, ok: response.ok });
  }
}

function getChromeRuntime(): RuntimeApi | undefined {
  return (globalThis as typeof globalThis & { chrome?: ChromeGlobal }).chrome?.runtime;
}

function createRequestId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeRequestId(requestId?: string): string {
  return requestId && requestId.trim() ? requestId : createRequestId();
}

function getRequestId(message: unknown): string {
  if (message && typeof message === 'object' && typeof (message as { requestId?: unknown }).requestId === 'string') {
    return normalizeRequestId((message as { requestId: string }).requestId);
  }
  return createRequestId();
}

function getMessageType(message: unknown): string | undefined {
  if (message && typeof message === 'object' && 'type' in message) {
    return String((message as { type?: unknown }).type);
  }
  return undefined;
}

function getUrlOrigin(url?: string): string | undefined {
  if (!url) return undefined;

  try {
    return new URL(url).origin;
  } catch {
    return undefined;
  }
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function serializeError(error: unknown): { message: string; stack?: string } {
  if (error instanceof Error) {
    return { message: error.message, stack: error.stack };
  }
  return { message: String(error) };
}

function sanitizeDebugDetails(details: Record<string, unknown>): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(details)) {
    if (key === 'content' && typeof value === 'string') {
      sanitized.contentLength = value.length;
      continue;
    }
    sanitized[key] = value;
  }

  return sanitized;
}

function debugLog(event: string, details: Record<string, unknown> = {}): void {
  console.info(DEBUG_PREFIX, event, sanitizeDebugDetails(details));
}

function debugError(event: string, error: unknown, details: Record<string, unknown> = {}): void {
  console.error(DEBUG_PREFIX, event, {
    ...sanitizeDebugDetails(details),
    error: serializeError(error),
  });
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
