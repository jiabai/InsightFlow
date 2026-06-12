import { similarity } from '@/utils/stringUtils';
import type { QuestionResponse } from '@/lib/questionTypes';
import type { UploadResult } from '@/lib/uploadResult';
import type { ContentHistoryItem, FileStatusResponse, StreamChunk } from '@/lib/apiTypes';
import { generateUserId, sha256 } from '@/utils/stringUtils';

// 从 src/.env 读取后端 API 地址；未配置时默认连接本地开发服务。
const API_DEBUG_PREFIX = '[InsightFlow:api]';
const REQUEST_ID_HEADER = 'X-InsightFlow-Request-Id';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080').replace(/\/$/, '');
apiDebug('api:base-url', { baseUrl: API_BASE_URL });

export interface GenerateAnswerResponse {
  answer: string;
  reasoning_content?: string | null;
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
    if ((key === 'content' || key === 'markdownContent' || key === 'text') && typeof value === 'string') {
      sanitized[`${key}Length`] = value.length;
      continue;
    }
    sanitized[key] = value;
  }

  return sanitized;
}

function apiDebug(event: string, details: Record<string, unknown> = {}): void {
  console.info(API_DEBUG_PREFIX, event, sanitizeDebugDetails(details));
}

function apiDebugError(event: string, error: unknown, details: Record<string, unknown> = {}): void {
  console.error(API_DEBUG_PREFIX, event, {
    ...sanitizeDebugDetails(details),
    error: serializeError(error),
  });
}

