import { Routes } from '@angular/router';

import { Dashboard } from '../pages/dashboard/dashboard';
import { Runs } from '../pages/runs/runs';
import { RunHistory } from '../pages/run-history/run-history';
import { Testsets } from '../pages/testsets/testsets';
import { Tutorial } from '../pages/help/tutorial/tutorial';
import { AboutTool } from '../pages/help/about/about';

export const routes: Routes = [
  { path: '', redirectTo: 'runs', pathMatch: 'full' },
  { path: 'dashboard', component: Dashboard },
  { path: 'runs', component: Runs },
  { path: 'run-history', component: RunHistory },
  { path: 'testsets', component: Testsets },

  { path: 'help/tutorial', component: Tutorial },
  { path: 'help/about', component: AboutTool },

  { path: '**', redirectTo: 'runs' },
];
