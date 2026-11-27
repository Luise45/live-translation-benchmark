import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';

type RunStatus = 'completed' | 'failed';
type SortOrder = 'ascending' | 'descending';
type PeriodOption = 'all' | '7-days' | '30-days' | 'custom';
type DetailsTab = 'overview' | 'testcases';

type CandidateScoreSet = {
  accuracy: number | null;
  criticalInfo: number | null;
  latency: number | null;
  robustness: number | null;
  reliability: number | null;
};

type DiagnosticItem = {
  label: string;
  value: string;
  isMissing?: boolean;
};

type DiagnosticGroup = {
  title: string;
  items: DiagnosticItem[];
};

type RepeatMeasurement = {
  id: string;
  label: string;
  technicalStatus: 'Abgeschlossen' | 'Fehlgeschlagen';
  rawValues: { label: string; value: string }[];
  errorReason?: string;
};

type TestVariation = {
  id: string;
  name: string;
  technicalStatus: 'Abgeschlossen' | 'Fehlgeschlagen';
  summaryValues: { label: string; value: string }[];
  repeatMeasurements: RepeatMeasurement[];
};

type TestCase = {
  id: string;
  title: string;
  language: string;
  variations: TestVariation[];
};

type CandidateTestsetGroup = {
  id: string;
  name: string;
  testCases: TestCase[];
};

type CandidateResult = {
  id: string;
  name: string;
  modelName: string;
  architecture: string;
  coverageSupported: number;
  coverageRequired: number;
  overallScore: number | null;
  overallScoreNote?: string;
  scores: CandidateScoreSet;
  diagnosticGroups: DiagnosticGroup[];
  testsetGroups: CandidateTestsetGroup[];
};

type BenchmarkRun = {
  id: number;
  finishedAtLabel: string;
  finishedAtDate: string;
  status: RunStatus;
  testsets: string[];
  languages: string[];
  candidates: CandidateResult[];
};

type AdvancedFilters = {
  sortOrder: SortOrder;
  statuses: RunStatus[];
  period: PeriodOption;
  customStart: string;
  customEnd: string;
};

function buildDiagnosticGroups(
  ttfaMedian: string,
  ttfaP95: string,
  turnGap: string,
  timeoutRate: string,
  retryRate: string,
  emptyOutputRate: string,
  metricXScore?: string,
  sttWer?: string
): DiagnosticGroup[] {
  const groups: DiagnosticGroup[] = [
    {
      title: 'End-to-End-Latenz',
      items: [
        { label: 'TTFA Median', value: ttfaMedian },
        { label: 'TTFA P95', value: ttfaP95 },
        { label: 'Turn Gap', value: turnGap },
      ],
    },
    {
      title: 'Zuverlässigkeit',
      items: [
        { label: 'Timeout-Rate', value: timeoutRate },
        { label: 'Retry-Rate', value: retryRate },
        { label: 'Leere Audioausgabe', value: emptyOutputRate },
      ],
    },
  ];

  if (metricXScore || sttWer) {
    groups.push({
      title: 'Qualitätsdiagnostik',
      items: [
        {
          label: 'MT COMET',
          value: metricXScore ?? 'Nicht verfügbar',
          isMissing: !metricXScore,
        },
        {
          label: 'STT WER',
          value: sttWer ?? 'Nicht verfügbar',
          isMissing: !sttWer,
        },
      ],
    });
  }

  return groups;
}

