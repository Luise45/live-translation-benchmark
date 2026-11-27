import type {
  ArchitectureType,
  BenchmarkRun,
  CandidateExecutionStatus,
  CandidateResult,
  CandidateTestsetResult,
  CoreScores,
  DiagnosticGroup,
  MetricResult,
  RunStatus,
  RunTestset,
  TestMeasurement,
} from '../models/run-history.model';

// Illustrative Beispieldaten, keine echten Benchmark-Messungen.
const availableTestsets: Record<string, RunTestset> = {
  general: {
    id: 'general',
    name: 'Contact Center – General',
    languageDirections: ['DE → EN', 'EN → ES', 'DE → TR'],
  },
  billing: {
    id: 'billing',
    name: 'Support – Billing',
    languageDirections: ['DE → EN', 'EN → FR'],
  },
  stress: {
    id: 'stress',
    name: 'General + Stress',
    languageDirections: ['EN → DE', 'DE → EN', 'EN → ES', 'FR → DE'],
  },
  claims: {
    id: 'claims',
    name: 'Service – Claims',
    languageDirections: ['DE → TR'],
  },
};

type CandidateExample = {
  id: string;
  name: string;
  modelName: string;
  architecture: ArchitectureType;
  scores: [number, number, number, number, number];
  overallScore: number;
  typicalTtfaMilliseconds: number;
};

const candidateExamples: Record<string, CandidateExample> = {
  openai: {
    id: 'openai',
    name: 'OpenAI',
    modelName: 'GPT-Realtime-Translate',
    architecture: 'Direct S2S',
    scores: [95.1, 96.3, 92.0, 94.2, 95.8],
    overallScore: 94.7,
    typicalTtfaMilliseconds: 672,
  },
  google: {
    id: 'google',
    name: 'Google',
    modelName: 'Gemini Live Translate',
    architecture: 'Direct S2S',
    scores: [94.2, 95.0, 91.4, 92.6, 92.1],
    overallScore: 93.2,
    typicalTtfaMilliseconds: 740,
  },
  microsoft: {
    id: 'microsoft',
    name: 'Microsoft',
    modelName: 'Azure Live Interpreter',
    architecture: 'Integrated',
    scores: [90.1, 92.2, 88.4, 87.9, 89.8],
    overallScore: 89.8,
    typicalTtfaMilliseconds: 810,
  },
  deepl: {
    id: 'deepl',
    name: 'DeepL',
    modelName: 'Voice API',
    architecture: 'Integrated',
    scores: [91.0, 89.2, 80.0, 86.2, 93.8],
    overallScore: 88.1,
    typicalTtfaMilliseconds: 920,
  },
  meta: {
    id: 'meta',
    name: 'Meta',
    modelName: 'SeamlessM4T Cascade',
    architecture: 'Cascaded',
    scores: [90.1, 92.2, 88.4, 87.9, 89.8],
    overallScore: 89.8,
    typicalTtfaMilliseconds: 1040,
  },
};

const testCaseNames: Record<string, string[]> = {
  general: [
    'Kundenanfrage',
    'Vertragsänderung',
    'Reklamation',
  ],
  billing: [
    'Rechnungskorrektur',
    'Zahlungsrückfrage',
  ],
  stress: [
    'Gesprächsübergabe',
    'Adressänderung',
    'Kundenanliegen',
    'Rückfrage',
  ],
  claims: [
    'Schadensmeldung',
  ],
};

function valid(value: number): MetricResult {
  return {
    value,
    status: 'VALID',
  };
}

function unavailable(status: MetricResult['status']): MetricResult {
  return {
    value: null,
    status,
  };
}

function createCoreScores(
  example: CandidateExample,
  executionStatus: CandidateExecutionStatus,
): CoreScores {
  const [
    accuracy,
    criticalInformation,
    latency,
    robustness,
    reliability,
  ] = example.scores;

  const result = (value: number): MetricResult =>
    executionStatus === 'completed'
      ? valid(value)
      : unavailable('FAILED');

  return {
    translationAccuracy: result(accuracy),
    criticalInformation: result(criticalInformation),
    conversationalLatency: result(latency),
    robustness: result(robustness),
    reliability: result(reliability),
  };
}

