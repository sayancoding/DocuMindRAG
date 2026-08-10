import { Component, signal } from '@angular/core';
import { RouterLink } from "@angular/router";

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class Sidebar {
  currentWorkspace = signal('documents'); 
  toggleOptionsPopup = signal(false);

  sidebarItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'clock_loader_60' },
    { id: 'chat', label: 'Chat', icon: 'chat' },
    { id: 'documents', label: 'Documents', icon: 'folder' }
  ];

  setWorkspace(viewId: string): void {
    this.currentWorkspace.set(viewId);
  }

  setToggleOptionsPopup(): void {
    this.toggleOptionsPopup.set(!this.toggleOptionsPopup());
  }
}