function buildTestsetGroup(
  testsetName: string,
  languageDirections: string[]
): CandidateTestsetGroup {
  const defaultTitles = [
    'Kundenanfrage',
    'Rechnungsfrage',
    'Vertragsänderung',
    'Terminabstimmung',
    'Beschwerde',
  ];

  return {
    id: testsetName.toLowerCase().replace(/\s+/g, '-'),
    name: testsetName,
    testCases: languageDirections.map((languageDirection, index) => ({
      id: `${testsetName}-${index + 1}`,
      title: `T${index + 1} – ${defaultTitles[index] ?? 'Beispiel-Testfall'}`,
      language: languageDirection,
      variations: [
        {
          id: `${testsetName}-${index + 1}-baseline`,
          name: 'Baseline',
          technicalStatus: 'Abgeschlossen',
          summaryValues: [
            { label: 'Status', value: 'Erfolgreich verarbeitet' },
            { label: 'Latenz', value: `${620 + index * 45} ms` },
            { label: 'Accuracy', value: `${94 - index}.0` },
          ],
          repeatMeasurements: [
            {
              id: `${testsetName}-${index + 1}-r1`,
              label: 'Wiederholung 1',
              technicalStatus: 'Abgeschlossen',
              rawValues: [
                { label: 'TTFA', value: `${610 + index * 30} ms` },
                { label: 'Turn Gap', value: `${180 + index * 8} ms` },
                { label: 'Empty Output Rate', value: '0.0 %' },
              ],
            },
            {
              id: `${testsetName}-${index + 1}-r2`,
              label: 'Wiederholung 2',
              technicalStatus: 'Abgeschlossen',
              rawValues: [
                { label: 'TTFA', value: `${640 + index * 25} ms` },
                { label: 'Turn Gap', value: `${190 + index * 10} ms` },
                { label: 'Empty Output Rate', value: '0.0 %' },
              ],
            },
          ],
        },
      ],
    })),
  };
}

function buildCandidate(
  id: string,
  name: string,
  modelName: string,
  architecture: string,
  coverageSupported: number,
  coverageRequired: number,
  overallScore: number | null,
  overallScoreNote: string | undefined,
  scores: CandidateScoreSet,
  diagnosticGroups: DiagnosticGroup[],
  testsets: { name: string; languages: string[] }[]
): CandidateResult {
  return {
    id,
    name,
    modelName,
    architecture,
    coverageSupported,
    coverageRequired,
    overallScore,
    overallScoreNote,
    scores,
    diagnosticGroups,
    testsetGroups: testsets.map(testset =>
      buildTestsetGroup(testset.name, testset.languages)
    ),
  };
}

