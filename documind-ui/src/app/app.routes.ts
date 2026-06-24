import { Routes } from '@angular/router';

export const routes: Routes = [
    {path: '', redirectTo: 'dashboard', pathMatch: 'full'},
    {path: 'dashboard', loadComponent: () => import('./components/dashboard/dashboard').then(m => m.Dashboard)},
    {path: 'chat', loadComponent: () => import('./components/chat/chat').then(m => m.Chat)},
    {path: 'documents', loadComponent: () => import('./components/my-document/my-document').then(m => m.MyDocument)},
];
