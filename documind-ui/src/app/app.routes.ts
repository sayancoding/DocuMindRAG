import { Routes } from '@angular/router';

export const routes: Routes = [
    {path: '', redirectTo: 'documents', pathMatch: 'full'},
    {path: 'dashboard', loadComponent: () => import('./components/dashboard/dashboard').then(m => m.Dashboard)},
    {path: 'chat', loadComponent: () => import('./components/chat/chat').then(m => m.Chat)},
    {path: 'documents', loadComponent: () => import('./components/documents/documents').then(m => m.Documents)},
];