function createApiRequestId(): string {
  return `api-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeRequestId(requestId?: string): string {
  return requestId && requestId.trim() ? requestId : createApiRequestId();
}

function withRequestIdHeaders(
  requestId: string,
  headers?: HeadersInit
): HeadersInit {
  return {
    ...(headers as Record<string, string> | undefined),
    [REQUEST_ID_HEADER]: requestId,
  };
}

// 定义API端点类型
type ApiEndpoint = 'generate-questions' | 'generate-answer';

// 定义请求数据类型
interface GenerateQuestionParams {
  text: string;
}

// 修改GenerateAnswerParams接口，添加question_id和chunk_id字段
interface GenerateAnswerParams {
  chunk_id: number;
  question_id: number;
}

/**
 * 执行API调用分发函数
 * @param endpoint 请求端点
 * @param data 请求参数
 * @returns API响应的Promise
 */
function executeAPICall(
  endpoint: ApiEndpoint,
  data: GenerateQuestionParams | GenerateAnswerParams,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void,
  onProgress?: (partialAnswer: string) => void,
  requestId?: string
): Promise<QuestionResponse | GenerateAnswerResponse> {
  const effectiveRequestId = normalizeRequestId(requestId);
  return new Promise((resolve, reject) => {
    if (endpoint === 'generate-questions') {
      // 立即执行异步函数以支持await
      (async () => {
        try {
          // 调用uploadMarkdownContent方法
          if ('text' in data) {
            const questionResponse: QuestionResponse = await uploadMarkdownContent(
              data.text,
              onPollIntervalCreated,
              effectiveRequestId
            );
            resolve(questionResponse);
          } else {
            reject(new Error('无效的参数: 缺少text字段'));
          }
        } catch (error) {
          console.error('获取问题列表失败:', error);
          reject(error); // 向上传递错误
        }
      })();
    // 处理 generate-answer 端点
    } else if (endpoint === 'generate-answer') {
    // 使用实际的generateAnswer方法，而不是模拟回答
    (async () => {
    try {
      if ('question_id' in data && 'chunk_id' in data) {
        const answerResponse: GenerateAnswerResponse = await llmQueryStream(
          data.question_id,
          data.chunk_id,
          onProgress,
          effectiveRequestId
        );
        resolve(answerResponse);
      } else {
        reject(new Error('无效的参数: 缺少question、question_id或chunk_id字段'));
      }
    } catch (error) {
      console.error('获取回答失败:', error);
      reject(error);
    }
    })();
    }
  });
}

/**
 * 生成问题API
 * @param text 选中文本
 * @returns 问题列表响应
 */
export function generateQuestion(
  text: string,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void,
  requestId?: string
): Promise<QuestionResponse> {
  return executeAPICall(
    'generate-questions',
    { text },
    onPollIntervalCreated,
    undefined,
    requestId
  ) as Promise<QuestionResponse>;
}

/**
 * 生成答案API
 * @param question_id 请求ID
 * @param chunk_id 文本块ID
 * @returns 问题列表响应
 */
export function generateAnswer(
  question_id: number,
  chunk_id: number,
  onProgress?: (partialAnswer: string) => void
): Promise<GenerateAnswerResponse> {
  return executeAPICall('generate-answer', { question_id, chunk_id }, undefined, onProgress) as Promise<GenerateAnswerResponse>;
}

export async function llmQueryStream(
  question_id: number,
  chunk_id: number,
  onProgress?: (partialAnswer: string) => void,
  requestId: string = normalizeRequestId()
): Promise<GenerateAnswerResponse> {
  console.log('🔄 开始流式查询:', { question_id, chunk_id: chunk_id, requestId });
  
  try {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/llm/query/stream`,
      {
        method: 'POST',
        headers: withRequestIdHeaders(requestId, {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        }),
        body: JSON.stringify({
          question_id,
          chunk_id,
          stream: true
        }),
      },
      60000 // 60秒超时
    );

    if (!response.ok) {
      const errorText = await response.text().catch(() => '无法获取错误详情');
      console.error('❌ 服务器响应错误:', response.status, errorText);
      throw new Error(`服务器返回错误: ${response.status} ${response.statusText}`);
    }

    // 检查是否为流式响应
    const contentType = response.headers.get('content-type') || '';
    console.log('📄 响应Content-Type:', contentType);

    let accumulatedAnswer = '';
    let accumulatedReasoning = '';
    let isFirstChunk = true;

    // 处理流式响应
    if (contentType.includes('text/event-stream') || contentType.includes('application/x-ndjson')) {
      console.log('🌊 检测到流式响应，开始处理...');
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          
          // 跳过空行和注释
          if (!trimmedLine || trimmedLine.startsWith(':')) continue;
          
          // 处理SSE格式的数据行
          if (trimmedLine.startsWith('data: ')) {
            const dataStr = trimmedLine.slice(6);
            
            // 跳过[DONE]标记
            if (dataStr.trim() === '[DONE]') continue;
            
            try {
              const data = JSON.parse(dataStr);
              
              // 提取内容
              const choice = data.choices?.[0];
              if (choice) {
                // 处理delta格式（流式）
                if (choice.delta) {
                  const delta = choice.delta;
                  if (delta.reasoning_content) {
                    accumulatedReasoning += delta.reasoning_content;
                  }
                  if (delta.content) {
                    accumulatedAnswer += delta.content;
                  }
                }
                // 处理message格式（非流式）
                else if (choice.message) {
                  const message = choice.message;
                  if (message.reasoning_content) {
                    accumulatedReasoning = message.reasoning_content;
                  }
                  if (message.content) {
                    accumulatedAnswer = message.content;
                  }
                }
              }
              
              // 构建当前响应
              let currentResponse = '';
              if (accumulatedReasoning) {
                currentResponse += `<div class="reasoning-section"><strong>推理过程：</strong><br>${accumulatedReasoning}</div><br>`;
              }
              if (accumulatedAnswer) {
                currentResponse += `<div class="answer-section"><strong>回答：</strong><br>${accumulatedAnswer}</div>`;
              }
              
              // 发送进度更新
              if (currentResponse && onProgress) {
                onProgress(currentResponse);
              }
              
              if (isFirstChunk) {
                console.log('✅ 收到第一个数据块:', data);
                isFirstChunk = false;
              }
              
            } catch (parseError) {
              console.warn('⚠️ 解析数据行失败:', trimmedLine, parseError);
            }
          }
        }
      }
      
      // 返回最终结果
      let finalAnswer = '';
      if (accumulatedReasoning) {
        finalAnswer += `<div class="reasoning-section"><strong>推理过程：</strong><br>${accumulatedReasoning}</div><br>`;
      }
      if (accumulatedAnswer) {
        finalAnswer += `<div class="answer-section"><strong>回答：</strong><br>${accumulatedAnswer}</div>`;
      }
      
      if (!finalAnswer) {
        finalAnswer = '服务器返回了空响应';
      }
      
      console.log('✅ 流式响应完成，最终答案长度:', finalAnswer.length);
      return {
        answer: finalAnswer,
        reasoning_content: accumulatedReasoning || undefined
      };
    }

    // 处理非流式响应
    console.log('📦 检测到非流式响应，直接解析...');
    const result = await response.json();
    console.log('📋 原始响应数据:', result);

    // 增强的响应解析逻辑
    return parseEnhancedResponse(result);

  } catch (error) {
    console.error('💥 llmQueryStream 发生错误:', error);
    throw error;
  }
}

