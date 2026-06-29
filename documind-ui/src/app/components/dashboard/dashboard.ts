import { Component, inject } from '@angular/core';
import { DocumentItem } from '../../models/DocumentItem';
import { ApiGateway } from '../../services/api-gateway';
import { AsyncPipe, CommonModule, KeyValuePipe } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  imports: [KeyValuePipe,CommonModule,AsyncPipe],
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

}
