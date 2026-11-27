import { TestBed } from '@angular/core/testing';
import { RunHistory } from './run-history';

describe('RunHistory', () => {
  let component: RunHistory;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RunHistory],
    }).compileComponents();

    const fixture = TestBed.createComponent(RunHistory);
    component = fixture.componentInstance;
  });

  // anfangszustand
  it('zeigt die Runs standardmäßig absteigend sortiert an', () => {
    const runIds = component.filteredRuns.map(run => run.id);

    expect(runIds).toEqual([10, 9, 8, 7, 6]);
  });

  it('zeigt standardmäßig fünf Einträge pro Seite an', () => {
    expect(component.entriesPerPage).toBe(5);
    expect(component.visibleRuns.length).toBe(5);
    expect(component.totalPageCount).toBe(1);
  });

  it('formatiert Run-Nummern mit führenden Nullen', () => {
    expect(component.formatRunId(9)).toBe('#0009');
    expect(component.formatRunId(10)).toBe('#0010');
  });

  // suche
  it('filtert sofort nach der Run-ID', () => {
    component.updateSearch('#0009');

    const runIds = component.filteredRuns.map(run => run.id);

    expect(runIds).toEqual([9]);
  });

  it('sucht unabhängig von Groß- und Kleinschreibung', () => {
    component.updateSearch('BILLING');

    const runIds = component.filteredRuns.map(run => run.id);

    expect(runIds).toEqual([10, 9]);
  });

  it('setzt beim Suchen die aktuelle Seite zurück', () => {
    component.currentPage = 2;

    component.updateSearch('OpenAI');

    expect(component.currentPage).toBe(1);
  });

  // filter geöffnet
  it('übernimmt Filter erst nach Anwenden', () => {
    component.openFilterPanel();
    component.toggleDraftStatus('failed');

    expect(component.filteredRuns.length).toBe(5);

    component.applyFilters();

    const runStatuses = component.filteredRuns.map(
      run => run.status
    );

    expect(runStatuses).toEqual(['failed']);
    expect(component.isFilterPanelOpen).toBe(false);
  });

  it('verwirft nicht angewendete Filter beim Schließen', () => {
    component.openFilterPanel();
    component.toggleDraftStatus('failed');

    component.closeFilterPanel();

    expect(component.appliedFilters.statuses).toEqual([]);
    expect(component.draftFilters.statuses).toEqual([]);
    expect(component.filteredRuns.length).toBe(5);
  });

  it('erlaubt die Mehrfachauswahl von Status', () => {
    component.openFilterPanel();

    component.toggleDraftStatus('completed');
    component.toggleDraftStatus('failed');

    expect(component.draftFilters.statuses).toEqual([
      'completed',
      'failed',
    ]);

    component.toggleDraftStatus('completed');

    expect(component.draftFilters.statuses).toEqual([
      'failed',
    ]);
  });

  it('sortiert Run-Nummern aufsteigend', () => {
    component.openFilterPanel();
    component.selectDraftSortOrder('ascending');
    component.applyFilters();

    const runIds = component.filteredRuns.map(run => run.id);

    expect(runIds).toEqual([6, 7, 8, 9, 10]);
  });

  it('filtert einen eigenen Zeitraum', () => {
    component.openFilterPanel();
    component.selectDraftPeriod('custom');

    component.draftFilters.customStart = '2026-11-22';
    component.draftFilters.customEnd = '2026-11-24';

    component.applyFilters();

    const runIds = component.filteredRuns.map(run => run.id);

    expect(runIds).toEqual([9, 8, 7]);
  });

  it('setzt Suche und Filter vollständig zurück', () => {
    component.updateSearch('Google');

    component.openFilterPanel();
    component.toggleDraftStatus('failed');
    component.applyFilters();

    component.resetAllFilters();

    expect(component.searchText).toBe('');
    expect(component.appliedFilters.statuses).toEqual([]);
    expect(component.appliedFilters.period).toBe('all');
    expect(component.appliedFilters.sortOrder).toBe('descending');
    expect(component.currentPage).toBe(1);
    expect(component.filteredRuns.length).toBe(5);
  });

  // Paginator
  it('unterstützt fünf, zehn und zwanzig Einträge pro Seite', () => {
    expect(component.entriesPerPageOptions).toEqual([
      5,
      10,
      20,
    ]);
  });

  it('ändert die Anzahl der Einträge pro Seite', () => {
    component.updateEntriesPerPage('10');

    expect(component.entriesPerPage).toBe(10);
    expect(component.currentPage).toBe(1);
    expect(component.visibleRuns.length).toBe(5);
  });

  it('verhindert einen Seitenwechsel außerhalb der verfügbaren Seiten', () => {
    component.selectPage(2);

    expect(component.currentPage).toBe(1);

    component.selectPage(0);

    expect(component.currentPage).toBe(1);
  });

  // Run details
  it('öffnet einen Run und wählt den ersten Candidate aus', () => {
    component.toggleRunDetails(10);

    expect(component.expandedRunId).toBe(10);
    expect(component.selectedRun?.id).toBe(10);
    expect(component.selectedCandidateId).toBe('run-10-openai');
    expect(component.activeDetailsTab).toBe('overview');
  });

  it('schließt einen Run beim erneuten Anklicken', () => {
    component.toggleRunDetails(10);
    component.toggleRunDetails(10);

    expect(component.expandedRunId).toBeNull();
    expect(component.selectedCandidateId).toBeNull();
  });

  it('zeigt immer nur die Details eines Runs an', () => {
    component.toggleRunDetails(10);
    component.toggleRunDetails(9);

    expect(component.expandedRunId).toBe(9);
    expect(component.selectedRun?.id).toBe(9);
    expect(component.selectedCandidateId).toBe('run-09-openai');
  });

  it('schließt Run-Details beim Ändern der Einträge pro Seite', () => {
    component.toggleRunDetails(10);

    component.updateEntriesPerPage('10');

    expect(component.expandedRunId).toBeNull();
    expect(component.selectedCandidateId).toBeNull();
  });

  // Candidate auswahl 
  it('wechselt zwischen den Candidates eines Runs', () => {
    component.toggleRunDetails(10);
    component.selectCandidate('run-10-google');

    expect(component.selectedDetailsCandidate?.id).toBe(
      'run-10-google'
    );

    expect(component.isCandidateSelected('run-10-google')).toBe(true);
    expect(component.isCandidateSelected('run-10-openai')).toBe(false);
  });

  it('behält den ausgewählten Candidate beim Tabwechsel', () => {
    component.toggleRunDetails(10);
    component.selectCandidate('run-10-google');

    component.selectDetailsTab('testcases');

    expect(component.activeDetailsTab).toBe('testcases');
    expect(component.selectedDetailsCandidate?.id).toBe(
      'run-10-google'
    );
  });

  // coverage + scores
  it('zeigt bei Partial Coverage keinen Overall Score', () => {
    component.toggleRunDetails(10);
    component.selectCandidate('run-10-microsoft');

    const candidate = component.selectedDetailsCandidate;

    expect(candidate).not.toBeNull();
    expect(candidate?.coverageSupported).toBe(3);
    expect(candidate?.coverageRequired).toBe(4);
    expect(candidate?.overallScore).toBeNull();
    expect(component.getCoverageLabel(candidate!)).toBe('3/4');
  });

  it('formatiert Scores mit genau einer Nachkommastelle', () => {
    expect(component.getMetricValue(95.1)).toBe('95.1');
    expect(component.getMetricValue(95)).toBe('95.0');
  });

  it('zeigt fehlende Metrikwerte nicht als null oder 0 an', () => {
    expect(component.getMetricValue(null)).toBe('–');
  });

  // Status
  it('kennt nur Abgeschlossen und Fehlgeschlagen', () => {
    expect(component.getStatusLabel('completed')).toBe(
      'Abgeschlossen'
    );

    expect(component.getStatusLabel('failed')).toBe(
      'Fehlgeschlagen'
    );

    expect(
      component.runs.every(
        run => run.status === 'completed' || run.status === 'failed'
      )
    ).toBe(true);
  });
});