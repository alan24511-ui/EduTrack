import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Layout } from '../../components/layout/layout';

@Component({
  selector: 'app-admin',
  imports: [Layout, RouterLink],
  templateUrl: './admin.html',
  styleUrl: './admin.css'
})
export class Admin {

}