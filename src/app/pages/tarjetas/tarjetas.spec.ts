import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { Tarjetas } from './tarjetas';

describe('Tarjetas', () => {
  let component: Tarjetas;
  let fixture: ComponentFixture<Tarjetas>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Tarjetas],
      providers: [provideRouter([]), provideHttpClient()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(Tarjetas);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
