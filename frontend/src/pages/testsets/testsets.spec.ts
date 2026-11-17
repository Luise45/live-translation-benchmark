import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Testsets } from './testsets';

describe('Testsets', () => {
  let component: Testsets;
  let fixture: ComponentFixture<Testsets>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Testsets],
    }).compileComponents();

    fixture = TestBed.createComponent(Testsets);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
