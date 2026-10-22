import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Layout } from '../../components/layout/layout';

@Component({
  imports: [Layout, RouterLink],
  selector: 'app-dashboard',
  styleUrl: './dashboard.css',
  templateUrl: './dashboard.html',
})
export class Dashboard {
}
