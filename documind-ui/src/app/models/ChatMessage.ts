export interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  time: string;
}
