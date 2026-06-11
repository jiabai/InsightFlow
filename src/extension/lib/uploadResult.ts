/**
 * 内容上传结果接口
 * 表示内容上传到服务器后的响应数据结构
 */
export interface UploadResult {
  /** 文件唯一标识符 */
  file_id: string;
  /** 原始文件名 */
  filename: string;
  /** 内容大小(字节) */
  size: number;
  /** 内容类型 */
  type: string;
  /** 上传时间 */
  upload_time: string;
  /** 服务器存储的文件名 */
  stored_filename: string;
  /** 上传状态 */
  status: string;
}

/**
 * 内容处理状态枚举
 * 领域层状态：Pending → Processing → Completed / Failed
 */
export enum ContentStatus {
  PENDING = 'Pending',
  PROCESSING = 'Processing',
  COMPLETED = 'Completed',
  FAILED = 'Failed',
}