const RUN_HISTORY_DATA: BenchmarkRun[] = [
  {
    id: 10,
    finishedAtLabel: '25.11.2026, 14:32',
    finishedAtDate: '2026-11-25T14:32:00',
    status: 'completed',
    testsets: ['Contact Center – General', 'Support – Billing'],
    languages: ['DE → EN', 'EN → ES', 'DE → TR', 'EN → FR'],
    candidates: [
      buildCandidate(
        'run-10-openai',
        'OpenAI',
        'GPT-Realtime-Translate',
        'Direct S2S',
        4,
        4,
        94.7,
        undefined,
        {
          accuracy: 95.1,
          criticalInfo: 96.3,
          latency: 92.0,
          robustness: 94.2,
          reliability: 95.8,
        },
        buildDiagnosticGroups(
          '672 ms',
          '842 ms',
          '190 ms',
          '0.8 %',
          '2.1 %',
          '0.3 %',
          '0.937',
          '4.6 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Support – Billing',
            languages: ['DE → EN', 'EN → FR'],
          },
        ]
      ),
      buildCandidate(
        'run-10-google',
        'Google',
        'Gemini Live Translate',
        'Direct S2S',
        4,
        4,
        93.2,
        undefined,
        {
          accuracy: 94.2,
          criticalInfo: 95.0,
          latency: 91.4,
          robustness: 92.6,
          reliability: 92.1,
        },
        buildDiagnosticGroups(
          '701 ms',
          '865 ms',
          '205 ms',
          '0.9 %',
          '1.6 %',
          '0.1 %',
          '0.921',
          '5.1 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Support – Billing',
            languages: ['DE → EN', 'EN → FR'],
          },
        ]
      ),
      buildCandidate(
        'run-10-microsoft',
        'Microsoft',
        'Azure Live Interpreter',
        'Direct S2S',
        3,
        4,
        null,
        'Kein Ranking-Score',
        {
          accuracy: 90.1,
          criticalInfo: 92.2,
          latency: 88.4,
          robustness: 87.9,
          reliability: 89.8,
        },
        buildDiagnosticGroups(
          '744 ms',
          '918 ms',
          '221 ms',
          '1.1 %',
          '2.4 %',
          '0.5 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Support – Billing',
            languages: ['DE → EN'],
          },
        ]
      ),
      buildCandidate(
        'run-10-meta',
        'Meta',
        'SeamlessM4T Cascade',
        'Cascaded',
        4,
        4,
        89.8,
        undefined,
        {
          accuracy: 90.1,
          criticalInfo: 92.2,
          latency: 88.4,
          robustness: 87.9,
          reliability: 89.8,
        },
        buildDiagnosticGroups(
          '790 ms',
          '962 ms',
          '245 ms',
          '1.4 %',
          '2.7 %',
          '0.5 %',
          '0.901',
          '6.4 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Support – Billing',
            languages: ['DE → EN', 'EN → FR'],
          },
        ]
      ),
    ],
  },
  {
    id: 9,
    finishedAtLabel: '24.11.2026, 11:04',
    finishedAtDate: '2026-11-24T11:04:00',
    status: 'failed',
    testsets: ['Support – Billing'],
    languages: ['DE → EN', 'EN → FR', 'DE → ES'],
    candidates: [
      buildCandidate(
        'run-09-openai',
        'OpenAI',
        'GPT-Realtime-Translate',
        'Direct S2S',
        3,
        3,
        92.8,
        undefined,
        {
          accuracy: 93.5,
          criticalInfo: 94.4,
          latency: 90.2,
          robustness: 91.8,
          reliability: 93.1,
        },
        buildDiagnosticGroups(
          '688 ms',
          '855 ms',
          '199 ms',
          '0.7 %',
          '1.8 %',
          '0.2 %'
        ),
        [
          {
            name: 'Support – Billing',
            languages: ['DE → EN', 'EN → FR', 'DE → ES'],
          },
        ]
      ),
      buildCandidate(
        'run-09-google',
        'Google',
        'Gemini Live Translate',
        'Direct S2S',
        3,
        3,
        91.9,
        undefined,
        {
          accuracy: 92.8,
          criticalInfo: 93.7,
          latency: 89.9,
          robustness: 90.8,
          reliability: 92.0,
        },
        buildDiagnosticGroups(
          '709 ms',
          '884 ms',
          '210 ms',
          '0.9 %',
          '2.2 %',
          '0.3 %'
        ),
        [
          {
            name: 'Support – Billing',
            languages: ['DE → EN', 'EN → FR', 'DE → ES'],
          },
        ]
      ),
      buildCandidate(
        'run-09-soniox',
        'Soniox',
        'Streaming Speech',
        'Integrated',
        2,
        3,
        null,
        'Kein Ranking-Score',
        {
          accuracy: null,
          criticalInfo: null,
          latency: null,
          robustness: null,
          reliability: null,
        },
        buildDiagnosticGroups(
          'Nicht verfügbar',
          'Nicht verfügbar',
          'Nicht verfügbar',
          'Nicht verfügbar',
          'Nicht verfügbar',
          'Nicht verfügbar'
        ),
        [
          {
            name: 'Support – Billing',
            languages: ['DE → EN', 'EN → FR'],
          },
        ]
      ),
    ],
  },
  {
    id: 8,
    finishedAtLabel: '23.11.2026, 16:20',
    finishedAtDate: '2026-11-23T16:20:00',
    status: 'completed',
    testsets: ['Contact Center – General'],
    languages: ['DE → EN', 'EN → ES', 'DE → TR'],
    candidates: [
      buildCandidate(
        'run-08-openai',
        'OpenAI',
        'GPT-Realtime-Translate',
        'Direct S2S',
        3,
        3,
        94.1,
        undefined,
        {
          accuracy: 94.8,
          criticalInfo: 95.6,
          latency: 91.2,
          robustness: 93.8,
          reliability: 95.0,
        },
        buildDiagnosticGroups(
          '664 ms',
          '835 ms',
          '184 ms',
          '0.6 %',
          '1.7 %',
          '0.1 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
        ]
      ),
      buildCandidate(
        'run-08-google',
        'Google',
        'Gemini Live Translate',
        'Direct S2S',
        3,
        3,
        92.7,
        undefined,
        {
          accuracy: 93.6,
          criticalInfo: 94.4,
          latency: 90.1,
          robustness: 91.6,
          reliability: 92.9,
        },
        buildDiagnosticGroups(
          '690 ms',
          '860 ms',
          '202 ms',
          '0.8 %',
          '1.9 %',
          '0.2 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
        ]
      ),
    ],
  },
  {
    id: 7,
    finishedAtLabel: '22.11.2026, 10:17',
    finishedAtDate: '2026-11-22T10:17:00',
    status: 'completed',
    testsets: ['General + Stress'],
    languages: ['EN → DE', 'DE → EN', 'EN → ES', 'DE → TR'],
    candidates: [
      buildCandidate(
        'run-07-meta',
        'Meta',
        'SeamlessM4T Cascade',
        'Cascaded',
        4,
        4,
        90.4,
        undefined,
        {
          accuracy: 91.1,
          criticalInfo: 92.0,
          latency: 88.1,
          robustness: 89.7,
          reliability: 90.2,
        },
        buildDiagnosticGroups(
          '784 ms',
          '954 ms',
          '241 ms',
          '1.3 %',
          '2.5 %',
          '0.4 %'
        ),
        [
          {
            name: 'General + Stress',
            languages: ['EN → DE', 'DE → EN', 'EN → ES', 'DE → TR'],
          },
        ]
      ),
      buildCandidate(
        'run-07-google',
        'Google',
        'Gemini Live Translate',
        'Direct S2S',
        4,
        4,
        92.4,
        undefined,
        {
          accuracy: 93.1,
          criticalInfo: 94.0,
          latency: 90.6,
          robustness: 91.5,
          reliability: 92.0,
        },
        buildDiagnosticGroups(
          '707 ms',
          '878 ms',
          '206 ms',
          '0.8 %',
          '1.7 %',
          '0.2 %'
        ),
        [
          {
            name: 'General + Stress',
            languages: ['EN → DE', 'DE → EN', 'EN → ES', 'DE → TR'],
          },
        ]
      ),
    ],
  },
  {
    id: 6,
    finishedAtLabel: '21.11.2026, 09:45',
    finishedAtDate: '2026-11-21T09:45:00',
    status: 'completed',
    testsets: ['Contact Center – General', 'Travel Support'],
    languages: ['DE → EN', 'EN → ES', 'EN → FR', 'DE → TR', 'EN → DE'],
    candidates: [
      buildCandidate(
        'run-06-google',
        'Google',
        'Gemini Live Translate',
        'Direct S2S',
        5,
        5,
        93.8,
        undefined,
        {
          accuracy: 94.1,
          criticalInfo: 94.9,
          latency: 91.8,
          robustness: 93.0,
          reliability: 93.3,
        },
        buildDiagnosticGroups(
          '698 ms',
          '870 ms',
          '201 ms',
          '0.7 %',
          '1.8 %',
          '0.2 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Travel Support',
            languages: ['EN → FR', 'EN → DE'],
          },
        ]
      ),
      buildCandidate(
        'run-06-microsoft',
        'Microsoft',
        'Azure Live Interpreter',
        'Direct S2S',
        4,
        5,
        null,
        'Kein Ranking-Score',
        {
          accuracy: 89.6,
          criticalInfo: 90.8,
          latency: 87.9,
          robustness: 86.1,
          reliability: 88.3,
        },
        buildDiagnosticGroups(
          '759 ms',
          '930 ms',
          '228 ms',
          '1.2 %',
          '2.6 %',
          '0.5 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Travel Support',
            languages: ['EN → FR'],
          },
        ]
      ),
      buildCandidate(
        'run-06-meta',
        'Meta',
        'SeamlessM4T Cascade',
        'Cascaded',
        5,
        5,
        89.5,
        undefined,
        {
          accuracy: 90.0,
          criticalInfo: 91.0,
          latency: 87.2,
          robustness: 88.8,
          reliability: 89.4,
        },
        buildDiagnosticGroups(
          '801 ms',
          '980 ms',
          '247 ms',
          '1.5 %',
          '2.8 %',
          '0.6 %'
        ),
        [
          {
            name: 'Contact Center – General',
            languages: ['DE → EN', 'EN → ES', 'DE → TR'],
          },
          {
            name: 'Travel Support',
            languages: ['EN → FR', 'EN → DE'],
          },
        ]
      ),
    ],
  },
];

