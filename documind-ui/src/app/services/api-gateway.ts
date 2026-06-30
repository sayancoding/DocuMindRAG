import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { DocumentItem } from '../models/DocumentItem';
import { ChatMessage } from '../models/ChatMessage';

@Injectable({
  providedIn: 'root'
})
export class ApiGateway {
  private http = inject(HttpClient);

  private gatewayBaseUrl = 'http://localhost:8081/api/gateway';

  private rosterSubject = new BehaviorSubject<DocumentItem[]>([]);
  documentsRoster$ = this.rosterSubject.asObservable();

  private activeUploadsSubject = new BehaviorSubject<{ [fileName: string]: DocumentItem }>({});
  activeUploads$ = this.activeUploadsSubject.asObservable();

  uploadAndTrackDocument(file: File): void {
    const formData = new FormData();
    formData.append('file', file);

    const initialJob: DocumentItem = {
      name: file.name,
      date: 'Today',
      progress: 10,
      stage: 'uploading',
      statusText: 'Uploading...',
    };

    this.activeUploadsSubject.next({
      ...this.activeUploadsSubject.value,
      [file.name]: initialJob,
    });

    this.http.post(`${this.gatewayBaseUrl}/ingest`, formData,{ responseType: 'text' }).subscribe({
      next: (data: any) => {
        this.establishSseConnection(file.name);
      },
      error: () => {
        this.handleFailure(file.name, 'Upload failed');
      }
    });
  }

  establishSseConnection(fileName: string): void {
    console.log(`Establishing SSE connection for ${fileName}`);
    const eventSource = new EventSource(`${this.gatewayBaseUrl}/stream/${fileName}`);
    eventSource.addEventListener('status-update', (event: any) => {
      const data = JSON.parse(event.data);
      console.log(`Received SSE update for ${fileName}:`, data);
      
      // 🌟 No zone wrapper needed! Just update the value stream directly
      if (data.stage === 'completed') {
        this.moveToRoster(data.fileName);
        eventSource.close();
      } else if (data.stage === 'failed') {
        this.handleFailure(data.fileName, data.statusText);
        eventSource.close();
      } else {
        const currentActive = this.activeUploadsSubject.value;
        this.activeUploadsSubject.next({
          ...currentActive,
          [data.fileName]: {
            name: data.fileName,
            date: 'Today',
            progress: data.progress,
            stage: data.stage,
            statusText: data.statusText
          }
        });
      }
    });

    eventSource.onerror = () => eventSource.close();
  }

  private moveToRoster(fileName: string): void {
    const currentActive = { ...this.activeUploadsSubject.value };
    const completedJob = currentActive[fileName];
    
    if (completedJob) {
      completedJob.stage = 'completed';
      completedJob.progress = 100;
      completedJob.statusText = 'Processed';

      // 1. Delete from active map
      delete currentActive[fileName];
      this.activeUploadsSubject.next(currentActive);

      // 2. Prepend to historical list
      this.rosterSubject.next([completedJob, ...this.rosterSubject.value]);
    }
  }
  private handleFailure(fileName: string, errorMsg: string): void {
    const currentActive = { ...this.activeUploadsSubject.value };
    if (currentActive[fileName]) {
      currentActive[fileName].stage = 'failed';
      currentActive[fileName].statusText = errorMsg;
      this.activeUploadsSubject.next(currentActive);
    }
  }

  // CHAT PART
  private messagesSubject = new BehaviorSubject<ChatMessage[]>([]);
  messages$ = this.messagesSubject.asObservable();

  /**
   * Executes a standard HTTP POST request to get the complete RAG answer in one single block
   */
  askRagQuestionNormal(queryText: string, activeDocumentId: string | null = null): void {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Immediately drop the user message bubble into view
    const userMsg: ChatMessage = { sender: 'user', text: queryText, time: timestamp };
    this.messagesSubject.next([...this.messagesSubject.value, userMsg]);

    // Assemble the precise payload structure matching your QueryRequest DTO class model
    const requestBody = {
      query: queryText,
      documentId: activeDocumentId
    };

    // 2. Add a temporary loading bubble for the AI response
    const loadingMsg: ChatMessage = { sender: 'ai', text: 'Thinking...', time: timestamp };
    const messagesWithLoading = [...this.messagesSubject.value, loadingMsg];
    this.messagesSubject.next(messagesWithLoading);

    const targetBubbleIndex = messagesWithLoading.length - 1;

    // 3. Make a standard http call
    this.http.post<{ answer: string }>(`${this.gatewayBaseUrl}/query`, requestBody).subscribe({
      next: (response) => {
        // Replace the "Thinking..." text with the full finished answer in one block
        const finalMessages = [...this.messagesSubject.value];
        finalMessages[targetBubbleIndex] = {
          sender: 'ai',
          text: response.answer,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        this.messagesSubject.next(finalMessages);
      },
      error: () => {
        const finalMessages = [...this.messagesSubject.value];
        finalMessages[targetBubbleIndex].text = '❌ Failed to extract answer context from your RAG vector database.';
        this.messagesSubject.next(finalMessages);
      }
    });
  }
}
