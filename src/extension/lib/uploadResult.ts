/**
 * 上传结果数据类接口
 * 表示文件上传到服务器后的响应数据结构
 */
export interface UploadResult {
  /** 文件唯一标识符 */
  file_id: string;
  /** 原始文件名 */
  filename: string;
  /** 文件大小(字节) */
  size: number;
  /** 文件类型 */
  type: string;
  /** 上传时间 */
  upload_time: string;
  /** 服务器存储的文件名 */
  stored_filename: string;
  /** 上传状态 */
  status: string;
}

/**
 * 上传状态枚举
 * 定义了可能的上传状态值
 */
export enum UploadStatus {
  COMPLETED = 'Upload Completed',
  PROCESSING = 'Processing',
  FAILED = 'Upload Failed'
}