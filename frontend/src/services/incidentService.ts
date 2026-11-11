export type IncidentAnalysisResponse = {
  incident_id: string;
  service: string;
  severity: string;
  title: string;
  candidate_root_cause: string;
  confidence: number | null;
  confidence_basis?: string;
  summary: string;
  evidence_documents: Array<{
    document_id: string;
    title: string;
    service: string;
    document_type: string;
    score: number;
    content: string;
    tags: string[];
  }>;
  tool_findings?: {
    deployment: {
      service: string;
      deployment_id: string | null;
      configuration_changes: Record<string, unknown>;
      risky_settings: string[];
    };
    logs: {
      service: string;
      error_count: number;
      error_types: string[];
      sample_messages: string[];
      latest_error: string | null;
    };
    metrics: {
      service: string;
      latency_p95_avg: number;
      db_connection_usage_peak: number;
      db_connection_usage_avg: number;
      error_rate_avg: number;
    };
  };
  recommendation?: {
    requires_human_approval: boolean;
    approval_status: string;
    recommended_action: string;
    approval_note: string;
  };
  timeline?: Array<{
    event: string;
    details: string;
  }>;
  graph_path?: string[];
  llm?: {
    mode: 'llm' | 'deterministic_fallback';
    provider: string | null;
    model: string | null;
    reason: string | null;
  };
};

export type IncidentApprovalResponse = {
  incident_id: string;
  approval_status: string;
  decision: string;
  message: string;
};

export type IncidentApprovalHistoryEntry = {
  incident_id: string;
  service: string;
  decision: string;
  status: string;
  recommended_action: string;
  approval_note: string;
  created_at: string;
  updated_at: string;
};

export type IncidentCatalogEntry = {
  incident_id: string;
  title: string;
  service: string;
  severity: string;
};

export type IncidentDetail = {
  incident_id: string;
  title: string;
  description: string;
  service: string;
  severity: string;
  timestamp: string;
  symptoms: string[];
  deployment: {
    deployment_id: string;
    service: string;
    version: string;
    environment: string;
    configuration_changes: Record<string, unknown>;
  };
};

const CANDIDATE_API_BASE_URLS = [
  import.meta.env.VITE_API_BASE_URL,
  'http://localhost:8000',
  'http://localhost:8001',
  'http://localhost:8012',
  'http://127.0.0.1:8000',
  'http://127.0.0.1:8001',
  'http://127.0.0.1:8012',
].filter((value, index, array) => !!value && array.indexOf(value) === index).map((value) => value!.replace(/\/$/, ''));

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let lastError: Error | null = null;

  for (const candidate of CANDIDATE_API_BASE_URLS) {
    try {
      const response = await fetch(`${candidate}${path}`, init);
      if (!response.ok) {
        const errorText = await response.text();
        lastError = new Error(errorText || `Request failed for ${path} with status ${response.status}`);
        continue;
      }

      return (await response.json()) as T;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
    }
  }

  throw lastError ?? new Error('API request failed.');
}

export async function fetchIncidentCatalog(): Promise<IncidentCatalogEntry[]> {
  return requestJson<IncidentCatalogEntry[]>('/api/v1/investigations/incidents');
}

export async function fetchIncidentDetail(incidentId: string): Promise<IncidentDetail> {
  return requestJson<IncidentDetail>(`/api/v1/investigations/${encodeURIComponent(incidentId)}`);
}

export async function analyzeIncident(incidentId: string): Promise<IncidentAnalysisResponse> {
  return requestJson<IncidentAnalysisResponse>('/api/v1/investigations/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ incident_id: incidentId }),
  });
}

export async function getIncidentHistory(incidentId: string): Promise<IncidentApprovalHistoryEntry[]> {
  return requestJson<IncidentApprovalHistoryEntry[]>(`/api/v1/investigations/history/${encodeURIComponent(incidentId)}`);
}

export async function approveIncident(
  incidentId: string,
  decision: 'approve' | 'reject',
): Promise<IncidentApprovalResponse> {
  return requestJson<IncidentApprovalResponse>('/api/v1/investigations/approve', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ incident_id: incidentId, decision }),
  });
}
