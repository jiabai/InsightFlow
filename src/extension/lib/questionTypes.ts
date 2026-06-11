// 问题项接口
export interface QuestionItem {
  question: string;
  label: string;
  chunk_id: number;
  question_id: number;
}

// 问题响应接口
export interface QuestionResponse {
  content_id: string;
  questions: QuestionItem[];
}