// 增强的响应解析函数
function parseEnhancedResponse(result: any): GenerateAnswerResponse {
  console.log('🔍 开始解析响应:', result);
  
  try {
    // 1. 标准OpenAI格式
    if (result.choices && Array.isArray(result.choices) && result.choices.length > 0) {
      const choice = result.choices[0];
      
      let reasoningContent = '';
      let answerContent = '';
      
      // 处理delta格式（流式响应）
      if (choice.delta) {
        reasoningContent = choice.delta.reasoning_content || '';
        answerContent = choice.delta.content || '';
      }
      // 处理message格式（完整响应）
      else if (choice.message) {
        reasoningContent = choice.message.reasoning_content || '';
        answerContent = choice.message.content || '';
      }
      // 处理text格式
      else if (choice.text) {
        answerContent = choice.text;
      }
      
      let finalAnswer = '';
      if (reasoningContent) {
        finalAnswer += `<div class="reasoning-section"><strong>推理过程：</strong><br>${reasoningContent}</div><br>`;
      }
      if (answerContent) {
        finalAnswer += `<div class="answer-section"><strong>回答：</strong><br>${answerContent}</div>`;
      }
      
      if (!finalAnswer) {
        finalAnswer = '暂无回答内容';
      }
      
      console.log('✅ 使用标准OpenAI格式解析成功');
      return {
        answer: finalAnswer,
        reasoning_content: reasoningContent || undefined
      };
    }
    
    // 2. 兼容原有格式
    if (result.answer || result.response || result.content) {
      const answer = result.answer || result.response || result.content || '';
      const reasoning = result.reasoning_content || '';
      
      let finalAnswer = '';
      if (reasoning) {
        finalAnswer += `<div class="reasoning-section"><strong>推理过程：</strong><br>${reasoning}</div><br>`;
      }
      if (answer) {
        finalAnswer += `<div class="answer-section"><strong>回答：</strong><br>${answer}</div>`;
      }
      
      console.log('✅ 使用兼容格式解析成功');
      return {
        answer: finalAnswer || answer || '暂无回答内容',
        reasoning_content: reasoning || undefined
      };
    }
    
    // 3. 直接字符串响应
    if (typeof result === 'string') {
      console.log('✅ 使用字符串格式解析成功');
      return {
        answer: result,
        reasoning_content: undefined
      };
    }
    
    // 4. 提取任意文本字段
    const textFields = ['text', 'message', 'content', 'answer', 'response', 'data'];
    for (const field of textFields) {
      if (result[field] && typeof result[field] === 'string') {
        console.log(`✅ 使用${field}字段解析成功`);
        return {
          answer: result[field],
          reasoning_content: undefined
        };
      }
    }
    
    // 5. 默认返回JSON字符串
    const fallback = JSON.stringify(result, null, 2);
    console.log('⚠️ 使用默认JSON格式');
    return {
      answer: fallback || '服务器返回了空响应',
      reasoning_content: undefined
    };
    
  } catch (error) {
    console.error('❌ 解析响应失败:', error);
    return {
      answer: '解析响应失败，请稍后重试',
      reasoning_content: undefined
    };
  }
}
/**
 * 文件状态轮询函数
 * @param fileId 文件ID
 * @param onCompleted 完成回调
 * @param onFailed 失败回调
 * @param interval 轮询间隔
 * @param onIntervalCreated 轮询创建回调
 */