@Component({
  selector: 'app-run-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './run-history.html',
  styleUrl: './run-history.scss',
})
export class RunHistory {
  @ViewChild('detailSection')
  detailSection?: ElementRef<HTMLElement>;

  readonly runs = RUN_HISTORY_DATA;
  readonly entriesPerPageOptions = [5, 10, 20];

  searchText = '';
  currentPage = 1;
  entriesPerPage = 5;

  isFilterPanelOpen = false;

  appliedFilters: AdvancedFilters = this.createDefaultFilters();
  draftFilters: AdvancedFilters = this.createDefaultFilters();

  expandedRunId: number | null = null;
  activeDetailsTab: DetailsTab = 'overview';
  selectedCandidateId: string | null = null;

  readonly filterReferenceDate = new Date('2026-11-25T23:59:59');

  createDefaultFilters(): AdvancedFilters {
    return {
      sortOrder: 'descending',
      statuses: [],
      period: 'all',
      customStart: '',
      customEnd: '',
    };
  }

  cloneFilters(filters: AdvancedFilters): AdvancedFilters {
    return {
      sortOrder: filters.sortOrder,
      statuses: [...filters.statuses],
      period: filters.period,
      customStart: filters.customStart,
      customEnd: filters.customEnd,
    };
  }

  get filteredRuns(): BenchmarkRun[] {
    const normalizedSearchText = this.searchText.trim().toLowerCase();

    let result = [...this.runs];

    if (normalizedSearchText) {
      result = result.filter(run => {
        const searchableValues = [
          this.formatRunId(run.id),
          run.finishedAtLabel,
          this.getStatusLabel(run.status),
          ...run.testsets,
          ...run.languages,
          ...run.candidates.map(candidate => candidate.name),
          ...run.candidates.map(candidate => candidate.modelName),
        ]
          .join(' ')
          .toLowerCase();

        return searchableValues.includes(normalizedSearchText);
      });
    }

    if (this.appliedFilters.statuses.length > 0) {
      result = result.filter(run =>
        this.appliedFilters.statuses.includes(run.status)
      );
    }

    result = result.filter(run => this.matchesPeriodFilter(run));

    result.sort((firstRun, secondRun) => {
      if (this.appliedFilters.sortOrder === 'descending') {
        return secondRun.id - firstRun.id;
      }

      return firstRun.id - secondRun.id;
    });

    return result;
  }

