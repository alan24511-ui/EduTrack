import { Component } from '@angular/core';
import { Sidebar } from '../sidebar/sidebar';

@Component({
  selector: 'app-layout',
  imports: [Sidebar],
  templateUrl: './layout.html',
})
export class Layout {}