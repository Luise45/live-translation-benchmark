import { Routes } from '@angular/router';

import { Dashboard } from '../pages/dashboard/dashboard';
import { Runs } from '../pages/runs/runs';
import { RunHistory } from '../pages/run-history/run-history';
import { Testsets } from '../pages/testsets/testsets';

export const routes: Routes = [
  { path: '', redirectTo: 'runs', pathMatch: 'full' },
  { path: 'dashboard', component: Dashboard },
  { path: 'runs', component: Runs },
  { path: 'run-history', component: RunHistory },
  { path: 'testsets', component: Testsets },
  { path: '**', redirectTo: 'runs' },
];