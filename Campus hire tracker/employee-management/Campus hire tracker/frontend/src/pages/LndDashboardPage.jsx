import { useEffect, useMemo, useState } from "react";

import {
  ContextBar,
  EmptyState,
  InlineAlert,
  KeyValueList,
  LoadingState,
  MetricCard,
  SegmentedTabs,
  SectionCard,
  SectionIntro,
  StatusBadge
} from "../components/Ui";
import { api } from "../utils/api";
import { formatDateTime, formatEnum, uniqueValues } from "../utils/format";

function YearCardGrid({ grid }) {
  const cards = [grid?.active_year, grid?.completed_year, ...(grid?.archive_years ?? [])].filter(Boolean);

  if (!cards.length) {
    return <EmptyState title="No year data available" description="Upload and configure the current intake to populate the year grid." />;
  }

  return (
    <div className="insight-grid">
      {cards.map((card) => (
        <article className="insight-panel" key={card.year}>
          <div className="insight-panel__top">
            <div>
              <div className="eyebrow">Year</div>
              <h3>{card.year}</h3>
            </div>
            <StatusBadge tone={card.status === "ACTIVE" ? "success" : card.status === "COMPLETED" ? "warning" : "neutral"}>
              {formatEnum(card.status)}
            </StatusBadge>
          </div>
          <KeyValueList
            items={[
              { label: "Candidates", value: card.candidate_count },
              { label: "Batches", value: card.batch_count },
              { label: "Phases", value: card.phases_created?.length ?? 0 }
            ]}
          />
          <div className="token-row">
            {(card.phases_created ?? []).length ? (
              card.phases_created.map((phase) => <StatusBadge key={phase}>{phase}</StatusBadge>)
            ) : (
              <span className="muted">No phases created</span>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

function LndMasterDatabaseSection({ token }) {
  const [file, setFile] = useState(null);
  const [filters, setFilters] = useState({ search: "", min_score: "", max_score: "", attended: "", page: 1, limit: 10 });
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);

  async function searchCandidates() {
    setLoading(true);
    setError("");
    try {
      const data = await api.searchMasterCandidates(token, {
        search: filters.search || undefined,
        min_score: filters.min_score || undefined,
        max_score: filters.max_score || undefined,
        attended: filters.attended === "" ? undefined : filters.attended,
        page: filters.page,
        limit: filters.limit
      });
      setResults(Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    searchCandidates();
  }, []);

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Master Database"
        title="Manage yearly hire records"
        description="Upload the yearly candidate master data, search the complete candidate database, and review baseline or knowledge-check driven status changes in one place."
      />
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />
      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <SectionCard title="Upload candidate file" subtitle="Upload the yearly hire dataset from Excel.">
            <div className="form-grid form-grid--single">
              <label className="field">
                <span>Excel file</span>
                <input type="file" accept=".xlsx,.xls,.csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              </label>
            </div>
            <button
              className="button button--primary"
              disabled={!file}
              onClick={async () => {
                setError("");
                setFeedback("");
                try {
                  await api.uploadMasterCandidates(token, file);
                  setFeedback("Master database uploaded successfully.");
                  setFile(null);
                  await searchCandidates();
                } catch (uploadError) {
                  setError(uploadError.message);
                }
              }}
              type="button"
            >
              Upload master data
            </button>
          </SectionCard>

          <SectionCard title="Search filters" subtitle="Search the full database by score and attendance.">
            <div className="form-grid form-grid--single">
              <label className="field">
                <span>Search</span>
                <input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Name, email, college" />
              </label>
              <label className="field">
                <span>Minimum score</span>
                <input type="number" value={filters.min_score} onChange={(event) => setFilters((current) => ({ ...current, min_score: event.target.value }))} />
              </label>
              <label className="field">
                <span>Maximum score</span>
                <input type="number" value={filters.max_score} onChange={(event) => setFilters((current) => ({ ...current, max_score: event.target.value }))} />
              </label>
              <label className="field">
                <span>Attendance</span>
                <select value={filters.attended} onChange={(event) => setFilters((current) => ({ ...current, attended: event.target.value }))}>
                  <option value="">All</option>
                  <option value="true">Attended</option>
                  <option value="false">Not attended</option>
                </select>
              </label>
            </div>
            <button className="button button--secondary" onClick={searchCandidates} type="button">Search database</button>
          </SectionCard>
        </aside>

        <div className="workspace-main">
          <SectionCard title="Candidate register" subtitle="Complete database of yearly hires uploaded into the platform.">
            {loading ? <LoadingState label="Loading master database..." /> : null}
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Phase</th>
                    <th>Status</th>
                    <th>College</th>
                    <th>Tech</th>
                    <th>Scores</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((candidate) => (
                    <tr key={candidate.id}>
                      <td>
                        <div className="table-primary">{candidate.name}</div>
                        <div className="table-secondary">{candidate.email}</div>
                      </td>
                      <td>{candidate.eligible_phase}</td>
                      <td>{formatEnum(candidate.status)}</td>
                      <td>{candidate.college ?? "--"}</td>
                      <td>{candidate.tech_stack ?? "--"}</td>
                      <td>{candidate.percentage ?? candidate.pre_onboarding_score ?? "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!loading && !results.length ? <EmptyState title="No candidates found" description="Upload data or refine the filter set." /> : null}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

function LndExamsSection({ token }) {
  const [baselineFile, setBaselineFile] = useState(null);
  const [knowledgeFile, setKnowledgeFile] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");

  async function upload(kind) {
    setError("");
    setFeedback("");
    try {
      if (kind === "baseline") {
        await api.uploadBaseline(token, baselineFile);
        setFeedback("Baseline scores uploaded successfully.");
        return;
      }

      await api.uploadKnowledgeCheck(token, knowledgeFile);
      setFeedback("Knowledge check scores uploaded successfully.");
    } catch (uploadError) {
      setError(uploadError.message);
    }
  }

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Exams"
        title="Upload baseline and coding challenge scores"
        description="This section supports the exam data flows already available in the backend: baseline uploads, knowledge check uploads, and baseline mismatch resolution."
      />
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />
      <div className="panel-cluster panel-cluster--two">
        <SectionCard title="Baseline upload" subtitle="Upload baseline exam data and mark attendance or non-attendance through the uploaded sheet.">
          <div className="form-grid form-grid--single">
            <label className="field">
              <span>Baseline file</span>
              <input type="file" accept=".xlsx,.xls,.csv" onChange={(event) => setBaselineFile(event.target.files?.[0] ?? null)} />
            </label>
          </div>
          <div className="token-row">
            <button className="button button--primary" disabled={!baselineFile} onClick={() => upload("baseline")} type="button">
              Upload baseline scores
            </button>
            <button
              className="button button--ghost"
              onClick={async () => {
                setError("");
                setFeedback("");
                try {
                  await api.resolveBaseline(token, { resolve_all: true });
                  setFeedback("Baseline mismatches resolved using auto resolve.");
                } catch (resolveError) {
                  setError(resolveError.message);
                }
              }}
              type="button"
            >
              Auto resolve mismatches
            </button>
          </div>
        </SectionCard>

        <SectionCard title="Knowledge check upload" subtitle="Upload coding challenge scores to support direct post-onboarding or phase filtering flows.">
          <div className="form-grid form-grid--single">
            <label className="field">
              <span>Knowledge check file</span>
              <input type="file" accept=".xlsx,.xls,.csv" onChange={(event) => setKnowledgeFile(event.target.files?.[0] ?? null)} />
            </label>
          </div>
          <button className="button button--primary" disabled={!knowledgeFile} onClick={() => upload("knowledge")} type="button">
            Upload knowledge check
          </button>
        </SectionCard>
      </div>

      <ContextBar
        items={[
          { label: "Baseline flow", value: "Upload and resolve" },
          { label: "Knowledge check", value: "Upload supported" },
          { label: "Attendance update", value: "Handled by backend" },
          { label: "Template support", value: "Backend endpoint not available yet" }
        ]}
      />
    </div>
  );
}

function LndBatchesSection({ token, grid }) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [workspace, setWorkspace] = useState(null);
  const [owners, setOwners] = useState([]);
  const [phasePool, setPhasePool] = useState([]);
  const [selectedPhase, setSelectedPhase] = useState("");
  const [phaseCandidates, setPhaseCandidates] = useState([]);
  const [phaseForm, setPhaseForm] = useState({ phase: "", candidate_emails_csv: "" });
  const [batchForm, setBatchForm] = useState({ phase: "", name: "", owner_id: "" });
  const [assignOwnerForm, setAssignOwnerForm] = useState({ batch_id: "", owner_id: "" });
  const [assignCandidatesForm, setAssignCandidatesForm] = useState({ batch_id: "", emails_csv: "" });
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const [batchView, setBatchView] = useState("workspace");

  async function loadWorkspace(targetYear = year) {
    setLoading(true);
    setError("");
    try {
      const [card, ownerData] = await Promise.all([api.fetchYearPhases(token, targetYear), api.fetchAssignableOwners(token)]);
      setWorkspace(card);
      setOwners(ownerData);
      const phases = card?.phases?.map((item) => item.phase) ?? [];
      setPhasePool(phases);
      setSelectedPhase((current) => (current && phases.includes(current) ? current : phases[0] ?? ""));
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedPhase) {
      setPhaseCandidates([]);
      return;
    }

    async function loadPhaseCandidates() {
      try {
        const data = await api.fetchPhaseCandidates(token, year, selectedPhase);
        setPhaseCandidates(data);
      } catch (loadError) {
        setError(loadError.message);
      }
    }

    loadPhaseCandidates();
  }, [selectedPhase, token, year]);

  async function runAction(action, successMessage, reset) {
    setError("");
    setFeedback("");
    try {
      await action();
      setFeedback(successMessage);
      reset?.();
      await loadWorkspace(year);
    } catch (actionError) {
      setError(actionError.message);
    }
  }

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Batches"
        title="Build the current year training structure"
        description="Create phases for the active year, add candidate emails into each phase, create multiple batches inside each phase, and assign a batch owner from the users created in user management."
        actions={
          <div className="toolbar toolbar--compact">
            <label className="field field--compact">
              <span>Working year</span>
              <input type="number" min="2000" max="2100" value={year} onChange={(event) => setYear(Number(event.target.value))} />
            </label>
            <button className="button button--primary" onClick={() => loadWorkspace(year)} type="button">Refresh year</button>
          </div>
        }
      />
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />
      <YearCardGrid grid={grid} />
      <ContextBar
        items={[
          { label: "Active year", value: grid?.active_year?.year ?? year },
          { label: "Completed year", value: grid?.completed_year?.year ?? "--" },
          { label: "Archive years", value: grid?.archive_years?.length ?? 0 },
          { label: "Available owners", value: owners.length }
        ]}
      />

      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <SectionCard title="Current year workspace" subtitle="Phase and batch context for the selected year.">
            {loading ? (
              <LoadingState label="Loading year workspace..." />
            ) : workspace ? (
              <>
                <KeyValueList
                  items={[
                    { label: "Year", value: workspace.year },
                    { label: "Status", value: formatEnum(workspace.status) },
                    { label: "Candidates", value: workspace.candidate_count },
                    { label: "Batches", value: workspace.batch_count }
                  ]}
                />
                <div className="token-row">
                  {(workspace.phases ?? []).map((phase) => (
                    <button
                      className={`chip-button${selectedPhase === phase.phase ? " chip-button--active" : ""}`}
                      key={phase.id}
                      onClick={() => setSelectedPhase(phase.phase)}
                      type="button"
                    >
                      {phase.phase}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState title="No year loaded" description="Refresh the year to see the active grid and phase setup." />
            )}
          </SectionCard>

          <SectionCard title="Phase candidates" subtitle="Only candidates available for the selected phase appear here.">
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>College</th>
                    <th>Tech</th>
                  </tr>
                </thead>
                <tbody>
                  {phaseCandidates.map((candidate) => (
                    <tr key={candidate.id}>
                      <td>
                        <div className="table-primary">{candidate.name}</div>
                        <div className="table-secondary">{candidate.email}</div>
                      </td>
                      <td>{candidate.college ?? "--"}</td>
                      <td>{candidate.tech_stack ?? "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!phaseCandidates.length ? <EmptyState title="No candidates in phase" description="Import candidate emails to create the phase roster." /> : null}
          </SectionCard>
        </aside>

        <div className="workspace-main">
          <SegmentedTabs
            items={[
              { value: "workspace", label: "Workspace", caption: "Year and phase context" },
              { value: "phase", label: "Create Phase", caption: "Create phase cards and add candidates" },
              { value: "batch", label: "Create Batch", caption: "Create batches inside phases" },
              { value: "assignment", label: "Assignments", caption: "Owner and candidate assignment" }
            ]}
            value={batchView}
            onChange={setBatchView}
          />

          {batchView === "workspace" ? (
            <SectionCard title="Year workspace summary" subtitle="Review the selected year context before performing setup actions.">
              {loading ? (
                <LoadingState label="Loading year workspace..." />
              ) : workspace ? (
                <div className="panel-cluster panel-cluster--two">
                  <KeyValueList
                    items={[
                      { label: "Year", value: workspace.year },
                      { label: "Status", value: formatEnum(workspace.status) },
                      { label: "Candidates", value: workspace.candidate_count },
                      { label: "Batches", value: workspace.batch_count }
                    ]}
                  />
                  <div className="token-row">
                    {(workspace.phases ?? []).map((phase) => (
                      <StatusBadge key={phase.id} tone={selectedPhase === phase.phase ? "info" : "neutral"}>
                        {phase.phase}
                      </StatusBadge>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState title="No year loaded" description="Refresh the year to see the active grid and phase setup." />
              )}
            </SectionCard>
          ) : null}

          {batchView === "phase" ? (
            <SectionCard title="Create phase card" subtitle="Use a dedicated task view to add candidates directly into a phase.">
              <div className="form-grid form-grid--single">
                <label className="field">
                  <span>Phase name</span>
                  <input value={phaseForm.phase} onChange={(event) => setPhaseForm((current) => ({ ...current, phase: event.target.value }))} />
                </label>
                <label className="field">
                  <span>Candidate emails</span>
                  <textarea rows="4" value={phaseForm.candidate_emails_csv} onChange={(event) => setPhaseForm((current) => ({ ...current, candidate_emails_csv: event.target.value }))} />
                </label>
              </div>
              <button
                className="button button--primary"
                onClick={() =>
                  runAction(
                    () => api.createPhaseCard(token, year, phaseForm),
                    "Phase card created successfully.",
                    () => setPhaseForm({ phase: "", candidate_emails_csv: "" })
                  )
                }
                type="button"
              >
                Create phase
              </button>
            </SectionCard>
          ) : null}

          {batchView === "batch" ? (
            <SectionCard title="Create batch inside phase" subtitle="Keep batch creation separate from ownership and candidate assignment.">
              <div className="form-grid form-grid--single">
                <label className="field">
                  <span>Phase</span>
                  <select value={batchForm.phase} onChange={(event) => setBatchForm((current) => ({ ...current, phase: event.target.value }))}>
                    <option value="">Select phase</option>
                    {phasePool.map((phase) => (
                      <option key={phase} value={phase}>{phase}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Batch name</span>
                  <input value={batchForm.name} onChange={(event) => setBatchForm((current) => ({ ...current, name: event.target.value }))} />
                </label>
                <label className="field">
                  <span>Batch owner</span>
                  <select value={batchForm.owner_id} onChange={(event) => setBatchForm((current) => ({ ...current, owner_id: event.target.value }))}>
                    <option value="">Select owner</option>
                    {owners.map((owner) => (
                      <option key={owner.id} value={owner.id}>{owner.name}</option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                className="button button--primary"
                onClick={() =>
                  runAction(
                    () => api.createPhaseBatch(token, year, batchForm.phase, { name: batchForm.name, owner_id: batchForm.owner_id }),
                    "Batch created successfully.",
                    () => setBatchForm({ phase: "", name: "", owner_id: "" })
                  )
                }
                type="button"
              >
                Create batch
              </button>
            </SectionCard>
          ) : null}

          {batchView === "assignment" ? (
            <div className="panel-cluster panel-cluster--two">
              <SectionCard title="Assign or reassign owner" subtitle="Select any created batch and update the owner assignment.">
                <div className="form-grid form-grid--single">
                  <label className="field">
                    <span>Batch</span>
                    <select value={assignOwnerForm.batch_id} onChange={(event) => setAssignOwnerForm((current) => ({ ...current, batch_id: event.target.value }))}>
                      <option value="">Select batch</option>
                      {(workspace?.batches ?? []).map((batch) => (
                        <option key={batch.id} value={batch.id}>{batch.name} ({batch.phase})</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Owner</span>
                    <select value={assignOwnerForm.owner_id} onChange={(event) => setAssignOwnerForm((current) => ({ ...current, owner_id: event.target.value }))}>
                      <option value="">Select owner</option>
                      {owners.map((owner) => (
                        <option key={owner.id} value={owner.id}>{owner.name}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <button
                  className="button button--secondary"
                  onClick={() =>
                    runAction(
                      () => api.assignBatchOwner(token, assignOwnerForm.batch_id, { owner_id: assignOwnerForm.owner_id }),
                      "Batch owner updated.",
                      () => setAssignOwnerForm({ batch_id: "", owner_id: "" })
                    )
                  }
                  type="button"
                >
                  Update owner
                </button>
              </SectionCard>

              <SectionCard title="Assign candidates to batch" subtitle="Move candidates from the phase pool into a created batch using comma-separated emails.">
                <div className="form-grid form-grid--single">
                  <label className="field">
                    <span>Batch</span>
                    <select value={assignCandidatesForm.batch_id} onChange={(event) => setAssignCandidatesForm((current) => ({ ...current, batch_id: event.target.value }))}>
                      <option value="">Select batch</option>
                      {(workspace?.batches ?? []).map((batch) => (
                        <option key={batch.id} value={batch.id}>{batch.name} ({batch.phase})</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Candidate emails</span>
                    <textarea rows="4" value={assignCandidatesForm.emails_csv} onChange={(event) => setAssignCandidatesForm((current) => ({ ...current, emails_csv: event.target.value }))} />
                  </label>
                </div>
                <button
                  className="button button--primary"
                  onClick={() =>
                    runAction(
                      () => api.assignBatchCandidates(token, assignCandidatesForm.batch_id, { emails_csv: assignCandidatesForm.emails_csv }),
                      "Candidates assigned to batch.",
                      () => setAssignCandidatesForm({ batch_id: "", emails_csv: "" })
                    )
                  }
                  type="button"
                >
                  Assign candidates
                </button>
              </SectionCard>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LndConfigurationSection({ token }) {
  const [form, setForm] = useState({
    batch_id: "",
    exam_type: "FOUNDATION_EXAM",
    custom_exam_name: "",
    current_pass_percentage: 60,
    requested_pass_percentage: 70,
    reason: ""
  });
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [configView, setConfigView] = useState("request");

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Configuration"
        title="Send rule change requests"
        description="L&D Manager can raise configuration change requests to the Program Manager by specifying the batch, pass percentage change, exam type, and business reason."
      />
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />
      <SegmentedTabs
        items={[
          { value: "request", label: "New Request", caption: "Raise a configuration change" },
          { value: "guide", label: "Guidance", caption: "What to send in a request" }
        ]}
        value={configView}
        onChange={setConfigView}
      />
      {configView === "request" ? (
      <SectionCard title="Rule configuration request" subtitle="Requests are forwarded to the Program Manager for approval or rejection.">
        <div className="form-grid">
          <label className="field">
            <span>Batch ID</span>
            <input value={form.batch_id} onChange={(event) => setForm((current) => ({ ...current, batch_id: event.target.value }))} />
          </label>
          <label className="field">
            <span>Exam type</span>
            <select value={form.exam_type} onChange={(event) => setForm((current) => ({ ...current, exam_type: event.target.value }))}>
              {["FOUNDATION_EXAM", "MODULE_EXAM", "ADVANCED_EXAM", "FINAL_EXAM", "CUSTOM_EXAM"].map((type) => (
                <option key={type} value={type}>{formatEnum(type)}</option>
              ))}
            </select>
          </label>
          {form.exam_type === "CUSTOM_EXAM" ? (
            <label className="field">
              <span>Custom exam name</span>
              <input value={form.custom_exam_name} onChange={(event) => setForm((current) => ({ ...current, custom_exam_name: event.target.value }))} />
            </label>
          ) : null}
          <label className="field">
            <span>Current pass percentage</span>
            <input type="number" value={form.current_pass_percentage} onChange={(event) => setForm((current) => ({ ...current, current_pass_percentage: event.target.value }))} />
          </label>
          <label className="field">
            <span>Requested pass percentage</span>
            <input type="number" value={form.requested_pass_percentage} onChange={(event) => setForm((current) => ({ ...current, requested_pass_percentage: event.target.value }))} />
          </label>
          <label className="field field--full">
            <span>Reason</span>
            <textarea rows="5" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} />
          </label>
        </div>
        <button
          className="button button--primary"
          onClick={async () => {
            setError("");
            setFeedback("");
            try {
              await api.createRuleChangeRequest(token, {
                ...form,
                current_pass_percentage: Number(form.current_pass_percentage),
                requested_pass_percentage: Number(form.requested_pass_percentage),
                custom_exam_name: form.exam_type === "CUSTOM_EXAM" ? form.custom_exam_name : null
              });
              setFeedback("Rule change request sent to the Program Manager.");
            } catch (submitError) {
              setError(submitError.message);
            }
          }}
          type="button"
        >
          Send rule request
        </button>
      </SectionCard>
      ) : null}
      {configView === "guide" ? (
        <SectionCard title="Request guidance" subtitle="Use this task view to avoid mixing instructions with the form itself.">
          <KeyValueList
            items={[
              { label: "Batch reference", value: "Use the target batch ID" },
              { label: "Exam scope", value: "Pick one exam type per request" },
              { label: "Pass change", value: "Provide current and requested values" },
              { label: "Reason", value: "Include clear business justification" }
            ]}
          />
        </SectionCard>
      ) : null}
    </div>
  );
}

function LndRequestsSection({ token }) {
  const [requests, setRequests] = useState([]);
  const [reviewForm, setReviewForm] = useState({ requestId: "", status: "APPROVED", reviewer_comment: "" });
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [requestView, setRequestView] = useState("queue");

  async function loadRequests() {
    try {
      const data = await api.fetchLndChangeRequests(token);
      setRequests(data);
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => {
    loadRequests();
  }, [token]);

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Dropout / Resignation"
        title="Review candidate requests raised by batch owners"
        description="This queue captures dropout and resignation requests raised from delivery batches. L&D Manager reviews the request and decides whether to revoke or reject the change."
      />
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />
      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <SectionCard title="Request queue" subtitle="Incoming dropout and resignation requests.">
            <div className="timeline-list">
              {requests.map((request) => (
                <div className="timeline-item" key={request.id}>
                  <div>
                    <strong>{formatEnum(request.request_type)}</strong>
                    <div className="muted">{request.candidate_email ?? "--"}</div>
                  </div>
                  <StatusBadge tone={request.status === "PENDING" ? "warning" : request.status === "APPROVED" ? "success" : "danger"}>
                    {formatEnum(request.status)}
                  </StatusBadge>
                </div>
              ))}
            </div>
            {!requests.length ? <EmptyState title="No requests available" description="Batch owner requests will appear here." /> : null}
          </SectionCard>
        </aside>

        <div className="workspace-main">
          <SegmentedTabs
            items={[
              { value: "queue", label: "Queue Summary", caption: "Incoming request overview" },
              { value: "review", label: "Review Action", caption: "Approve or reject a request" }
            ]}
            value={requestView}
            onChange={setRequestView}
          />

          {requestView === "queue" ? (
            <SectionCard title="Request summary" subtitle="Keep the review action separate from queue monitoring.">
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Candidate</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requests.map((request) => (
                      <tr key={request.id}>
                        <td>{formatEnum(request.request_type)}</td>
                        <td>{request.candidate_email ?? "--"}</td>
                        <td>{formatEnum(request.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!requests.length ? <EmptyState title="No requests available" description="Batch owner requests will appear here." /> : null}
            </SectionCard>
          ) : null}

          {requestView === "review" ? (
            <SectionCard title="Review request" subtitle="Approve or reject the selected request with a review comment.">
              <div className="form-grid form-grid--single">
                <label className="field">
                  <span>Request</span>
                  <select value={reviewForm.requestId} onChange={(event) => setReviewForm((current) => ({ ...current, requestId: event.target.value }))}>
                    <option value="">Select request</option>
                    {requests.map((request) => (
                      <option key={request.id} value={request.id}>
                        {formatEnum(request.request_type)} - {request.candidate_email ?? request.id}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Decision</span>
                  <select value={reviewForm.status} onChange={(event) => setReviewForm((current) => ({ ...current, status: event.target.value }))}>
                    <option value="APPROVED">Approve / Revoke</option>
                    <option value="REJECTED">Reject</option>
                  </select>
                </label>
                <label className="field">
                  <span>Review comment</span>
                  <textarea rows="4" value={reviewForm.reviewer_comment} onChange={(event) => setReviewForm((current) => ({ ...current, reviewer_comment: event.target.value }))} />
                </label>
              </div>
              <button
                className="button button--primary"
                onClick={async () => {
                  setError("");
                  setFeedback("");
                  try {
                    await api.reviewLndChangeRequest(token, reviewForm.requestId, {
                      status: reviewForm.status,
                      reviewer_comment: reviewForm.reviewer_comment || null
                    });
                    setFeedback("Request reviewed successfully.");
                    setReviewForm({ requestId: "", status: "APPROVED", reviewer_comment: "" });
                    await loadRequests();
                  } catch (submitError) {
                    setError(submitError.message);
                  }
                }}
                type="button"
              >
                Submit review
              </button>
            </SectionCard>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LndArchivesSection({ token }) {
  const [archiveCards, setArchiveCards] = useState([]);
  const [selectedYear, setSelectedYear] = useState("");
  const [filters, setFilters] = useState({ q: "", phase: "", candidate_status: "", tech_stack: "", college: "" });
  const [archive, setArchive] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [error, setError] = useState("");
  const [archiveView, setArchiveView] = useState("results");

  useEffect(() => {
    async function loadArchives() {
      try {
        const data = await api.fetchYearArchives(token);
        setArchiveCards(data);
        setSelectedYear(data[0] ? String(data[0].year) : "");
      } catch (loadError) {
        setError(loadError.message);
      }
    }

    loadArchives();
  }, [token]);

  useEffect(() => {
    if (!selectedYear) {
      setArchive(null);
      return;
    }

    async function loadArchive() {
      try {
        const data = await api.fetchYearArchiveDetails(token, selectedYear, filters);
        setArchive(data);
      } catch (loadError) {
        setError(loadError.message);
      }
    }

    loadArchive();
  }, [filters, selectedYear, token]);

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Year Archives"
        title="Review past year history"
        description="Browse completed years, filter historical candidates, and view a candidate timeline inside the specific training context."
      />
      <InlineAlert tone="danger" message={error} />
      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <SectionCard title="Archive years" subtitle="Select a past year to load its data.">
            <div className="timeline-list">
              {archiveCards.map((card) => (
                <button
                  className={`timeline-item timeline-item--button${selectedYear === String(card.year) ? " timeline-item--selected" : ""}`}
                  key={card.year}
                  onClick={() => setSelectedYear(String(card.year))}
                  type="button"
                >
                  <div>
                    <strong>{card.year}</strong>
                    <div className="muted">{card.candidate_count} candidates</div>
                  </div>
                  <StatusBadge>{formatEnum(card.status)}</StatusBadge>
                </button>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Filters" subtitle="Filter archive results by phase, status, college, and tech stack.">
            <div className="form-grid form-grid--single">
              <label className="field">
                <span>Search</span>
                <input value={filters.q} onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} />
              </label>
              <label className="field">
                <span>Phase</span>
                <input value={filters.phase} onChange={(event) => setFilters((current) => ({ ...current, phase: event.target.value }))} />
              </label>
              <label className="field">
                <span>Status</span>
                <input value={filters.candidate_status} onChange={(event) => setFilters((current) => ({ ...current, candidate_status: event.target.value }))} />
              </label>
              <label className="field">
                <span>Tech stack</span>
                <input value={filters.tech_stack} onChange={(event) => setFilters((current) => ({ ...current, tech_stack: event.target.value }))} />
              </label>
              <label className="field">
                <span>College</span>
                <input value={filters.college} onChange={(event) => setFilters((current) => ({ ...current, college: event.target.value }))} />
              </label>
            </div>
          </SectionCard>
        </aside>

        <div className="workspace-main">
          <SegmentedTabs
            items={[
              { value: "results", label: "Archive Results", caption: "Filtered candidate history" },
              { value: "timeline", label: "Timeline", caption: "Selected candidate audit trail" }
            ]}
            value={archiveView}
            onChange={setArchiveView}
          />

          {archiveView === "results" ? (
            <SectionCard title="Archive results" subtitle="Filtered candidates from the selected archive year.">
              {archive ? (
                <>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Candidate</th>
                          <th>Phase</th>
                          <th>Status</th>
                          <th>Batch</th>
                          <th>Timeline</th>
                        </tr>
                      </thead>
                      <tbody>
                        {archive.candidates.map((candidate) => (
                          <tr key={candidate.id}>
                            <td>
                              <div className="table-primary">{candidate.name}</div>
                              <div className="table-secondary">{candidate.email}</div>
                            </td>
                            <td>{candidate.eligible_phase}</td>
                            <td>{formatEnum(candidate.status)}</td>
                            <td>{candidate.batch_id ?? "--"}</td>
                            <td>
                              <button
                                className="button button--ghost"
                                disabled={!candidate.batch_id}
                                onClick={async () => {
                                  try {
                                    const data = await api.fetchCandidateTimeline(token, candidate.batch_id, candidate.id);
                                    setTimeline(data);
                                    setArchiveView("timeline");
                                  } catch (timelineError) {
                                    setError(timelineError.message);
                                  }
                                }}
                                type="button"
                              >
                                View timeline
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!archive.candidates.length ? <EmptyState title="No archive results" description="Change the filter set or select a different archive year." /> : null}
                </>
              ) : (
                <EmptyState title="No archive selected" description="Select a year to load past data." />
              )}
            </SectionCard>
          ) : null}

          {archiveView === "timeline" ? (
            <SectionCard title="Candidate timeline" subtitle="L&D Manager can view candidate history inside the selected training context.">
              <div className="timeline-list">
                {timeline.map((event) => (
                  <div className="timeline-item" key={event.id}>
                    <div>
                      <strong>{event.description}</strong>
                      <div className="muted">{formatDateTime(event.created_at)}</div>
                    </div>
                    <StatusBadge>{formatEnum(event.event_type)}</StatusBadge>
                  </div>
                ))}
              </div>
              {!timeline.length ? <EmptyState title="No timeline loaded" description="Choose a candidate from the archive results tab to open the timeline." /> : null}
            </SectionCard>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LndAnalyticsSection({ grid }) {
  const yearCards = [grid?.active_year, grid?.completed_year, ...(grid?.archive_years ?? [])].filter(Boolean);
  const highestCandidateYear = yearCards.reduce((best, current) => (current.candidate_count > (best?.candidate_count ?? -1) ? current : best), null);

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="Analytics"
        title="Review lifecycle and year comparison signals"
        description="The backend does not yet expose dedicated analytics APIs, so this section uses the existing year grid to surface intake counts, batch spread, and year-on-year comparison signals."
      />
      <div className="metrics-row">
        <MetricCard label="Active year candidates" value={grid?.active_year?.candidate_count ?? 0} tone="accent" hint="Current active funnel size" />
        <MetricCard label="Completed year candidates" value={grid?.completed_year?.candidate_count ?? 0} tone="success" hint="Last completed cycle" />
        <MetricCard label="Archive years" value={grid?.archive_years?.length ?? 0} tone="warning" hint="History available for comparison" />
        <MetricCard label="Highest volume year" value={highestCandidateYear?.year ?? "--"} tone="default" hint="From available year cards" />
      </div>
      <SectionCard title="Year comparison" subtitle="High-level comparison using the data already available in the year grid.">
        <YearCardGrid grid={grid} />
      </SectionCard>
    </div>
  );
}

function LndUsersSection({ token }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({
    email: "",
    name: "",
    employee_id: "",
    role: "BATCH_OWNER",
    temporary_password: ""
  });
  const [roleFilter, setRoleFilter] = useState("");
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [userView, setUserView] = useState("create");

  async function loadUsers(role = roleFilter) {
    try {
      const data = await api.fetchLndUsers(token, role);
      setUsers(data);
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => {
    loadUsers();
  }, [token]);

  return (
    <div className="section-stack">
      <SectionIntro
        eyebrow="User Management"
        title="Create batch owners and program managers"
        description="L&D Manager creates users with name, UST email, employee ID, role, and temporary password. The created user then logs in and is forced to change password before normal access."
      />
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />
      <SegmentedTabs
        items={[
          { value: "create", label: "Create User", caption: "Add batch owners and program managers" },
          { value: "directory", label: "User Directory", caption: "Review created user accounts" }
        ]}
        value={userView}
        onChange={setUserView}
      />
      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          {userView === "create" ? (
          <SectionCard title="Create user" subtitle="Temporary password is required for first login.">
            <div className="form-grid form-grid--single">
              <label className="field">
                <span>Name</span>
                <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
              </label>
              <label className="field">
                <span>UST email</span>
                <input type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
              </label>
              <label className="field">
                <span>UST employee ID</span>
                <input value={form.employee_id} onChange={(event) => setForm((current) => ({ ...current, employee_id: event.target.value }))} />
              </label>
              <label className="field">
                <span>Role</span>
                <select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>
                  <option value="BATCH_OWNER">Batch Owner</option>
                  <option value="PROGRAM_MANAGER">Program Manager</option>
                </select>
              </label>
              <label className="field">
                <span>Temporary password</span>
                <input type="password" value={form.temporary_password} onChange={(event) => setForm((current) => ({ ...current, temporary_password: event.target.value }))} />
              </label>
            </div>
            <button
              className="button button--primary"
              onClick={async () => {
                setError("");
                setFeedback("");
                try {
                  await api.createPlatformUser(token, form);
                  setFeedback("User created successfully.");
                  setForm({
                    email: "",
                    name: "",
                    employee_id: "",
                    role: "BATCH_OWNER",
                    temporary_password: ""
                  });
                  await loadUsers(roleFilter);
                } catch (submitError) {
                  setError(submitError.message);
                }
              }}
              type="button"
            >
              Create user
            </button>
          </SectionCard>
          ) : (
            <SectionCard title="Directory guidance" subtitle="Use the directory tab to review role-based user coverage.">
              <EmptyState title="Directory view ready" description="Switch to the User Directory tab to review accounts and filter by role." />
            </SectionCard>
          )}
        </aside>

        <div className="workspace-main">
          {userView === "directory" ? (
          <SectionCard
            title="User directory"
            subtitle="Read-only directory of created users."
            actions={
              <label className="field field--compact">
                <span>Role filter</span>
                <select
                  value={roleFilter}
                  onChange={(event) => {
                    const role = event.target.value;
                    setRoleFilter(role);
                    loadUsers(role);
                  }}
                >
                  <option value="">All roles</option>
                  <option value="BATCH_OWNER">Batch Owner</option>
                  <option value="PROGRAM_MANAGER">Program Manager</option>
                </select>
              </label>
            }
          >
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Employee ID</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>
                        <div className="table-primary">{user.name}</div>
                        <div className="table-secondary">{user.email}</div>
                      </td>
                      <td>{formatEnum(user.role)}</td>
                      <td>{user.employee_id ?? "--"}</td>
                      <td>{user.must_change_password ? "Password setup pending" : "Active"}</td>
                      <td>{formatDateTime(user.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!users.length ? <EmptyState title="No users available" description="Create users to populate this directory." /> : null}
          </SectionCard>
          ) : (
            <SectionCard title="Creation guidance" subtitle="Use the create tab to keep onboarding actions separate from directory review.">
              <KeyValueList
                items={[
                  { label: "Name", value: "Required" },
                  { label: "UST email", value: "Required" },
                  { label: "Employee ID", value: "Required" },
                  { label: "Temporary password", value: "Required for first login" }
                ]}
              />
            </SectionCard>
          )}
        </div>
      </div>
    </div>
  );
}

export function LndDashboardPage({ token, section = "master-data" }) {
  const [grid, setGrid] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadGrid() {
      try {
        const data = await api.fetchYearGrid(token);
        setGrid(data);
      } catch (loadError) {
        setError(loadError.message);
      }
    }

    loadGrid();
  }, [token]);

  const activePhases = uniqueValues(grid?.active_year?.phases ?? [], (item) => item.phase);

  return (
    <div className="dashboard-stack">
      <InlineAlert tone="danger" message={error} />
      {section === "master-data" ? <LndMasterDatabaseSection token={token} /> : null}
      {section === "exams" ? <LndExamsSection token={token} /> : null}
      {section === "batches" ? <LndBatchesSection token={token} grid={grid} /> : null}
      {section === "configuration" ? <LndConfigurationSection token={token} /> : null}
      {section === "requests" ? <LndRequestsSection token={token} /> : null}
      {section === "archives" ? <LndArchivesSection token={token} /> : null}
      {section === "analytics" ? <LndAnalyticsSection grid={grid} activePhases={activePhases} /> : null}
      {section === "users" ? <LndUsersSection token={token} /> : null}
    </div>
  );
}
