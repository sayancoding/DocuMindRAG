import { Component, inject } from '@angular/core';
import { ApiGateway } from '../../services/api-gateway';
import { AsyncPipe, KeyValuePipe } from '@angular/common';

@Component({
  selector: 'app-documents',
  imports: [AsyncPipe,KeyValuePipe],
  templateUrl: './documents.html',
  styleUrl: './documents.css',
})
export class Documents {
  private apiGateway = inject(ApiGateway);

  // Expose the raw streams straight to the HTML template layout
  activeJobs$ = this.apiGateway.activeUploads$;
  completedRoster$ = this.apiGateway.documentsRoster$;

  ngOnInit(): void {
    this.apiGateway.fetchDocumentsRoster();
  }

  // Captures file selection from standard input click click
  onFilePicked(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.apiGateway.uploadAndTrackDocument(input.files[0]);
    }
  }

  triggerSelect(inputRef: HTMLInputElement): void {
    inputRef.click();
  }

  deleteDocument(documentId: string): void {
    this.apiGateway.deleteDocument(documentId);
  }
}
