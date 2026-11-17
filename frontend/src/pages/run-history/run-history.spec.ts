import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RunHistory } from './run-history';

describe('RunHistory', () => {
  let component: RunHistory;
  let fixture: ComponentFixture<RunHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RunHistory],
    }).compileComponents();

    fixture = TestBed.createComponent(RunHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
