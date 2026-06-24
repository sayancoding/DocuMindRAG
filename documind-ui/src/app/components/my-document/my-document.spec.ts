import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MyDocument } from './my-document';

describe('MyDocument', () => {
  let component: MyDocument;
  let fixture: ComponentFixture<MyDocument>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MyDocument],
    }).compileComponents();

    fixture = TestBed.createComponent(MyDocument);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
