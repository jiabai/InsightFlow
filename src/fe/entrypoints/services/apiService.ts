import { similarity } from '@/utils/stringUtils';
import type { QuestionResponse } from '@/lib/questionTypes';
import type { UploadResult } from '@/lib/uploadResult';
import { generateUserId, sha256 } from '@/utils/stringUtils';

// 删除FileInfo接口，因为我们不再需要它
export interface FileInfo {
  id: number;
  file_id: string;
  user_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  upload_time: string;
  stored_filename: string;
}

export interface GenerateAnswerResponse {
  answer: string;
  reasoning_content?: string | null;
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
 * 模拟API调用函数
 * @param endpoint 请求端点
 * @param data 请求参数
 * @returns 模拟API响应的Promise
 */
function simulateAPICall(
  endpoint: ApiEndpoint,
  data: GenerateQuestionParams | GenerateAnswerParams,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void,
  onProgress?: (partialAnswer: string) => void
): Promise<QuestionResponse | GenerateAnswerResponse> {
  return new Promise((resolve, reject) => {
    if (endpoint === 'generate-questions') {
      // 立即执行异步函数以支持await
      (async () => {
        try {
          // 调用uploadMarkdownContent方法
          if ('text' in data) {
            const questionResponse: QuestionResponse = await uploadMarkdownContent(data.text, onPollIntervalCreated);
            resolve(questionResponse);
          } else {
            reject(new Error('无效的参数: 缺少text字段'));
          }
        } catch (error) {
          console.error('获取问题列表失败:', error);
          reject(error); // 向上传递错误
        }
      })();
    // 修改simulateAPICall函数中的generate-answer端点处理逻辑
    } else if (endpoint === 'generate-answer') {
    // 使用实际的generateAnswer方法，而不是模拟回答
    (async () => {
    try {
      if ('question_id' in data && 'chunk_id' in data) {
        const answerResponse: GenerateAnswerResponse = await llmQueryStream(
          data.question_id,
          data.chunk_id,
          onProgress
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
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void
): Promise<QuestionResponse> {
  return simulateAPICall('generate-questions', { text }, onPollIntervalCreated) as Promise<QuestionResponse>;
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
  return simulateAPICall('generate-answer', { question_id, chunk_id }, undefined, onProgress) as Promise<GenerateAnswerResponse>;
}

export async function llmQueryStream(
  question_id: number,
  chunk_id: number,
  onProgress?: (partialAnswer: string) => void
): Promise<GenerateAnswerResponse> {
  console.log('🔄 开始流式查询:', { question_id, chunk_id: chunk_id });
  
  try {
    const response = await fetchWithTimeout(
      'http://39.107.59.41:18080/llm/query/stream',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
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
 * 简化的文件状态轮询函数 - 解决404过度处理问题
 * @param fileId 文件ID
 * @param onCompleted 完成回调
 * @param onFailed 失败回调
 * @param interval 轮询间隔
 * @param onIntervalCreated 轮询创建回调
 */
export async function pollFileStatus(
  fileId: string,
  onCompleted: (fileId: string) => Promise<void>,
  onFailed?: () => void,
  interval: number = 3000,
  onIntervalCreated?: (intervalId: ReturnType<typeof setInterval>) => void
) {
  const maxAttempts = 60;
  let attempts = 0;
  
  const intervalId = setInterval(async () => {
    attempts++;
    
    try {
      const statusResponse = await fetchWithTimeout(
        `http://39.107.59.41:18080/file_status/${fileId}`,
        { method: 'GET' },
        5000
      );

      if (!statusResponse.ok) {
        // 简化404处理 - 只在超时后报错
        if (attempts >= maxAttempts) {
          clearInterval(intervalId);
          console.error(`文件状态检查超时 (${maxAttempts * 3}秒)`);
          onFailed?.();
        }
        return;
      }

      const statusResult = await statusResponse.json();
      
      switch (statusResult.status) {
        case 'Completed':
          clearInterval(intervalId);
          await onCompleted(fileId);
          break;
          
        case 'Failed':
          clearInterval(intervalId);
          console.error('文件处理失败:', statusResult);
          onFailed?.();
          break;
          
        case 'Processing':
        case 'Pending':
          if (attempts >= maxAttempts) {
            clearInterval(intervalId);
            onFailed?.();
          }
          break;
          
        default:
          // 未知状态继续轮询
          break;
      }
    } catch (error) {
      if (attempts >= maxAttempts) {
        clearInterval(intervalId);
        onFailed?.();
      }
    }
  }, interval);

  onIntervalCreated?.(intervalId);
}

/**
 * 上传Markdown内容到服务器
 * @param markdownContent Markdown内容
 * @returns 问题响应
 * @description 上传接口规范：
 * URL: http://39.107.59.41:18080/upload/{user_id}
 * Method: POST
 * Content-Type: multipart/form-data
 * Body: multipart/form-data 包含文件字段
 */
export async function uploadMarkdownContent(
  markdownContent: string,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void
): Promise<QuestionResponse> {
  const MAX_RETRIES = 2;
  const RETRY_DELAY = 1000;
  
  try {
    // 1. 生成用户ID和哈希
    const userId = generateUserId();
    const hashedUserIdHex = await sha256(userId);

    // 2. 创建multipart/form-data数据
    const blob = new Blob([markdownContent], { type: 'text/markdown' });
    const formData = new FormData();
    formData.append('file', blob, 'content.md'); // 文件字段名为 'file'

    // 3. 构建正确的URL
    const uploadUrl = `http://39.107.59.41:18080/upload/${hashedUserIdHex}`;
    console.log('📤 开始上传:', uploadUrl);

    // 4. 执行上传请求
    const response = await fetchWithTimeout(uploadUrl, {
      method: 'POST',
      body: formData,
      // 注意：不要手动设置Content-Type，让浏览器自动设置multipart边界
      headers: { 
        'Accept': 'application/json' // 只设置Accept头
      },
      credentials: 'include'
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '无法获取错误详情');
      console.error('❌ 上传失败:', response.status, errorText);
      return { questions: [], file_id: '' };
    }

    const result: UploadResult = await response.json();
    console.log('✅ 上传成功:', result);

    // 5. 继续后续处理流程
    return await processAfterUpload(result, hashedUserIdHex, onPollIntervalCreated);
    
  } catch (error) {
    console.error('💥 上传过程错误:', error);
    return { questions: [], file_id: '' };
  }
}

// 上传后的处理流程
async function processAfterUpload(
  result: UploadResult,
  hashedUserIdHex: string,
  onPollIntervalCreated?: (pollIntervalId: ReturnType<typeof setInterval>) => void
): Promise<QuestionResponse> {
  try {
    // 调用generate接口生成问题
    const generateUrl = `http://39.107.59.41:18080/questions/generate/${hashedUserIdHex}/${result.file_id}`;
    console.log('🔄 生成问题:', generateUrl);

    const generateResponse = await fetchWithTimeout(generateUrl, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
      credentials: 'include'
    });

    if (!generateResponse.ok) {
      console.error('❌ 生成问题失败:', generateResponse.status);
      return { questions: [], file_id: result.file_id };
    }

    // 轮询获取结果
    return new Promise<QuestionResponse>((resolve) => {
      pollFileStatus(
        result.file_id,
        async (fileId) => {
          try {
            const questionsUrl = `http://39.107.59.41:18080/questions/${fileId}`;
            const questionsResponse = await fetchWithTimeout(questionsUrl, {
              method: 'GET',
              headers: { 'Accept': 'application/json' }
            });

            if (!questionsResponse.ok) {
              console.error('❌ 获取问题列表失败:', questionsResponse.status);
              resolve({ questions: [], file_id: fileId });
              return;
            }

            const questionsResult = await questionsResponse.json() as QuestionResponse;
            console.log('✅ 获取问题列表成功:', questionsResult);
            resolve(questionsResult);
          } catch (error) {
            console.error('💥 获取问题列表错误:', error);
            resolve({ questions: [], file_id: fileId });
          }
        },
        () => {
          console.error('⏰ 文件处理超时');
          resolve({ questions: [], file_id: result.file_id });
        },
        3000,
        onPollIntervalCreated
      );
    });
  } catch (error) {
    console.error('💥 后续处理错误:', error);
    return { questions: [], file_id: result.file_id };
  }
}

// 首先，将fetchWithTimeout提取为独立函数
const fetchWithTimeout = (url: string, options: RequestInit, timeout = 30000) => {
  return Promise.race([
    fetch(url, options),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('请求超时')), timeout)
    )
  ]);
};


/**
 * 简化的获取用户文件列表函数
 * @param userIdHash 用户ID的哈希值
 * @returns 文件列表
 */
async function getUserFiles(userIdHash: string): Promise<any[]> {
  const filesUrl = `http://39.107.59.41:18080/files/${userIdHash}`;
  
  try {
    const response = await fetchWithTimeout(filesUrl, {
      method: 'GET',
      headers: { 
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      },
      credentials: 'include'
    });

    if (!response.ok) {
      // 所有错误统一处理为返回空数组
      console.warn(`获取文件列表失败: ${response.status}`);
      return [];
    }

    const files = await response.json();
    return Array.isArray(files) ? files : [];
    
  } catch (error) {
    // 网络错误也返回空数组
    console.warn('获取文件列表出错:', error);
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
  handler: StreamResponseHandler
): Promise<void> {
  try {
    const answerUrl = `http://39.107.59.41:18080/llm/query/stream`;
    
    const response = await fetchWithTimeout(answerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
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
