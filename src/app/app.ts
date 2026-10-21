import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink],
  templateUrl: './app.html',
})
export class App {
  private router = inject(Router);

  get sinBarra() {
    return ['/login', '/dashboard'].some(r => this.router.url.startsWith(r));
  }
}