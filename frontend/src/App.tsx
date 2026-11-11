import { useEffect, useState } from 'react';
import {
  analyzeIncident,
  approveIncident,
  fetchIncidentCatalog,
  fetchIncidentDetail,
  getIncidentHistory,
  type IncidentAnalysisResponse,
  type IncidentApprovalHistoryEntry,
  type IncidentCatalogEntry,
  type IncidentDetail,
} from './services/incidentService';

export default function App() {
  const [incidentId, setIncidentId] = useState('INC-001');
  const [incidentQuery, setIncidentQuery] = useState('');
  const [availableIncidents, setAvailableIncidents] = useState<IncidentCatalogEntry[]>([]);
  const [incidentDetail, setIncidentDetail] = useState<IncidentDetail | null>(null);
  const [result, setResult] = useState<IncidentAnalysisResponse | null>(null);
  const [history, setHistory] = useState<IncidentApprovalHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalState, setApprovalState] = useState<string>('pending');

  const filteredIncidents = availableIncidents.filter((incident) => {
    const search = incidentQuery.trim().toLowerCase();
    if (!search) {
      return true;
    }

    const haystack = `${incident.incident_id} ${incident.title} ${incident.service} ${incident.severity}`.toLowerCase();
    return haystack.includes(search);
  });
  const selectedIncident = availableIncidents.find((incident) => incident.incident_id === incidentId);
  const selectedIncidentIsFilteredOut =
    selectedIncident !== undefined &&
    !filteredIncidents.some((incident) => incident.incident_id === selectedIncident.incident_id);

  useEffect(() => {
    const loadCatalog = async () => {
      try {
        const catalog = await fetchIncidentCatalog();
        setAvailableIncidents(catalog);
        if (catalog.length > 0 && !catalog.some((incident) => incident.incident_id === incidentId)) {
          setIncidentId(catalog[0].incident_id);
        }
      } catch (err) {
        console.warn('Unable to load incident catalog', err);
      }
    };

    void loadCatalog();
  }, []);

  useEffect(() => {
    if (availableIncidents.length > 0 && !availableIncidents.some((incident) => incident.incident_id === incidentId)) {
      setIncidentId(availableIncidents[0].incident_id);
    }
  }, [availableIncidents, incidentId]);

  useEffect(() => {
    let active = true;

    const loadDetail = async () => {
      if (!incidentId) {
        setIncidentDetail(null);
        return;
      }

      setIncidentDetail(null);
      try {
        const detail = await fetchIncidentDetail(incidentId);
        if (active) {
          setIncidentDetail(detail);
        }
      } catch (err) {
        if (active) {
          console.warn('Unable to load incident detail', err);
        }
      }
    };

    void loadDetail();
    return () => {
      active = false;
    };
  }, [incidentId]);

  const loadHistory = async (targetIncidentId: string) => {
    try {
      const nextHistory = await getIncidentHistory(targetIncidentId);
      setHistory(nextHistory);
    } catch (err) {
      console.warn('Unable to load incident history', err);
      setHistory([]);
    }
  };

  const handleInvestigate = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await analyzeIncident(incidentId);
      setResult(response);
      setApprovalState(response.recommendation?.approval_status ?? 'pending');
      await loadHistory(response.incident_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to analyze incident.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async (decision: 'approve' | 'reject') => {
    if (!result) {
      return;
    }

    try {
      const body = await approveIncident(result.incident_id, decision);
      setApprovalState(body.approval_status);
      await loadHistory(result.incident_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update approval state.');
    }
  };

  const handleResetResult = () => {
    setResult(null);
    setHistory([]);
    setError(null);
    setApprovalState('pending');
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI Incident Investigation</p>
          <h1>AEGIS</h1>
        </div>
        <span className="status-pill">Workflow online</span>
      </header>

      <section className="panel panel-primary">
        <h2>Incident analysis</h2>
        <div className="selector-stack">
          <label className="input-label" htmlFor="incident-filter">
            Search incidents
          </label>
          <input
            id="incident-filter"
            type="text"
            value={incidentQuery}
            placeholder="Filter by ID, service, or severity"
            onChange={(event) => setIncidentQuery(event.target.value)}
          />
        </div>

        <label className="input-label" htmlFor="incident-id">
          Incident ID
        </label>
        <select
          id="incident-id"
          value={incidentId}
          onChange={(event) => {
            setIncidentId(event.target.value);
            setResult(null);
            setHistory([]);
            setError(null);
            setApprovalState('pending');
          }}
          aria-label="Incident ID"
        >
          {selectedIncidentIsFilteredOut ? (
            <option value={selectedIncident.incident_id}>
              {selectedIncident.incident_id} — {selectedIncident.service} (current selection)
            </option>
          ) : null}
          {filteredIncidents.length === 0 && !selectedIncident ? (
            <option value={incidentId}>{incidentId}</option>
          ) : null}
          {filteredIncidents.map((incident) => (
            <option key={incident.incident_id} value={incident.incident_id}>
              {incident.incident_id} — {incident.service}
            </option>
          ))}
        </select>
        <div className="filter-actions">
          <p className="filter-summary">
            {filteredIncidents.length} matching {filteredIncidents.length === 1 ? 'incident' : 'incidents'}
          </p>
          {incidentQuery ? (
            <button type="button" className="ghost-button" onClick={() => setIncidentQuery('')}>
              Clear search
            </button>
          ) : null}
        </div>
        <div className="action-row">
          <button type="button" onClick={handleInvestigate} disabled={loading || !incidentId}>
            {loading ? 'Investigating...' : 'Investigate'}
          </button>
          {result || history.length > 0 || error ? (
            <button type="button" className="secondary-button ghost-button" onClick={handleResetResult}>
              Reset analysis
            </button>
          ) : null}
        </div>
      </section>

      {error ? (
        <section className="panel error-panel">
          <h3>Investigation failed</h3>
          <p>{error}</p>
        </section>
      ) : null}

      {incidentDetail ? (
        <section className="panel inner-panel">
          <h3>Selected incident</h3>
          <p><strong>{incidentDetail.incident_id}</strong> — {incidentDetail.title}</p>
          <p>{incidentDetail.description}</p>
          <ul>
            {incidentDetail.symptoms.map((symptom) => (
              <li key={symptom}>{symptom}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {result ? (
        <section className="panel result-panel">
          <div className="result-header">
            <div>
              <p className="eyebrow">Candidate root cause</p>
              <h2>{result.candidate_root_cause}</h2>
            </div>
            <span className="confidence-badge">
              {result.confidence === null
                ? 'Confidence not calibrated'
                : `Evidence coverage (heuristic): ${Math.round(result.confidence * 100)}%`}
            </span>
          </div>

          <p className="summary-text">{result.summary}</p>
          <p className="llm-status">
            {result.llm?.mode === 'llm'
              ? `Generated by ${result.llm.provider} (${result.llm.model})`
              : 'Evidence-only fallback; no live provider response was used.'}
          </p>

          <div className="meta-grid">
            <div>
              <span className="meta-label">Incident</span>
              <strong>{result.incident_id}</strong>
            </div>
            <div>
              <span className="meta-label">Service</span>
              <strong>{result.service}</strong>
            </div>
            <div>
              <span className="meta-label">Severity</span>
              <strong>{result.severity}</strong>
            </div>
          </div>

          <div className="grid">
            <div className="panel inner-panel">
              <h3>Evidence chain</h3>
              <ol>
                {result.graph_path?.map((step) => <li key={step}>{step}</li>)}
              </ol>
            </div>

            <div className="panel inner-panel">
              <h3>Runtime findings</h3>
              <ul>
                <li>Errors: {result.tool_findings?.logs.error_count ?? 0}</li>
                <li>Peak DB usage: {result.tool_findings?.metrics.db_connection_usage_peak ?? 0}%</li>
                <li>Latest error: {result.tool_findings?.logs.latest_error ?? 'none'}</li>
              </ul>
            </div>
          </div>

          <div className="panel inner-panel">
            <h3>Recommended action</h3>
            <p>{result.recommendation?.recommended_action}</p>
            <p className="approval-note">{result.recommendation?.approval_note}</p>
            <div className="approval-actions">
              <button type="button" className="secondary-button" onClick={() => handleApproval('approve')} disabled={approvalState !== 'pending'}>
                Approve
              </button>
              <button type="button" className="secondary-button danger-button" onClick={() => handleApproval('reject')} disabled={approvalState !== 'pending'}>
                Reject
              </button>
            </div>
            <p className="approval-status">Status: {approvalState}</p>
          </div>

          <div className="panel inner-panel">
            <h3>Investigation timeline</h3>
            <ol>
              {result.timeline?.map((item) => (
                <li key={item.event}>
                  <strong>{item.event}</strong>
                  <p>{item.details}</p>
                </li>
              ))}
            </ol>
          </div>

          <div className="panel inner-panel">
            <h3>Approval history</h3>
            {history.length === 0 ? (
              <p>No prior review history for this incident.</p>
            ) : (
              <ul className="evidence-list">
                {history.map((entry) => (
                  <li key={`${entry.incident_id}-${entry.created_at}`}>
                    <strong>{entry.decision}</strong>
                    <span>{entry.status}</span>
                    <p>{entry.recommended_action}</p>
                    <small>{new Date(entry.created_at).toLocaleString()}</small>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel inner-panel">
            <h3>Retrieved evidence</h3>
            <ul className="evidence-list">
              {result.evidence_documents.map((document) => (
                <li key={document.document_id}>
                  <strong>{document.title}</strong>
                  <span>{document.document_type}</span>
                  <p>{document.content}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </main>
  );
}
