
import { Component } from '@angular/core';

type CandidateView = 'carousel' | 'grid';

type BenchmarkCandidate = {
  id: string;
  providerName: string;
  modelName: string;
  architecture: 'Direct S2S' | 'Integrated' | 'Cascaded';
  symbol: string;
};

type BenchmarkTestset = {
  id: string;
  name: string;
  languageDirections: string[];
};

@Component({
  selector: 'app-runs',
  templateUrl: './runs.html',
  styleUrl: './runs.scss',
})
export class Runs {
  readonly availableCandidates: BenchmarkCandidate[] = [
    {
      id: 'openai',
      providerName: 'OpenAI',
      modelName: 'GPT-Realtime-Translate',
      architecture: 'Direct S2S',
      symbol: 'O',
    },
    {
      id: 'google',
      providerName: 'Google',
      modelName: 'Gemini Live Translate',
      architecture: 'Direct S2S',
      symbol: 'G',
    },
    {
      id: 'deepl',
      providerName: 'DeepL',
      modelName: 'Voice API',
      architecture: 'Integrated',
      symbol: 'D',
    },
    {
      id: 'microsoft',
      providerName: 'Microsoft',
      modelName: 'Azure Live Interpreter',
      architecture: 'Direct S2S',
      symbol: 'M',
    },
    {
      id: 'soniox',
      providerName: 'Soniox',
      modelName: 'Streaming Speech',
      architecture: 'Integrated',
      symbol: 'S',
    },
    {
      id: 'meta',
      providerName: 'Meta',
      modelName: 'SeamlessM4T',
      architecture: 'Cascaded',
      symbol: 'Me',
    },
    {
      id: 'elevenlabs',
      providerName: 'ElevenLabs',
      modelName: 'Conversational AI',
      architecture: 'Cascaded',
      symbol: '11',
    },
    {
      id: 'amazon',
      providerName: 'Amazon',
      modelName: 'Translate Voice Stack',
      architecture: 'Integrated',
      symbol: 'A',
    },
    {
      id: 'test-09',
      providerName: 'Test Candidate 09',
      modelName: 'Placeholder',
      architecture: 'Direct S2S',
      symbol: '09',
    },
    {
      id: 'test-10',
      providerName: 'Test Candidate 10',
      modelName: 'Placeholder',
      architecture: 'Integrated',
      symbol: '10',
    },
    {
      id: 'test-11',
      providerName: 'Test Candidate 11',
      modelName: 'Placeholder',
      architecture: 'Cascaded',
      symbol: '11',
    },
    {
      id: 'test-12',
      providerName: 'Test Candidate 12',
      modelName: 'Placeholder',
      architecture: 'Direct S2S',
      symbol: '12',
    },
    {
      id: 'test-13',
      providerName: 'Test Candidate 13',
      modelName: 'Placeholder',
      architecture: 'Integrated',
      symbol: '13',
    },
    {
      id: 'test-14',
      providerName: 'Test Candidate 14',
      modelName: 'Placeholder',
      architecture: 'Direct S2S',
      symbol: '14',
    },
    {
      id: 'test-15',
      providerName: 'Test Candidate 15',
      modelName: 'Placeholder',
      architecture: 'Cascaded',
      symbol: '15',
    },
    {
      id: 'test-16',
      providerName: 'Test Candidate 16',
      modelName: 'Placeholder',
      architecture: 'Integrated',
      symbol: '16',
    },
  ];

  readonly availableTestsets: BenchmarkTestset[] = [
    {
      id: 'general',
      name: 'Contact Center – General',
      languageDirections: ['DE → EN', 'EN → ES', 'DE → TR'],
    },
    {
      id: 'billing',
      name: 'Support – Billing',
      languageDirections: ['DE → EN', 'EN → FR'],
    },
  ];

  candidateSearchText = '';
  selectedArchitecture = 'Alle';
  readonly availableArchitectureTypes = [
    'Alle',
    'Direct S2S',
    'Integrated',
    'Cascaded'
  ] as const;
  selectedCandidateIds: string[] = ['openai', 'google', 'microsoft'];

  // links: karussell, rechts kachel
  candidateView: CandidateView = 'carousel';