export async function pollFileStatus(
  fileId: string,
  onCompleted: (fileId: string) => Promise<void>,
  onFailed?: (error: Error) => void,
  interval: number = 3000,
  onIntervalCreated?: (intervalId: ReturnType<typeof setInterval>) => void,
  requestId?: string
) {
  if (!fileId) {
    throw new Error('缺少 file_id，无法检查文件处理状态');
  }
  requestId = normalizeRequestId(requestId);

  const maxAttempts = 60;
  let attempts = 0;
  
  const intervalId = setInterval(async () => {
    attempts++;
    
    try {
      apiDebug('file-status:poll', {
        requestId,
        fileId,
        attempt: attempts,
        maxAttempts,
      });

      const statusResponse = await fetchWithTimeout(
        `${API_BASE_URL}/file_status/${fileId}`,
        {
          method: 'GET',
          headers: withRequestIdHeaders(requestId),
        },
        5000
      );

      if (!statusResponse.ok) {
        clearInterval(intervalId);
        const errorText = await statusResponse.text().catch(() => '无法获取错误详情');
        apiDebugError('file-status:error', new Error(errorText), {
          requestId,
          fileId,
          attempt: attempts,
          httpStatus: statusResponse.status,
        });
        onFailed?.(new Error(`文件状态检查失败: ${statusResponse.status} ${errorText}`));
        return;
      }

      const statusResult = await statusResponse.json() as FileStatusResponse;
      apiDebug('file-status:poll', {
        requestId,
        fileId,
        attempt: attempts,
        httpStatus: statusResponse.status,
        status: statusResult.status,
      });
      
      switch (statusResult.status) {
        case 'Completed':
          clearInterval(intervalId);
          apiDebug('file-status:completed', {
            requestId,
            fileId,
            attempt: attempts,
          });
          await onCompleted(fileId);
          break;
          
        case 'Failed':
          clearInterval(intervalId);
          console.error('内容处理失败:', statusResult);
          apiDebug('file-status:failed', {
            requestId,
            fileId,
            attempt: attempts,
          });
          onFailed?.(new Error('文件处理失败'));
          break;
          
        case 'Processing':
        case 'Pending':
          if (attempts >= maxAttempts) {
            clearInterval(intervalId);
            apiDebugError('file-status:error', new Error('File status polling timed out'), {
              requestId,
              fileId,
              attempt: attempts,
              status: statusResult.status,
            });
            onFailed?.(new Error(`文件状态检查超时 (${maxAttempts * 3}秒)`));
          }
          break;
          
        default:
          if (attempts >= maxAttempts) {
            clearInterval(intervalId);
            apiDebugError('file-status:error', new Error(`Unknown file status: ${statusResult.status}`), {
              requestId,
              fileId,
              attempt: attempts,
              status: statusResult.status,
            });
            onFailed?.(new Error(`未知文件状态: ${statusResult.status}`));
          }
          break;
      }
    } catch (error) {
      clearInterval(intervalId);
      apiDebugError('file-status:error', error, {
        requestId,
        fileId,
        attempt: attempts,
      });
      onFailed?.(error instanceof Error ? error : new Error(String(error)));
    }
  }, interval);

  onIntervalCreated?.(intervalId);
}

/**
 * 上传Markdown内容到服务器
 * @param markdownContent Markdown内容
 * @returns 问题响应
 */
export async function uploadMarkdownContent(
  markdownContent: string,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void,
  requestId?: string
): Promise<QuestionResponse> {
  const MAX_RETRIES = 2;
  const RETRY_DELAY = 1000;
  
  try {
    requestId = normalizeRequestId(requestId);
    if (!markdownContent.trim()) {
      throw new Error('没有可上传的文本内容');
    }

    const userId = generateUserId();
    const hashedUserIdHex = await sha256(userId);

    const blob = new Blob([markdownContent], { type: 'text/markdown' });
    const formData = new FormData();
    formData.append('file', blob, 'content.md');

    const uploadUrl = `${API_BASE_URL}/upload/${hashedUserIdHex}`;
    apiDebug('upload:start', {
      requestId,
      url: uploadUrl,
      contentLength: markdownContent.length,
    });

    const response = await fetchWithTimeout(uploadUrl, {
      method: 'POST',
      body: formData,
      headers: withRequestIdHeaders(requestId, {
        'Accept': 'application/json'
      }),
      credentials: 'include'
    });

    apiDebug('upload:response', {
      requestId,
      status: response.status,
      ok: response.ok,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '无法获取错误详情');
      apiDebugError('upload:error', new Error(errorText), {
        requestId,
        status: response.status,
      });
      throw new Error(`上传失败: ${response.status} ${errorText}`);
    }

    const result: UploadResult = await response.json();
    apiDebug('upload:file-id', {
      requestId,
      fileId: result.file_id,
      hasFileId: Boolean(result.file_id),
    });

    return await processAfterUpload(result, hashedUserIdHex, onPollIntervalCreated, requestId);
    
  } catch (error) {
    apiDebugError('upload:error', error, { requestId });
    throw error instanceof Error ? error : new Error(String(error));
  }
}