function createDiagnostics(
  example: CandidateExample,
): DiagnosticGroup[] {
  const groups: DiagnosticGroup[] = [
    {
      title: 'End-to-End-Latenz',
      diagnostics: [
        {
          label: 'TTFA Median',
          result: valid(example.typicalTtfaMilliseconds),
          unit: 'ms',
        },
        {
          label: 'TTFA P95',
          result: valid(example.typicalTtfaMilliseconds + 170),
          unit: 'ms',
        },
        {
          label: 'Turn Gap',
          result: valid(190),
          unit: 'ms',
        },
      ],
    },
    {
      title: 'Zuverlässigkeit',
      diagnostics: [
        {
          label: 'Timeout-Rate',
          result: valid(0.8),
          unit: '%',
        },
        {
          label: 'Retry-Rate',
          result: valid(2.1),
          unit: '%',
        },
        {
          label: 'Leere Audioausgabe',
          result: valid(0.3),
          unit: '%',
        },
      ],
    },
  ];

  if (example.architecture === 'Integrated') {
    groups.push({
      title: 'Interne Verarbeitung',
      diagnostics: [
        {
          label: 'Interne Stage-Latenz',
          result: unavailable('NOT_PROVIDED'),
          unit: 'ms',
        },
      ],
    });
  }

  if (example.architecture === 'Cascaded') {
    groups.push({
      title: 'STT- und MT-Diagnostics',
      diagnostics: [
        {
          label: 'STT WER',
          result: valid(4.6),
          unit: '%',
        },
        {
          label: 'MT chrF++',
          result: valid(74.3),
          unit: 'Punkte',
        },
      ],
    });

    groups.push({
      title: 'Stage-Latenzen',
      diagnostics: [
        {
          label: 'STT',
          result: valid(210),
          unit: 'ms',
        },
        {
          label: 'MT',
          result: valid(95),
          unit: 'ms',
        },
        {
          label: 'TTS',
          result: valid(310),
          unit: 'ms',
        },
      ],
    });
  }

  return groups;
}

function createMeasurements(
  candidate: CandidateExample,
  isStressCondition: boolean,
): TestMeasurement[] {
  const stressDelay = isStressCondition ? 120 : 0;

  return [0, 1, 2, 3, 4].map(index => {
    const failed =
      isStressCondition &&
      candidate.id === 'google' &&
      index === 3;

    return {
      id: String(index + 1),
      status: failed ? 'failed' : 'valid',
      ttfaMilliseconds: failed
        ? null
        : candidate.typicalTtfaMilliseconds +
          stressDelay +
          index * 18,
      errorReason: failed ? 'Provider-Timeout' : null,
    };
  });
}

function createCandidateTestsets(
  example: CandidateExample,
  runTestsets: RunTestset[],
  unsupportedDirections: string[],
): CandidateTestsetResult[] {
  return runTestsets.map(testset => ({
    id: testset.id,
    name: testset.name,

    testCases: testset.languageDirections.map(
      (languageDirection, index) => {
        const isUnsupported =
          unsupportedDirections.includes(languageDirection);

        const makeMeasurements = (
          isStress: boolean,
        ): TestMeasurement[] =>
          isUnsupported
            ? [
                {
                  id: '1',
                  status: 'unsupported',
                  ttfaMilliseconds: null,
                  errorReason: null,
                },
              ]
            : createMeasurements(example, isStress);

        return {
          id: `T${index + 1}`,
          title:
            testCaseNames[testset.id]?.[index] ??
            'Weiterer Testfall',
          languageDirection,
          conditions: [
            {
              id: 'baseline',
              name: 'Baseline',
              isBaseline: true,
              measurements: makeMeasurements(false),
            },
            {
              id: 'background-noise',
              name: 'Hintergrundgeräusche',
              isBaseline: false,
              measurements: makeMeasurements(true),
            },
          ],
        };
      },
    ),
  }));
}

