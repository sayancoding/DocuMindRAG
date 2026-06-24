import { Component, signal } from '@angular/core';
import { RouterLink } from "@angular/router";

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class Sidebar {
  currentWorkspace = signal('dashboard'); 

  sidebarItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'clock_loader_60' },
    { id: 'chat', label: 'Chat', icon: 'chat' },
    { id: 'documents', label: 'My Documents', icon: 'folder' }
  ];

  setWorkspace(viewId: string): void {
    this.currentWorkspace.set(viewId);
  }
}