  get totalPageCount(): number {
    return Math.max(1, Math.ceil(this.filteredRuns.length / this.entriesPerPage));
  }

  get visibleRuns(): BenchmarkRun[] {
    const firstIndex = (this.currentPage - 1) * this.entriesPerPage;
    return this.filteredRuns.slice(firstIndex, firstIndex + this.entriesPerPage);
  }

  get pageNumbers(): number[] {
    return Array.from({ length: this.totalPageCount }, (_, index) => index + 1);
  }

  get selectedRun(): BenchmarkRun | null {
    if (this.expandedRunId === null) {
      return null;
    }

    return (
      this.filteredRuns.find(run => run.id === this.expandedRunId) ??
      this.runs.find(run => run.id === this.expandedRunId) ??
      null
    );
  }

  get selectedDetailsCandidate(): CandidateResult | null {
    if (!this.selectedRun || !this.selectedCandidateId) {
      return null;
    }

    return (
      this.selectedRun.candidates.find(
        candidate => candidate.id === this.selectedCandidateId
      ) ?? null
    );
  }

  updateSearch(searchText: string): void {
    this.searchText = searchText;
    this.currentPage = 1;
    this.closeRunDetails();
  }

  openFilterPanel(): void {
    this.draftFilters = this.cloneFilters(this.appliedFilters);
    this.isFilterPanelOpen = true;
  }

