import { Component, inject } from '@angular/core';
import { ApiGateway } from '../../services/api-gateway';
import { AsyncPipe, CommonModule, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-chat',
  imports: [CommonModule,AsyncPipe,FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.css',
})
export class Chat {
  private apiGateway = inject(ApiGateway);

  // Expose the raw streams straight to the HTML template layout
  activeJobs$ = this.apiGateway.activeUploads$;
  completedRoster$ = this.apiGateway.documentsRoster$;
  // Expose the raw messages subject observable stream straight 
  // to your HTML template layout
  conversation$ = this.apiGateway.messages$;

  activeDocId: string | null = null;
  activeDocName: string | null = null;
  userQuery = '';
  
  documentSelectionDropdownOpen = false;
  modelSelectionDropdownOpen = false;

  ngOnInit(): void {
    this.apiGateway.fetchDocumentsRoster();
  }

  sendMessage(): void {
    const rawText = this.userQuery.trim();
    if (!rawText) return;
    this.apiGateway.askRagQuestionNormal(rawText, this.activeDocId);
    this.userQuery = '';
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

  toggleDocumentSelectionDropdown(): void {
    this.documentSelectionDropdownOpen = !this.documentSelectionDropdownOpen;
  }
  toggleModelSelectionDropdown(): void {
    this.modelSelectionDropdownOpen = !this.modelSelectionDropdownOpen;
  }
  selectDocument(docId: string | null, docName: string | null): void {
    this.activeDocId = docId;
    this.activeDocName = docName;
    this.documentSelectionDropdownOpen = false; // Auto-close overlay tray after selection
  }
}
