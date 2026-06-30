import { Component, inject } from '@angular/core';
import { DocumentItem } from '../../models/DocumentItem';
import { ApiGateway } from '../../services/api-gateway';
import { AsyncPipe, CommonModule, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-dashboard',
  imports: [KeyValuePipe,CommonModule,AsyncPipe,FormsModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  private apiGateway = inject(ApiGateway);

  // Expose the raw streams straight to the HTML template layout
  activeJobs$ = this.apiGateway.activeUploads$;
  completedRoster$ = this.apiGateway.documentsRoster$;

  ngOnInit(): void {
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

  userQuery = '';
  selectedDocumentId: string | null = "057a6268-78ed-4c12-b76a-53d576bc3f7a"; 

  // Expose the raw messages subject observable stream straight to your HTML template layout
  conversation$ = this.apiGateway.messages$;

  sendMessage(): void {
    const rawText = this.userQuery.trim();
    if (!rawText) return;

    // Trigger our non-streaming HTTP post pipeline
    this.apiGateway.askRagQuestionNormal(rawText, this.selectedDocumentId);
    
    // Instantly wipe the text area clean for the next user question
    this.userQuery = '';
  }

  documentSelectionDropdownOpen = false;
  modelSelectionDropdownOpen = false;

  toggleDocumentSelectionDropdown(): void {
    this.documentSelectionDropdownOpen = !this.documentSelectionDropdownOpen;
  }
  toggleModelSelectionDropdown(): void {
    this.modelSelectionDropdownOpen = !this.modelSelectionDropdownOpen;
  }

}