  closeFilterPanel(): void {
    this.isFilterPanelOpen = false;
    this.draftFilters = this.cloneFilters(this.appliedFilters);
  }

  applyFilters(): void {
    this.appliedFilters = this.cloneFilters(this.draftFilters);
    this.isFilterPanelOpen = false;
    this.currentPage = 1;
    this.closeRunDetails();
  }

  resetAllFilters(): void {
    this.searchText = '';
    this.appliedFilters = this.createDefaultFilters();
    this.draftFilters = this.createDefaultFilters();
    this.currentPage = 1;
    this.isFilterPanelOpen = false;
    this.closeRunDetails();
  }

  selectDraftSortOrder(sortOrder: SortOrder): void {
    this.draftFilters.sortOrder = sortOrder;
  }

  isDraftSortOrderSelected(sortOrder: SortOrder): boolean {
    return this.draftFilters.sortOrder === sortOrder;
  }

  toggleDraftStatus(status: RunStatus): void {
    if (this.draftFilters.statuses.includes(status)) {
      this.draftFilters.statuses = this.draftFilters.statuses.filter(
        selectedStatus => selectedStatus !== status
      );
      return;
    }

    this.draftFilters.statuses = [...this.draftFilters.statuses, status];
  }

  isDraftStatusSelected(status: RunStatus): boolean {
    return this.draftFilters.statuses.includes(status);
  }

  selectDraftPeriod(period: PeriodOption): void {
    this.draftFilters.period = period;

    if (period !== 'custom') {
      this.draftFilters.customStart = '';
      this.draftFilters.customEnd = '';
    }
  }

  isDraftPeriodSelected(period: PeriodOption): boolean {
    return this.draftFilters.period === period;
  }

  matchesPeriodFilter(run: BenchmarkRun): boolean {
    const runDate = new Date(run.finishedAtDate);

    if (this.appliedFilters.period === 'all') {
      return true;
    }

    if (this.appliedFilters.period === '7-days') {
      const sevenDaysAgo = new Date(this.filterReferenceDate);
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      return runDate >= sevenDaysAgo && runDate <= this.filterReferenceDate;
    }

    if (this.appliedFilters.period === '30-days') {
      const thirtyDaysAgo = new Date(this.filterReferenceDate);
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      return runDate >= thirtyDaysAgo && runDate <= this.filterReferenceDate;
    }

    if (
      this.appliedFilters.period === 'custom' &&
      this.appliedFilters.customStart &&
      this.appliedFilters.customEnd
    ) {
      const startDate = new Date(`${this.appliedFilters.customStart}T00:00:00`);
      const endDate = new Date(`${this.appliedFilters.customEnd}T23:59:59`);

      return runDate >= startDate && runDate <= endDate;
    }

    return true;
  }

