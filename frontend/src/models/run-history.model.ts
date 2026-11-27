export type RunStatus = 'completed' | 'failed';

export type CandidateExecutionStatus = 'completed' | 'failed';

export type MeasurementStatus = 'valid' | 'failed' | 'unsupported';

export type MetricStatus =
  | 'VALID'
  | 'N/A'
  | 'NOT_PROVIDED'
  | 'MISSING'
  | 'FAILED'
  | 'UNSUPPORTED'
  | 'INSUFFICIENT_DATA'
  | 'BENCHMARK_ERROR';

export type ArchitectureType = 'Direct S2S' | 'Integrated' | 'Cascaded';

export interface MetricResult {
  value: number | null;
  status: MetricStatus;
}

export interface CoreScores {
  translationAccuracy: MetricResult;
  criticalInformation: MetricResult;
  conversationalLatency: MetricResult;
  robustness: MetricResult;
  reliability: MetricResult;
}

export interface Diagnostic {
  label: string;
  result: MetricResult;
  unit: string;
}

export interface DiagnosticGroup {
  title: string;
  diagnostics: Diagnostic[];
}

export interface TestMeasurement {
  id: string;
  status: MeasurementStatus;
  ttfaMilliseconds: number | null;
  errorReason: string | null;
}

export interface TestCondition {
  id: string;
  name: string;
  isBaseline: boolean;
  measurements: TestMeasurement[];
}

export interface TestCaseResult {
  id: string;
  title: string;
  languageDirection: string;
  conditions: TestCondition[];
}

export interface CandidateTestsetResult {
  id: string;
  name: string;
  testCases: TestCaseResult[];
}

export interface RunTestset {
  id: string;
  name: string;
  languageDirections: string[];
}

export interface CandidateResult {
  id: string;
  name: string;
  modelName: string;
  architecture: ArchitectureType;
  executionStatus: CandidateExecutionStatus;

  coverageSupported: number;
  coverageRequired: number;
  unsupportedDirections: string[];

  rankingEligible: boolean;
  rankingReason: string | null;
  overallScore: number | null;
  coreScores: CoreScores;

  diagnosticGroups: DiagnosticGroup[];
  testsets: CandidateTestsetResult[];
}

export interface BenchmarkRun {
  id: number;
  finishedAt: string;
  status: RunStatus;
  testsets: RunTestset[];
  candidates: CandidateResult[];
}

export type RunPeriod = 'all' | '7-days' | '30-days' | 'custom';

export type RunSortOrder = 'descending' | 'ascending';

export interface RunFilters {
  sortOrder: RunSortOrder;
  period: RunPeriod;
  startDate: string;
  endDate: string;
  statuses: RunStatus[];
}