function createCandidate(
  candidateId: string,
  runTestsets: RunTestset[],
  executionStatus: CandidateExecutionStatus = 'completed',
  unsupportedDirections: string[] = [],
): CandidateResult {
  const example = candidateExamples[candidateId];

  const requiredDirections = [
    ...new Set(
      runTestsets.flatMap(
        testset => testset.languageDirections,
      ),
    ),
  ];

  const unsupportedRequired = requiredDirections.filter(
    direction => unsupportedDirections.includes(direction),
  );

  const hasFullCoverage =
    unsupportedRequired.length === 0;

  const rankingEligible =
    executionStatus === 'completed' && hasFullCoverage;

  const rankingReason =
    executionStatus !== 'completed'
      ? 'Candidate-Ausführung nicht erfolgreich abgeschlossen'
      : !hasFullCoverage
        ? 'Nicht alle erforderlichen Sprachrichtungen unterstützt'
        : null;

  return {
    id: example.id,
    name: example.name,
    modelName: example.modelName,
    architecture: example.architecture,
    executionStatus,

    coverageSupported:
      requiredDirections.length - unsupportedRequired.length,
    coverageRequired: requiredDirections.length,
    unsupportedDirections: unsupportedRequired,

    rankingEligible,
    rankingReason,
    overallScore: rankingEligible
      ? example.overallScore
      : null,
    coreScores: createCoreScores(
      example,
      executionStatus,
    ),

    diagnosticGroups:
      executionStatus === 'completed'
        ? createDiagnostics(example)
        : [],

    testsets:
      executionStatus === 'completed'
        ? createCandidateTestsets(
            example,
            runTestsets,
            unsupportedRequired,
          )
        : [],
  };
}

function createRun(
  id: number,
  finishedAt: string,
  status: RunStatus,
  testsetIds: string[],
  candidateIds: string[],
  failedCandidateId: string | null = null,
  partialCandidateId: string | null = null,
): BenchmarkRun {
  const testsets = testsetIds.map(
    testsetId => availableTestsets[testsetId],
  );

  const requiredDirections = [
    ...new Set(
      testsets.flatMap(
        testset => testset.languageDirections,
      ),
    ),
  ];

  return {
    id,
    finishedAt,
    status,
    testsets,

    candidates: candidateIds.map(candidateId => {
      const executionStatus: CandidateExecutionStatus =
        candidateId === failedCandidateId
          ? 'failed'
          : 'completed';

      const unsupportedDirections =
        candidateId === partialCandidateId
          ? requiredDirections.slice(-1)
          : [];

      return createCandidate(
        candidateId,
        testsets,
        executionStatus,
        unsupportedDirections,
      );
    }),
  };
}

export const mockRunHistory: BenchmarkRun[] = [
  createRun(
    10,
    '2026-11-25T14:32:00',
    'completed',
    ['general', 'billing'],
    ['openai', 'google', 'microsoft', 'meta'],
    null,
    'microsoft',
  ),
  createRun(
    9,
    '2026-11-24T11:04:00',
    'failed',
    ['billing'],
    ['openai', 'google', 'deepl'],
    'deepl',
  ),
  createRun(
    8,
    '2026-11-23T16:20:00',
    'completed',
    ['general'],
    ['openai', 'google'],
  ),
  createRun(
    7,
    '2026-11-22T10:17:00',
    'failed',
    ['stress'],
    ['meta', 'google'],
    'meta',
  ),
  createRun(
    6,
    '2026-11-21T09:45:00',
    'completed',
    ['general', 'stress'],
    ['google', 'microsoft', 'meta'],
  ),
  createRun(
    5,
    '2026-11-18T14:12:00',
    'completed',
    ['claims'],
    ['openai'],
  ),
  createRun(
    4,
    '2026-11-16T13:30:00',
    'completed',
    ['general', 'billing', 'claims'],
    ['deepl', 'meta', 'google'],
  ),
  createRun(
    3,
    '2026-11-11T16:20:00',
    'failed',
    ['general'],
    ['microsoft', 'google'],
    'microsoft',
  ),
  createRun(
    2,
    '2026-10-28T10:17:00',
    'completed',
    ['stress'],
    ['openai', 'meta'],
  ),
  createRun(
    1,
    '2026-10-12T09:45:00',
    'completed',
    ['general'],
    ['google', 'openai'],
  ),
];