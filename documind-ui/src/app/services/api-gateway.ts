import { HttpClient } from '@angular/common/http';
import { Inject, Service, NgZone, Injectable, inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { DocumentItem } from '../models/DocumentItem';

@Injectable({
  providedIn: 'root' // 🌟 Standard Angular service decorator
})
export class ApiGateway {
  private http = inject(HttpClient);
  private zone = inject(NgZone);

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
}
