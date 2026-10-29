import { useEffect, useMemo, useState } from "react";

import {
  ContextBar,
  EmptyState,
  InlineAlert,
  KeyValueList,
  MetricCard,
  SectionCard,
  SectionIntro,
  StatusBadge
} from "../components/Ui";
import { api } from "../utils/api";
import { formatDate, formatDateTime, formatEnum, formatList } from "../utils/format";

function BatchList({ batches, selectedBatch, onSelect }) {
  return (
    <div className="timeline-list">
      {batches.map((batch) => (
        <button
          key={batch.id}
          type="button"
          className={`timeline-item timeline-item--button${selectedBatch === batch.id ? " timeline-item--selected" : ""}`}
          onClick={() => onSelect(batch.id)}
        >
          <div>
            <strong>{batch.name}</strong>
            <div className="muted">{batch.phase}</div>
          </div>
          <StatusBadge tone="info">{batch.year}</StatusBadge>
        </button>
      ))}
      {!batches.length ? <EmptyState title="No assigned batches" description="Program batches mapped to this user will appear here." /> : null}
    </div>
  );
}

export function ProgramManagerPage({ token, section = "batches" }) {
  const [batches, setBatches] = useState([]);
  const [requests, setRequests] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const [batchData, requestData] = await Promise.all([
          api.fetchProgramBatches(token),
          api.fetchProgramRuleRequests(token, statusFilter)
        ]);
        setBatches(batchData);
        setRequests(requestData);
        setSelectedBatch((current) => current || batchData[0]?.id || "");
      } catch (loadError) {
        setError(loadError.message);
      }
    }

    loadData();
  }, [statusFilter, token]);

  useEffect(() => {
    if (!selectedBatch) {
      setCandidates([]);
      return;
    }

    async function loadCandidates() {
      try {
        const data = await api.fetchProgramBatchCandidates(token, selectedBatch);
        setCandidates(data);
      } catch (loadError) {
        setError(loadError.message);
      }
    }

    loadCandidates();
  }, [selectedBatch, token]);

  const selectedBatchRecord = useMemo(
    () => batches.find((batch) => batch.id === selectedBatch) ?? null,
    [batches, selectedBatch]
  );

  const metrics = {
    assignedBatches: batches.length,
    visibleCandidates: candidates.length,
    pendingRules: requests.filter((item) => item.status === "PENDING").length,
    reviewedRules: requests.filter((item) => item.status !== "PENDING").length
  };

  return (
    <div className="dashboard-stack">
      <InlineAlert tone="danger" message={error} />

      {section === "batches" ? (
        <div className="section-stack">
          <div className="hero-strip hero-strip--program">
            <div>
              <div className="eyebrow">Assigned Batches</div>
              <h2>Read-only program batch view</h2>
              <p>Program Manager can review assigned batches and their candidate rosters without editing the underlying training data.</p>
            </div>
            <div className="token-row">
              <StatusBadge tone="info">{metrics.assignedBatches} assigned</StatusBadge>
              <StatusBadge tone="warning">{metrics.pendingRules} pending requests</StatusBadge>
            </div>
          </div>

          <div className="metrics-row">
            <MetricCard label="Assigned batches" value={metrics.assignedBatches} tone="accent" hint="Read-only program scope" />
            <MetricCard label="Visible candidates" value={metrics.visibleCandidates} tone="success" hint="Selected batch roster size" />
            <MetricCard label="Pending rule requests" value={metrics.pendingRules} tone="warning" hint="Awaiting review" />
            <MetricCard label="Reviewed requests" value={metrics.reviewedRules} tone="default" hint="Approved or rejected" />
          </div>

          <SectionIntro
            eyebrow="Batches"
            title="Inspect assigned batches and batch rosters"
            description="This workspace supports the available read-only APIs for Program Manager: assigned program batches and candidate-level visibility within each assigned batch."
          />

          <div className="workspace-layout">
            <aside className="workspace-sidebar">
              <SectionCard title="Assigned batches" subtitle="Select any assigned program batch to inspect its roster.">
                <BatchList batches={batches} selectedBatch={selectedBatch} onSelect={setSelectedBatch} />
              </SectionCard>
            </aside>

            <div className="workspace-main">
              <ContextBar
                items={[
                  { label: "Batch", value: selectedBatchRecord?.name ?? "--" },
                  { label: "Owner", value: selectedBatchRecord?.owner_name ?? "Unassigned" },
                  { label: "Dates", value: selectedBatchRecord ? `${formatDate(selectedBatchRecord.start_date)} to ${formatDate(selectedBatchRecord.end_date)}` : "--" },
                  { label: "Tech stack", value: formatList(selectedBatchRecord?.tech_stack) }
                ]}
              />

              <SectionCard title="Batch roster" subtitle="Candidate list within the selected assigned batch.">
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Candidate</th>
                        <th>Status</th>
                        <th>Phase</th>
                        <th>Tech</th>
                      </tr>
                    </thead>
                    <tbody>
                      {candidates.map((candidate) => (
                        <tr key={candidate.id}>
                          <td>
                            <div className="table-primary">{candidate.name}</div>
                            <div className="table-secondary">{candidate.email}</div>
                          </td>
                          <td>{formatEnum(candidate.status)}</td>
                          <td>{candidate.eligible_phase}</td>
                          <td>{candidate.tech_stack ?? "--"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!candidates.length ? <EmptyState title="No candidates available" description="Candidates for the selected assigned batch will appear here." /> : null}
              </SectionCard>

              <SectionCard title="Program batch cards" subtitle="Card view of all assigned batches for quick portfolio scanning.">
                <div className="insight-grid">
                  {batches.map((batch) => (
                    <article className="insight-panel" key={batch.id}>
                      <div className="insight-panel__top">
                        <div>
                          <div className="eyebrow">{batch.phase}</div>
                          <h3>{batch.name}</h3>
                        </div>
                        <StatusBadge tone="info">{batch.year}</StatusBadge>
                      </div>
                      <KeyValueList
                        items={[
                          { label: "Owner", value: batch.owner_name ?? "Unassigned" },
                          { label: "Start", value: formatDate(batch.start_date) },
                          { label: "End", value: formatDate(batch.end_date) },
                          { label: "Tech", value: formatList(batch.tech_stack) }
                        ]}
                      />
                    </article>
                  ))}
                </div>
              </SectionCard>
            </div>
          </div>
        </div>
      ) : null}

      {section === "rule-requests" ? (
        <div className="section-stack">
          <ContextBar
            items={[
              { label: "Pending requests", value: metrics.pendingRules },
              { label: "Reviewed requests", value: metrics.reviewedRules },
              { label: "Visible requests", value: requests.length },
              { label: "Role", value: "Program Manager" }
            ]}
          />
          <SectionIntro
            eyebrow="Rule Requests"
            title="Review configuration change requests"
            description="Program Manager receives the rule change requests raised by the L&D Manager and can monitor which requests are pending, approved, or rejected."
          />

          <SectionCard
            title="Configuration request queue"
            subtitle="Queue of rule configuration requests raised by L&D."
            actions={
              <label className="field field--compact">
                <span>Status filter</span>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="">All statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="APPROVED">Approved</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </label>
            }
          >
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Batch</th>
                    <th>Assessment</th>
                    <th>Current %</th>
                    <th>Requested %</th>
                    <th>Status</th>
                    <th>Raised</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((request) => (
                    <tr key={request.id}>
                      <td>{request.batch_id}</td>
                      <td>{request.custom_exam_name || formatEnum(request.exam_type) || "--"}</td>
                      <td>{request.current_pass_percentage ?? "--"}%</td>
                      <td>{request.requested_pass_percentage ?? "--"}%</td>
                      <td>
                        <StatusBadge tone={request.status === "PENDING" ? "warning" : request.status === "APPROVED" ? "success" : "danger"}>
                          {formatEnum(request.status)}
                        </StatusBadge>
                      </td>
                      <td>{formatDateTime(request.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!requests.length ? <EmptyState title="No rule requests available" description="Rule requests raised by L&D will appear here." /> : null}
          </SectionCard>
        </div>
      ) : null}
    </div>
  );
}