  readonly carouselVisibleCount = 4;
  carouselStartIndex = 0;

  readonly gridCandidatesPerPage = 12;
  currentGridPage = 1;

  selectedTestsetId = 'general';

  get selectedTestsetName(): string {
  const selectedTestset = this.availableTestsets.find(
    testset => testset.id === this.selectedTestsetId
  );

  return selectedTestset?.name ?? 'Testset auswählen';
}

  get filteredCandidates(): BenchmarkCandidate[] {
    const searchText = this.candidateSearchText.trim().toLowerCase();

    return this.availableCandidates.filter(candidate => {
      const candidateName =
        `${candidate.providerName} ${candidate.modelName}`.toLowerCase();

      const matchesSearch = candidateName.includes(searchText);

      const matchesArchitecture =
        this.selectedArchitecture === 'Alle' ||
        candidate.architecture === this.selectedArchitecture;

      return matchesSearch && matchesArchitecture;
    });
  }

  get visibleCandidates(): BenchmarkCandidate[] {
    if (this.candidateView === 'carousel') {
      return this.filteredCandidates.slice(
        this.carouselStartIndex,
        this.carouselStartIndex + this.carouselVisibleCount
      );
    }

    const firstCandidateIndex =
      (this.currentGridPage - 1) * this.gridCandidatesPerPage;

    return this.filteredCandidates.slice(
      firstCandidateIndex,
      firstCandidateIndex + this.gridCandidatesPerPage
    );
  }

  get gridPageCount(): number {
    return Math.max(
      1,
      Math.ceil(this.filteredCandidates.length / this.gridCandidatesPerPage)
    );
  }

  get canMoveCarouselBack(): boolean {
    return this.carouselStartIndex > 0;
  }

  get canMoveCarouselForward(): boolean {
    return (
      this.carouselStartIndex + this.carouselVisibleCount <
      this.filteredCandidates.length
    );
  }

  get selectedLanguageDirections(): string[] {
    const selectedTestset = this.availableTestsets.find(
      testset => testset.id === this.selectedTestsetId
    );

    return selectedTestset?.languageDirections ?? [];
  }

  updateCandidateSearch(searchText: string): void {
    this.candidateSearchText = searchText;
    this.resetCandidateNavigation();
  }

  updateArchitectureFilter(architecture: string): void {
    this.selectedArchitecture = architecture;
    this.resetCandidateNavigation();
  }

  changeCandidateView(selectedView: CandidateView): void {
    this.candidateView = selectedView;
    this.resetCandidateNavigation();
  }

  resetCandidateNavigation(): void {
    this.carouselStartIndex = 0;
    this.currentGridPage = 1;
  }

  moveCarousel(direction: -1 | 1): void {
    const lastPossibleStartIndex = Math.max(
      0,
      this.filteredCandidates.length - this.carouselVisibleCount
    );

    const nextStartIndex = this.carouselStartIndex + direction;

    this.carouselStartIndex = Math.max(
      0,
      Math.min(nextStartIndex, lastPossibleStartIndex)
    );
  }

  changeGridPage(direction: -1 | 1): void {
    const nextPage = this.currentGridPage + direction;

    this.currentGridPage = Math.max(
      1,
      Math.min(nextPage, this.gridPageCount)
    );
  }

  isCandidateSelected(candidateId: string): boolean {
    return this.selectedCandidateIds.includes(candidateId);
  }

  toggleCandidateSelection(candidateId: string): void {
    if (this.isCandidateSelected(candidateId)) {
      this.selectedCandidateIds = this.selectedCandidateIds.filter(
        selectedId => selectedId !== candidateId
      );
    } else {
      this.selectedCandidateIds = [
        ...this.selectedCandidateIds,
        candidateId,
      ];
    }
  }

  selectAllFilteredCandidates(): void {
    const filteredCandidateIds = this.filteredCandidates.map(
      candidate => candidate.id
    );

    this.selectedCandidateIds = [
      ...new Set([
        ...this.selectedCandidateIds,
        ...filteredCandidateIds,
      ]),
    ];
  }

  clearCandidateSelection(): void {
    this.selectedCandidateIds = [];
  }
}
