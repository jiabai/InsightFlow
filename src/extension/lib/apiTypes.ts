/**
 * API 响应类型定义
 * 统一 apiService.ts 中的所有返回类型，替换 any
 */

import type { QuestionItem } from './questionTypes';

/** 上传响应 */
export interface UploadResponse {
  content_id: string;
  filename: string;
  size: number;
  type: string;
  upload_time: string;
  stored_filename: string;
  status: string;
}

/** 内容状态查询响应 */
export interface ContentStatusResponse {
  content_id: string;
  status: 'Pending' | 'Processing' | 'Completed' | 'Failed';
}

/** 问题生成请求响应 */
export interface GenerateQuestionsResponse {
  content_id: string;
  questions: QuestionItem[];
}

/** 用户历史内容列表项 */
export interface ContentHistoryItem {
  id: number;
  content_id: string;
  user_id: string;
  filename: string;
  content_size: number;
  content_type: string;
  upload_time: string;
  stored_filename: string;
}

/** SSE 流式数据块 */
export interface StreamChunk {
  choices?: Array<{
    delta?: {
      reasoning_content?: string;
      content?: string;
    };
    message?: {
      reasoning_content?: string;
      content?: string;
    };
    text?: string;
  }>;
}