// 上传后的处理流程
async function processAfterUpload(
  result: UploadResult,
  hashedUserIdHex: string,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void,
  requestId?: string
): Promise<QuestionResponse> {
  const traceRequestId = normalizeRequestId(requestId);
  try {
    const fileId = result.file_id;
    if (!fileId) {
      apiDebugError('upload:file-id', new Error('Upload response missing file_id'), { requestId: traceRequestId });
      throw new Error('上传响应缺少 file_id，无法生成问题');
    }

    const generateUrl = `${API_BASE_URL}/questions/generate/${hashedUserIdHex}/${fileId}`;
    apiDebug('questions-generate:start', {
      requestId: traceRequestId,
      fileId,
      url: generateUrl,
    });

    const generateResponse = await fetchWithTimeout(generateUrl, {
      method: 'POST',
      headers: withRequestIdHeaders(traceRequestId, { 'Accept': 'application/json' }),
      credentials: 'include'
    });

    apiDebug('questions-generate:response', {
      requestId: traceRequestId,
      fileId,
      status: generateResponse.status,
      ok: generateResponse.ok,
    });

    if (!generateResponse.ok) {
      const errorText = await generateResponse.text().catch(() => '无法获取错误详情');
      apiDebugError('questions-generate:error', new Error(errorText), {
        requestId: traceRequestId,
        fileId,
        status: generateResponse.status,
      });
      throw new Error(`生成问题失败: ${generateResponse.status} ${errorText}`);
    }
    await releaseResponseBody(generateResponse);

    // 轮询获取结果
    return new Promise<QuestionResponse>((resolve, reject) => {
      pollFileStatus(
        fileId,
        async (completedFileId) => {
          try {
            const questionsUrl = `${API_BASE_URL}/questions/${completedFileId}`;
            apiDebug('questions:fetch', {
              requestId: traceRequestId,
              fileId: completedFileId,
              url: questionsUrl,
            });
            const questionsResponse = await fetchWithTimeout(questionsUrl, {
              method: 'GET',
              headers: withRequestIdHeaders(traceRequestId, { 'Accept': 'application/json' })
            });

            apiDebug('questions:response', {
              requestId: traceRequestId,
              fileId: completedFileId,
              status: questionsResponse.status,
              ok: questionsResponse.ok,
            });

            if (!questionsResponse.ok) {
              const errorText = await questionsResponse.text().catch(() => '无法获取错误详情');
              apiDebugError('questions:response', new Error(errorText), {
                requestId: traceRequestId,
                fileId: completedFileId,
                status: questionsResponse.status,
              });
              reject(new Error(`获取问题列表失败: ${questionsResponse.status} ${errorText}`));
              return;
            }

            const questionsResult = await questionsResponse.json() as Partial<QuestionResponse>;
            apiDebug('questions:response', {
              requestId: traceRequestId,
              fileId: questionsResult.file_id || completedFileId,
              questionsCount: questionsResult.questions?.length || 0,
            });
            resolve({
              file_id: questionsResult.file_id || completedFileId,
              questions: questionsResult.questions || [],
            });
          } catch (error) {
            apiDebugError('questions:response', error, {
              requestId: traceRequestId,
              fileId: completedFileId,
            });
            reject(error instanceof Error ? error : new Error(String(error)));
          }
        },
        (error) => {
          apiDebugError('file-status:error', error, {
            requestId: traceRequestId,
            fileId,
          });
          reject(error);
        },
        3000,
        onPollIntervalCreated,
        traceRequestId
      ).catch(reject);
    });
  } catch (error) {
    apiDebugError('questions-generate:error', error, { requestId: traceRequestId });
    throw error instanceof Error ? error : new Error(String(error));
  }
}

