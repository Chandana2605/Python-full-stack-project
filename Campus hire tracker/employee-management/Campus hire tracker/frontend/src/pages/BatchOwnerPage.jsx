import { useEffect, useMemo, useState } from "react";

import {
  ContextBar,
  EmptyState,
  InlineAlert,
  KeyValueList,
  MetricCard,
  SegmentedTabs,
  SectionCard,
  SectionIntro,
  StatusBadge
} from "../components/Ui";
import { api } from "../utils/api";
import { formatDate, formatDateTime, formatEnum, formatList } from "../utils/format";

function BatchPicker({ batches, selectedBatch, onSelect }) {
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
      {!batches.length ? <EmptyState title="No assigned batches" description="Batches assigned to this owner will appear here." /> : null}
    </div>
  );
}

export function BatchOwnerPage({ token, section = "setup" }) {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [eligibleCandidates, setEligibleCandidates] = useState([]);
  const [examResults, setExamResults] = useState([]);
  const [requests, setRequests] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [examTemplate, setExamTemplate] = useState("");
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [myBatchView, setMyBatchView] = useState("roster");
  const [examView, setExamView] = useState("manual");
  const [requestView, setRequestView] = useState("submit");
  const [configurationForm, setConfigurationForm] = useState({ start_date: "", end_date: "", tech_stack: "" });
  const [candidateSelection, setCandidateSelection] = useState([]);
  const [marksForm, setMarksForm] = useState({ candidate_id: "", mark_key: "", mark_value: "" });
  const [employmentForm, setEmploymentForm] = useState({ candidate_id: "", uid: "", employee_email: "" });
  const [examForm, setExamForm] = useState({
    candidate_id: "",
    phase: "PRE_ONBOARDING",
    exam_type: "FOUNDATION_EXAM",
    custom_exam_name: "",
    attempt: 1,
    score: "",
    max_score: "",
    pass_percentage: 60
  });
  const [examUploadFile, setExamUploadFile] = useState(null);
  const [requestForm, setRequestForm] = useState({ candidate_email: "", request_type: "DROPOUT", reason: "" });

  async function loadBatches() {
    try {
      const data = await api.fetchAssignedBatches(token);
      setBatches(data);
      setSelectedBatch((current) => current || data[0]?.id || "");
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  async function loadBatchContext(batchId) {
    if (!batchId) {
      setCandidates([]);
      setEligibleCandidates([]);
      setExamResults([]);
      return;
    }

    try {
      const [candidateData, eligibleData, examData] = await Promise.all([
        api.fetchAssignedBatchCandidates(token, batchId),
        api.fetchEligibleCandidates(token, batchId),
        api.fetchExamResults(token, batchId)
      ]);
      setCandidates(candidateData);
      setEligibleCandidates(eligibleData);
      setExamResults(examData);
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  async function loadRequests() {
    try {
      const data = await api.fetchOwnerChangeRequests(token);
      setRequests(data);
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => {
    loadBatches();
    loadRequests();
  }, [token]);

  useEffect(() => {
    loadBatchContext(selectedBatch);
  }, [selectedBatch, token]);

  const selectedBatchRecord = useMemo(
    () => batches.find((batch) => batch.id === selectedBatch) ?? null,
    [batches, selectedBatch]
  );

  useEffect(() => {
    if (!selectedBatchRecord) {
      return;
    }

    setConfigurationForm({
      start_date: selectedBatchRecord.start_date ?? "",
      end_date: selectedBatchRecord.end_date ?? "",
      tech_stack: selectedBatchRecord.tech_stack?.join(", ") ?? ""
    });
  }, [selectedBatchRecord]);

  const metrics = {
    activeBatches: batches.length,
    roster: candidates.length,
    eligible: eligibleCandidates.length,
    pendingRequests: requests.filter((request) => request.status === "PENDING").length
  };

  async function runAction(action, successMessage, refresh = true) {
    setError("");
    setFeedback("");
    try {
      await action();
      setFeedback(successMessage);
      if (refresh) {
        await loadBatches();
        await loadBatchContext(selectedBatch);
        await loadRequests();
      }
    } catch (actionError) {
      setError(actionError.message);
    }
  }

  function exportBatchData() {
    if (!selectedBatch) {
      return;
    }

    api.fetchCandidateExport(token, selectedBatch).then((csv) => {
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${selectedBatchRecord?.name ?? "batch"}-candidates.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }).catch((loadError) => setError(loadError.message));
  }

  return (
    <div className="dashboard-stack">
      <InlineAlert tone="danger" message={error} />
      <InlineAlert tone="success" message={feedback} />

      {section === "setup" ? (
        <div className="section-stack">
          <div className="hero-strip hero-strip--owner">
            <div>
              <div className="eyebrow">Batch Setup</div>
              <h2>{selectedBatchRecord?.name ?? "Assigned batches"}</h2>
              <p>Configure the assigned batch details and assign only candidates who belong to the relevant training phase.</p>
            </div>
            <div className="token-row">
              <StatusBadge tone="info">{selectedBatchRecord?.phase ?? "No batch selected"}</StatusBadge>
              <StatusBadge tone="neutral">{selectedBatchRecord?.year ?? "--"}</StatusBadge>
            </div>
          </div>

          <div className="metrics-row">
            <MetricCard label="Assigned batches" value={metrics.activeBatches} tone="accent" hint="Batches owned by you" />
            <MetricCard label="Current roster" value={metrics.roster} tone="success" hint="Candidates in selected batch" />
            <MetricCard label="Eligible pool" value={metrics.eligible} tone="warning" hint="Phase-matched candidates only" />
            <MetricCard label="Pending requests" value={metrics.pendingRequests} tone="default" hint="Awaiting L&D review" />
          </div>

          <SectionIntro
            eyebrow="Batch Setup"
            title="Configure the batch and assign phase candidates"
            description="This flow covers batch dates, technology stack, and candidate assignment limited to the current phase of the selected batch."
          />

          <div className="workspace-layout">
            <aside className="workspace-sidebar">
              <SectionCard title="Assigned batches" subtitle="Select the batch you want to configure.">
                <BatchPicker batches={batches} selectedBatch={selectedBatch} onSelect={setSelectedBatch} />
              </SectionCard>

              <SectionCard title="Eligible candidates" subtitle="Only candidates eligible for this batch phase can be assigned.">
                <div className="selection-list">
                  {eligibleCandidates.map((candidate) => {
                    const isSelected = candidateSelection.includes(candidate.id);
                    return (
                      <label className={`selection-card${isSelected ? " selection-card--active" : ""}`} key={candidate.id}>
                        <input
                          checked={isSelected}
                          type="checkbox"
                          onChange={(event) => {
                            setCandidateSelection((current) =>
                              event.target.checked
                                ? [...current, candidate.id]
                                : current.filter((id) => id !== candidate.id)
                            );
                          }}
                        />
                        <div>
                          <strong>{candidate.name}</strong>
                          <div className="muted">{candidate.email}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
                <button
                  className="button button--secondary"
                  disabled={!selectedBatch || !candidateSelection.length}
                  onClick={() =>
                    runAction(
                      () => api.assignEligibleCandidates(token, selectedBatch, { candidate_ids: candidateSelection }),
                      `${candidateSelection.length} candidate(s) assigned to the batch.`
                    ).then(() => setCandidateSelection([]))
                  }
                  type="button"
                >
                  Assign selected candidates
                </button>
              </SectionCard>
            </aside>

            <div className="workspace-main">
              <SectionCard title="Batch details" subtitle="Update start date, end date, and technology stack for the selected batch.">
                <div className="form-grid">
                  <label className="field">
                    <span>Start date</span>
                    <input type="date" value={configurationForm.start_date} onChange={(event) => setConfigurationForm((current) => ({ ...current, start_date: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>End date</span>
                    <input type="date" value={configurationForm.end_date} onChange={(event) => setConfigurationForm((current) => ({ ...current, end_date: event.target.value }))} />
                  </label>
                  <label className="field field--full">
                    <span>Tech stack</span>
                    <textarea rows="4" value={configurationForm.tech_stack} onChange={(event) => setConfigurationForm((current) => ({ ...current, tech_stack: event.target.value }))} />
                  </label>
                </div>
                <button
                  className="button button--primary"
                  disabled={!selectedBatch}
                  onClick={() =>
                    runAction(
                      () =>
                        api.updateBatchConfiguration(token, selectedBatch, {
                          start_date: configurationForm.start_date,
                          end_date: configurationForm.end_date,
                          tech_stack: configurationForm.tech_stack.split(",").map((item) => item.trim()).filter(Boolean)
                        }),
                      "Batch configuration updated successfully."
                    )
                  }
                  type="button"
                >
                  Save batch details
                </button>
              </SectionCard>
            </div>
          </div>
        </div>
      ) : null}

      {section === "my-batch" ? (
        <div className="section-stack">
          <ContextBar
            items={[
              { label: "Selected batch", value: selectedBatchRecord?.name ?? "--" },
              { label: "Phase", value: selectedBatchRecord?.phase ?? "--" },
              { label: "Duration", value: selectedBatchRecord ? `${formatDate(selectedBatchRecord.start_date)} to ${formatDate(selectedBatchRecord.end_date)}` : "--" },
              { label: "Tech stack", value: formatList(selectedBatchRecord?.tech_stack) }
            ]}
          />
          <SectionIntro
            eyebrow="My Batch"
            title="Work on the live batch roster"
            description="Use focused task views for roster review, marks update, employment details, and candidate timeline instead of handling everything in one screen."
            actions={
              <button className="button button--ghost" disabled={!selectedBatch} onClick={exportBatchData} type="button">
                Export batch data
              </button>
            }
          />

          <div className="workspace-layout">
            <aside className="workspace-sidebar">
              <SectionCard title="Assigned batches" subtitle="Choose which batch to inspect.">
                <BatchPicker batches={batches} selectedBatch={selectedBatch} onSelect={setSelectedBatch} />
              </SectionCard>
            </aside>

            <div className="workspace-main">
              <SegmentedTabs
                items={[
                  { value: "roster", label: "Roster", caption: "Candidate list and batch roster" },
                  { value: "marks", label: "Marks", caption: "Manual score updates" },
                  { value: "employment", label: "Employment", caption: "UID and employee email" },
                  { value: "timeline", label: "Timeline", caption: "Candidate audit trail" }
                ]}
                value={myBatchView}
                onChange={setMyBatchView}
              />

              {myBatchView === "roster" ? (
                <SectionCard title="Candidate roster" subtitle="Review candidates inside the selected batch without mixing update forms into the same view.">
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Candidate</th>
                          <th>Status</th>
                          <th>College</th>
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
                            <td>{candidate.college ?? "--"}</td>
                            <td>{candidate.tech_stack ?? "--"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!candidates.length ? <EmptyState title="No candidates assigned" description="Assigned candidates will appear here." /> : null}
                </SectionCard>
              ) : null}

              {myBatchView === "marks" ? (
                <SectionCard title="Manual marks update" subtitle="Edit candidate marks in a dedicated task view.">
                  <div className="form-grid form-grid--single">
                    <label className="field">
                      <span>Candidate</span>
                      <select value={marksForm.candidate_id} onChange={(event) => setMarksForm((current) => ({ ...current, candidate_id: event.target.value }))}>
                        <option value="">Select candidate</option>
                        {candidates.map((candidate) => (
                          <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Marks key</span>
                      <input value={marksForm.mark_key} onChange={(event) => setMarksForm((current) => ({ ...current, mark_key: event.target.value }))} placeholder="foundation_exam" />
                    </label>
                    <label className="field">
                      <span>Marks value</span>
                      <input type="number" value={marksForm.mark_value} onChange={(event) => setMarksForm((current) => ({ ...current, mark_value: event.target.value }))} />
                    </label>
                  </div>
                  <button
                    className="button button--primary"
                    disabled={!selectedBatch}
                    onClick={() =>
                      runAction(
                        () =>
                          api.updateCandidateMarks(token, selectedBatch, marksForm.candidate_id, {
                            marks: { [marksForm.mark_key]: Number(marksForm.mark_value) }
                          }),
                        "Candidate marks updated."
                      )
                    }
                    type="button"
                  >
                    Update marks
                  </button>
                </SectionCard>
              ) : null}

              {myBatchView === "employment" ? (
                <SectionCard title="Employment details" subtitle="Post-onboarding updates are separated from marks and roster work.">
                  <div className="form-grid form-grid--single">
                    <label className="field">
                      <span>Candidate</span>
                      <select value={employmentForm.candidate_id} onChange={(event) => setEmploymentForm((current) => ({ ...current, candidate_id: event.target.value }))}>
                        <option value="">Select candidate</option>
                        {candidates.map((candidate) => (
                          <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>UID</span>
                      <input value={employmentForm.uid} onChange={(event) => setEmploymentForm((current) => ({ ...current, uid: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Employee email</span>
                      <input type="email" value={employmentForm.employee_email} onChange={(event) => setEmploymentForm((current) => ({ ...current, employee_email: event.target.value }))} />
                    </label>
                  </div>
                  <button
                    className="button button--secondary"
                    disabled={!selectedBatch}
                    onClick={() =>
                      runAction(
                        () =>
                          api.updateCandidateEmploymentDetails(token, selectedBatch, employmentForm.candidate_id, {
                            uid: employmentForm.uid,
                            employee_email: employmentForm.employee_email
                          }),
                        "Employment details updated."
                      )
                    }
                    type="button"
                  >
                    Save employment details
                  </button>
                </SectionCard>
              ) : null}

              {myBatchView === "timeline" ? (
                <SectionCard title="Candidate timeline" subtitle="View the audit trail in its own dedicated screen.">
                  <div className="token-row">
                    {candidates.map((candidate) => (
                      <button
                        className="chip-button"
                        key={candidate.id}
                        onClick={async () => {
                          try {
                            const data = await api.fetchBatchOwnerCandidateTimeline(token, candidate.id);
                            setTimeline(data);
                          } catch (timelineError) {
                            setError(timelineError.message);
                          }
                        }}
                        type="button"
                      >
                        {candidate.name}
                      </button>
                    ))}
                  </div>
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
                  {!timeline.length ? <EmptyState title="Timeline not loaded" description="Select a candidate to view the full audit trail." /> : null}
                </SectionCard>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {section === "exams" ? (
        <div className="section-stack">
          <ContextBar
            items={[
              { label: "Selected batch", value: selectedBatchRecord?.name ?? "--" },
              { label: "Phase", value: selectedBatchRecord?.phase ?? "--" },
              { label: "Candidates", value: candidates.length },
              { label: "Exam results", value: examResults.length }
            ]}
          />
          <SectionIntro
            eyebrow="Exams"
            title="Record manual or bulk exam scores"
            description="Use separate exam task views for manual entry, bulk upload, and result review."
            actions={
              <button
                className="button button--ghost"
                onClick={async () => {
                  try {
                    const template = await api.fetchExamTemplate(token);
                    setExamTemplate(template);
                  } catch (templateError) {
                    setError(templateError.message);
                  }
                }}
                type="button"
              >
                View upload template
              </button>
            }
          />

          <div className="workspace-layout">
            <aside className="workspace-sidebar">
              <SectionCard title="Assigned batches" subtitle="Choose a batch to update exam scores.">
                <BatchPicker batches={batches} selectedBatch={selectedBatch} onSelect={setSelectedBatch} />
              </SectionCard>

              <SectionCard title="Bulk upload" subtitle="Upload batch exam results through the sample structure supported by the backend.">
                <div className="form-grid form-grid--single">
                  <label className="field">
                    <span>Exam file</span>
                    <input type="file" accept=".xlsx,.xls,.csv" onChange={(event) => setExamUploadFile(event.target.files?.[0] ?? null)} />
                  </label>
                </div>
                <button
                  className="button button--secondary"
                  disabled={!selectedBatch || !examUploadFile}
                  onClick={() => runAction(() => api.uploadExamResults(token, selectedBatch, examUploadFile), "Exam result file uploaded.")}
                  type="button"
                >
                  Upload exam file
                </button>
                {examTemplate ? (
                  <div className="empty-state">
                    <div className="empty-state__title">Template preview</div>
                    <pre>{examTemplate}</pre>
                  </div>
                ) : null}
              </SectionCard>
            </aside>

            <div className="workspace-main">
              <SegmentedTabs
                items={[
                  { value: "manual", label: "Manual Entry", caption: "Enter scores candidate by candidate" },
                  { value: "upload", label: "Bulk Upload", caption: "Upload exam sheet and template" },
                  { value: "results", label: "Result Ledger", caption: "Review recorded exam results" }
                ]}
                value={examView}
                onChange={setExamView}
              />

              {examView === "manual" ? (
                <SectionCard title="Manual exam entry" subtitle="Supports pre-onboarding and post-onboarding exam updates.">
                  <div className="form-grid">
                    <label className="field">
                      <span>Candidate</span>
                      <select value={examForm.candidate_id} onChange={(event) => setExamForm((current) => ({ ...current, candidate_id: event.target.value }))}>
                        <option value="">Select candidate</option>
                        {candidates.map((candidate) => (
                          <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Phase</span>
                      <select value={examForm.phase} onChange={(event) => setExamForm((current) => ({ ...current, phase: event.target.value }))}>
                        <option value="PRE_ONBOARDING">Pre Onboarding</option>
                        <option value="POST_ONBOARDING">Post Onboarding</option>
                      </select>
                    </label>
                    <label className="field">
                      <span>Exam type</span>
                      <select value={examForm.exam_type} onChange={(event) => setExamForm((current) => ({ ...current, exam_type: event.target.value }))}>
                        {["FOUNDATION_EXAM", "MODULE_EXAM", "ADVANCED_EXAM", "FINAL_EXAM", "CUSTOM_EXAM"].map((type) => (
                          <option key={type} value={type}>{formatEnum(type)}</option>
                        ))}
                      </select>
                    </label>
                    {examForm.exam_type === "CUSTOM_EXAM" ? (
                      <label className="field">
                        <span>Custom exam name</span>
                        <input value={examForm.custom_exam_name} onChange={(event) => setExamForm((current) => ({ ...current, custom_exam_name: event.target.value }))} />
                      </label>
                    ) : null}
                    <label className="field">
                      <span>Attempt</span>
                      <input type="number" min="1" max="2" value={examForm.attempt} onChange={(event) => setExamForm((current) => ({ ...current, attempt: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Score</span>
                      <input type="number" value={examForm.score} onChange={(event) => setExamForm((current) => ({ ...current, score: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Max score</span>
                      <input type="number" value={examForm.max_score} onChange={(event) => setExamForm((current) => ({ ...current, max_score: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Pass percentage</span>
                      <input type="number" value={examForm.pass_percentage} onChange={(event) => setExamForm((current) => ({ ...current, pass_percentage: event.target.value }))} />
                    </label>
                  </div>
                  <button
                    className="button button--primary"
                    disabled={!selectedBatch}
                    onClick={() =>
                      runAction(
                        () =>
                          api.recordExamResult(token, selectedBatch, {
                            ...examForm,
                            attempt: Number(examForm.attempt),
                            score: Number(examForm.score),
                            max_score: Number(examForm.max_score),
                            pass_percentage: Number(examForm.pass_percentage),
                            custom_exam_name: examForm.exam_type === "CUSTOM_EXAM" ? examForm.custom_exam_name : null
                          }),
                        "Exam score recorded."
                      )
                    }
                    type="button"
                  >
                    Save score
                  </button>
                </SectionCard>
              ) : null}

              {examView === "upload" ? (
                <SectionCard title="Bulk upload" subtitle="Upload exam sheets and review the template in a dedicated upload view.">
                  <div className="form-grid form-grid--single">
                    <label className="field">
                      <span>Exam file</span>
                      <input type="file" accept=".xlsx,.xls,.csv" onChange={(event) => setExamUploadFile(event.target.files?.[0] ?? null)} />
                    </label>
                  </div>
                  <button
                    className="button button--secondary"
                    disabled={!selectedBatch || !examUploadFile}
                    onClick={() => runAction(() => api.uploadExamResults(token, selectedBatch, examUploadFile), "Exam result file uploaded.")}
                    type="button"
                  >
                    Upload exam file
                  </button>
                  {examTemplate ? (
                    <div className="empty-state">
                      <div className="empty-state__title">Template preview</div>
                      <pre>{examTemplate}</pre>
                    </div>
                  ) : (
                    <EmptyState title="No template loaded" description="Use the header action to load the upload template." />
                  )}
                </SectionCard>
              ) : null}

              {examView === "results" ? (
                <SectionCard title="Exam result ledger" subtitle="Current exam history for the selected batch.">
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Exam</th>
                          <th>Candidate</th>
                          <th>Attempt</th>
                          <th>Score</th>
                          <th>Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {examResults.map((exam) => (
                          <tr key={exam.id}>
                            <td>
                              <div className="table-primary">{exam.exam_name}</div>
                              <div className="table-secondary">{formatEnum(exam.phase)}</div>
                            </td>
                            <td>{candidates.find((candidate) => candidate.id === exam.candidate_id)?.name ?? exam.candidate_id}</td>
                            <td>{exam.attempt}</td>
                            <td>{exam.score}/{exam.max_score}</td>
                            <td>
                              <StatusBadge tone={exam.passed ? "success" : "danger"}>{exam.passed ? "Passed" : "Failed"}</StatusBadge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!examResults.length ? <EmptyState title="No exam results found" description="Enter or upload exam scores to populate this ledger." /> : null}
                </SectionCard>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {section === "requests" ? (
        <div className="section-stack">
          <ContextBar
            items={[
              { label: "Selected batch", value: selectedBatchRecord?.name ?? "--" },
              { label: "Submitted requests", value: requests.length },
              { label: "Pending", value: metrics.pendingRequests },
              { label: "Role", value: "Batch Owner" }
            ]}
          />
          <SectionIntro
            eyebrow="Dropout / Resignation"
            title="Submit candidate dropout or resignation details"
            description="Keep request submission and request tracking in separate task views."
          />

          <div className="workspace-layout">
            <aside className="workspace-sidebar">
              <SectionCard title="Submit request" subtitle="Raise a dropout or resignation request for the selected batch.">
                <div className="form-grid form-grid--single">
                  <label className="field">
                    <span>Candidate email</span>
                    <input type="email" value={requestForm.candidate_email} onChange={(event) => setRequestForm((current) => ({ ...current, candidate_email: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Request type</span>
                    <select value={requestForm.request_type} onChange={(event) => setRequestForm((current) => ({ ...current, request_type: event.target.value }))}>
                      <option value="DROPOUT">Dropout</option>
                      <option value="RESIGNATION">Resignation</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>Reason</span>
                    <textarea rows="5" value={requestForm.reason} onChange={(event) => setRequestForm((current) => ({ ...current, reason: event.target.value }))} />
                  </label>
                </div>
                <button
                  className="button button--primary"
                  disabled={!selectedBatch}
                  onClick={() =>
                    runAction(
                      () => api.createChangeRequest(token, selectedBatch, requestForm),
                      "Request submitted successfully."
                    ).then(() => setRequestForm({ candidate_email: "", request_type: "DROPOUT", reason: "" }))
                  }
                  type="button"
                >
                  Send request
                </button>
              </SectionCard>
            </aside>

            <div className="workspace-main">
              <SegmentedTabs
                items={[
                  { value: "submit", label: "Submit Request", caption: "Raise a new dropout or resignation" },
                  { value: "register", label: "Request Register", caption: "Track submitted requests" }
                ]}
                value={requestView}
                onChange={setRequestView}
              />

              {requestView === "submit" ? (
                <SectionCard title="Submission guidance" subtitle="Use the left panel to create a request for the selected batch.">
                  <EmptyState title="Ready to submit" description="Fill the request form in the sidebar and submit it from this task view." />
                </SectionCard>
              ) : null}

              {requestView === "register" ? (
                <SectionCard title="Request register" subtitle="Status of requests you have submitted from your assigned batches.">
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Type</th>
                          <th>Candidate</th>
                          <th>Reason</th>
                          <th>Status</th>
                          <th>Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {requests.map((request) => (
                          <tr key={request.id}>
                            <td>{formatEnum(request.request_type)}</td>
                            <td>{request.candidate_email ?? "--"}</td>
                            <td>{request.reason}</td>
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
                  {!requests.length ? <EmptyState title="No requests submitted" description="Requests raised from this role will appear here." /> : null}
                </SectionCard>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
