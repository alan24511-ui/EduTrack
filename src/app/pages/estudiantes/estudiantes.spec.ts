import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Estudiantes } from './estudiantes';

describe('Estudiantes', () => {
  let component: Estudiantes;
  let fixture: ComponentFixture<Estudiantes>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Estudiantes],
      providers: [provideRouter([])],
    })
      .compileComponents();

    fixture = TestBed.createComponent(Estudiantes);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
