import { Component, inject } from '@angular/core';
import { DocumentItem } from '../../models/DocumentItem';
import { ApiGateway } from '../../services/api-gateway';
import { Chat } from "../chat/chat";

@Component({
  selector: 'app-dashboard',
  imports: [],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  private apiGateway = inject(ApiGateway);

  

}
