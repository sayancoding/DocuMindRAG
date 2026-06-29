export interface DocumentItem {
  name: string;
  date: string;
  progress: number;
  stage: 'uploading' | 'extracting' | 'embedding' | 'vectorizing' | 'completed' | 'failed';
  statusText: string;
}