// 首先，将fetchWithTimeout提取为独立函数
const fetchWithTimeout = async (url: string, options: RequestInit, timeout = 30000): Promise<Response> => {
  const controller = new AbortController();
  let didTimeout = false;
  const timeoutId = setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, timeout);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } catch (error) {
    if (didTimeout) {
      throw new Error('请求超时');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
};

async function releaseResponseBody(response: Response): Promise<void> {
  if (response.bodyUsed) return;

  try {
    await response.arrayBuffer();
  } catch {
    try {
      if (response.body) {
        await response.body.cancel();
      }
    } catch {
      // Best-effort cleanup only; the request itself has already completed.
    }
  }
}


/**
 * 获取用户历史内容列表
 * @param userIdHash 用户ID的哈希值
 * @returns 内容列表
 */
async function getUserContents(userIdHash: string): Promise<ContentHistoryItem[]> {
  const url = `${API_BASE_URL}/files/${userIdHash}`;
  const requestId = normalizeRequestId();
  
  try {
    const response = await fetchWithTimeout(url, {
      method: 'GET',
      headers: withRequestIdHeaders(requestId, {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      }),
      credentials: 'include'
    });

    if (!response.ok) {
      console.warn(`获取内容列表失败: ${response.status}`);
      return [];
    }

    const contents = await response.json();
    return Array.isArray(contents) ? contents : [];
    
  } catch (error) {
    console.warn('获取内容列表出错:', error);
    return [];
  }
}

// 添加流式响应处理接口
export interface StreamResponseHandler {
  onContent?: (content: string, isReasoning: boolean) => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

/**
 * 流式获取回答 - 支持逐步接收reasoning_content和content
 * @param question_id 请求ID
 * @param chunk_id 文本块ID
 * @param handler 流式响应处理器
 */
export async function llmQueryStreamWithProgress(
  question_id: number,
  chunk_id: number,
  handler: StreamResponseHandler,
  requestId: string = normalizeRequestId()
): Promise<void> {
  try {
    const answerUrl = `${API_BASE_URL}/llm/query/stream`;
    
    const response = await fetchWithTimeout(answerUrl, {
      method: 'POST',
      headers: withRequestIdHeaders(requestId, {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      }),
      body: JSON.stringify({
        question_id,
        chunk_id
      }),
      credentials: 'include'
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '无法获取错误详情');
      throw new Error(`获取回答失败: ${response.status} ${response.statusText}\n${errorText}`);
    }

    // 检查是否为流式响应
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/stream')) {
      // 处理流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法读取响应流');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.choices && data.choices[0]) {
                const delta = data.choices[0].delta;
                
                if (delta.reasoning_content) {
                  handler.onContent?.(delta.reasoning_content, true);
                }
                if (delta.content) {
                  handler.onContent?.(delta.content, false);
                }
              }
            } catch (e) {
              console.warn('解析流式数据失败:', e);
            }
          }
        }
      }
      
      handler.onComplete?.();
    } else {
      // 处理普通JSON响应
      const result = await response.json();
      
      // 处理OpenAI标准响应格式
      if (result.choices && Array.isArray(result.choices)) {
        const firstChoice = result.choices[0];
        if (firstChoice && firstChoice.delta) {
          const delta = firstChoice.delta;
          
          // 先发送reasoning_content
          if (delta.reasoning_content) {
            handler.onContent?.(delta.reasoning_content, true);
          }
          
          // 再发送content
          if (delta.content) {
            handler.onContent?.(delta.content, false);
          }
        }
      } else if (typeof result.answer === 'string') {
        // 兼容原有格式
        handler.onContent?.(result.answer, false);
      }
      
      handler.onComplete?.();
    }
  } catch (error) {
    handler.onError?.(error instanceof Error ? error : new Error(String(error)));
  }
}