  toggleRunDetails(runId: number): void {
    if (this.expandedRunId === runId) {
      this.closeRunDetails();
      return;
    }

    this.expandedRunId = runId;
    this.activeDetailsTab = 'overview';

    const selectedRun = this.runs.find(run => run.id === runId);
    this.selectedCandidateId = selectedRun?.candidates[0]?.id ?? null;

    setTimeout(() => {
      this.detailSection?.nativeElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  }

  closeRunDetails(): void {
    this.expandedRunId = null;
    this.selectedCandidateId = null;
  }

  selectDetailsTab(tab: DetailsTab): void {
    this.activeDetailsTab = tab;
  }

  selectCandidate(candidateId: string): void {
    this.selectedCandidateId = candidateId;
  }

  isCandidateSelected(candidateId: string): boolean {
    return this.selectedCandidateId === candidateId;
  }

  selectPage(pageNumber: number): void {
    if (pageNumber < 1 || pageNumber > this.totalPageCount) {
      return;
    }

    this.currentPage = pageNumber;
    this.closeRunDetails();
  }

  goToPreviousPage(): void {
    this.selectPage(this.currentPage - 1);
  }

  goToNextPage(): void {
    this.selectPage(this.currentPage + 1);
  }

  updateEntriesPerPage(entriesPerPageValue: string): void {
    this.entriesPerPage = Number(entriesPerPageValue);
    this.currentPage = 1;
    this.closeRunDetails();
  }

  formatRunId(runId: number): string {
    return `#${runId.toString().padStart(4, '0')}`;
  }

  getStatusLabel(status: RunStatus): string {
    return status === 'completed' ? 'Abgeschlossen' : 'Fehlgeschlagen';
  }

  getStatusClass(status: RunStatus): string {
    return status === 'completed' ? 'status-pill-completed' : 'status-pill-failed';
  }

  getStatusIconPath(status: RunStatus): string {
    if (status === 'completed') {
      return 'M12 2.75a9.25 9.25 0 1 0 0 18.5a9.25 9.25 0 0 0 0-18.5Zm4.21 6.96-4.84 5.08a.75.75 0 0 1-1.08.02l-2.52-2.45a.75.75 0 0 1 1.05-1.08l1.98 1.92l4.31-4.52a.75.75 0 0 1 1.1 1.03Z';
    }

    return 'M12 2.75a9.25 9.25 0 1 0 0 18.5a9.25 9.25 0 0 0 0-18.5Zm-3.22 5.97a.75.75 0 0 1 1.06 0L12 10.88l2.16-2.16a.75.75 0 1 1 1.06 1.06L13.06 12l2.16 2.16a.75.75 0 1 1-1.06 1.06L12 13.06l-2.16 2.16a.75.75 0 1 1-1.06-1.06L10.94 12L8.78 9.78a.75.75 0 0 1 0-1.06Z';
  }

  getVisibleTestsets(testsets: string[]): string[] {
    return testsets.slice(0, 1);
  }

  getHiddenTestsets(testsets: string[]): string[] {
    return testsets.slice(1);
  }

  getVisibleLanguages(languages: string[]): string[] {
    return languages.slice(0, 2);
  }

  getHiddenLanguages(languages: string[]): string[] {
    return languages.slice(2);
  }

  getVisibleCandidateNames(run: BenchmarkRun): string[] {
    return run.candidates.map(candidate => candidate.name).slice(0, 2);
  }

  getHiddenCandidateNames(run: BenchmarkRun): string[] {
    return run.candidates.map(candidate => candidate.name).slice(2);
  }

  getCoverageLabel(candidate: CandidateResult): string {
    return `${candidate.coverageSupported}/${candidate.coverageRequired}`;
  }

  getMetricValue(value: number | null): string {
    return value === null ? '–' : value.toFixed(1);
  }

  trackRunById(_: number, run: BenchmarkRun): number {
    return run.id;
  }

  trackCandidateById(_: number, candidate: CandidateResult): string {
    return candidate.id;
  }

  trackPageByNumber(_: number, pageNumber: number): number {
    return pageNumber;
  }
}