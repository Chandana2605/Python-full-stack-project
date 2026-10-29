const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8080/api/v1";

async function request(path, { method = "GET", token, body, headers, isFormData = false } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      ...(!isFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers ?? {})
    },
    body: body
      ? isFormData
        ? body
        : JSON.stringify(body)
      : undefined
  });

  if (!response.ok) {
    let message = "Request failed";

    try {
      const error = await response.json();
      message = error.detail ?? message;
    } catch {
      message = response.statusText || message;
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/plain")) {
    return response.text();
  }

  return response.json();
}

function buildQuery(params = {}) {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, value);
    }
  });

  const query = search.toString();
  return query ? `?${query}` : "";
}

function createFilePayload(file) {
  const formData = new FormData();
  formData.append("file", file);
  return formData;
}

export const api = {
  login: (body) => request("/auth/login", { method: "POST", body }),
  changePassword: (token, body) => request("/auth/change-password", { method: "POST", token, body }),

  uploadMasterCandidates: (token, file) =>
    request("/lnd-manager/candidates/upload", {
      method: "POST",
      token,
      body: createFilePayload(file),
      isFormData: true
    }),
  searchMasterCandidates: (token, params = {}) =>
    request(`/lnd-manager/search-candidates${buildQuery(params)}`, { token }),
  uploadBaseline: (token, file) =>
    request("/lnd-manager/exams/baseline-upload", {
      method: "POST",
      token,
      body: createFilePayload(file),
      isFormData: true
    }),
  resolveBaseline: (token, body) =>
    request("/lnd-manager/exams/baseline/resolve", { method: "POST", token, body }),
  uploadKnowledgeCheck: (token, file) =>
    request("/lnd-manager/exams/knowledge-check", {
      method: "POST",
      token,
      body: createFilePayload(file),
      isFormData: true
    }),

  fetchYearGrid: (token, referenceYear) =>
    request(`/lnd-manager/batches/year-grid${buildQuery({ reference_year: referenceYear })}`, { token }),
  fetchYearPhases: (token, year, referenceYear) =>
    request(`/lnd-manager/batches/years/${year}/phases${buildQuery({ reference_year: referenceYear })}`, { token }),
  createPhaseCard: (token, year, body) =>
    request(`/lnd-manager/batches/years/${year}/phase-cards`, { method: "POST", token, body }),
  fetchPhaseCard: (token, year, phase) =>
    request(`/lnd-manager/batches/years/${year}/phase-cards/${encodeURIComponent(phase)}`, { token }),
  importPhaseCandidates: (token, year, phase, body) =>
    request(`/lnd-manager/batches/years/${year}/phases/${encodeURIComponent(phase)}/candidates/import-emails`, {
      method: "POST",
      token,
      body
    }),
  fetchPhaseCandidates: (token, year, phase, params = {}) =>
    request(`/lnd-manager/batches/years/${year}/phases/${encodeURIComponent(phase)}/candidates${buildQuery(params)}`, { token }),
  fetchAssignableOwners: (token) => request("/lnd-manager/batches/assignable-owners", { token }),
  createPhaseBatch: (token, year, phase, body) =>
    request(`/lnd-manager/batches/years/${year}/phases/${encodeURIComponent(phase)}/batches`, {
      method: "POST",
      token,
      body
    }),
  assignBatchOwner: (token, batchId, body) =>
    request(`/lnd-manager/batches/${batchId}/owner`, { method: "PATCH", token, body }),
  assignBatchCandidates: (token, batchId, body) =>
    request(`/lnd-manager/batches/${batchId}/candidates/assign-emails`, { method: "POST", token, body }),
  fetchYearArchives: (token, referenceYear) =>
    request(`/lnd-manager/year-archives${buildQuery({ reference_year: referenceYear })}`, { token }),
  fetchYearArchiveDetails: (token, year, params = {}) =>
    request(`/lnd-manager/year-archives/${year}${buildQuery(params)}`, { token }),
  fetchCandidateTimeline: (token, batchId, candidateId) =>
    request(`/lnd-manager/batches/${batchId}/candidates/${candidateId}/timeline`, { token }),
  createRuleChangeRequest: (token, body) =>
    request("/lnd-manager/configuration/rule-change-requests", { method: "POST", token, body }),
  fetchLndUsers: (token, role = "") =>
    request(`/lnd-manager/users${buildQuery({ role })}`, { token }),
  createPlatformUser: (token, body) =>
    request("/lnd-manager/users", { method: "POST", token, body }),
  fetchLndChangeRequests: (token, status = "") =>
    request(`/lnd-manager/dropout-resignation-requests${buildQuery({ status })}`, { token }),
  reviewLndChangeRequest: (token, requestId, body) =>
    request(`/lnd-manager/dropout-resignation-requests/${requestId}/review`, {
      method: "PATCH",
      token,
      body
    }),

  fetchAssignedBatches: (token) => request("/batch-owner/assigned-batches", { token }),
  updateBatchConfiguration: (token, batchId, body) =>
    request(`/batch-owner/assigned-batches/${batchId}/configuration`, {
      method: "PATCH",
      token,
      body
    }),
  fetchEligibleCandidates: (token, batchId, params = {}) =>
    request(`/batch-owner/assigned-batches/${batchId}/eligible-candidates${buildQuery(params)}`, { token }),
  assignEligibleCandidates: (token, batchId, body) =>
    request(`/batch-owner/assigned-batches/${batchId}/eligible-candidates`, {
      method: "POST",
      token,
      body
    }),
  fetchAssignedBatchCandidates: (token, batchId, params = {}) =>
    request(`/batch-owner/assigned-batches/${batchId}/candidates${buildQuery(params)}`, { token }),
  fetchCandidateExport: (token, batchId, params = {}) =>
    request(`/batch-owner/assigned-batches/${batchId}/candidate-export${buildQuery(params)}`, { token }),
  fetchBatchOwnerCandidateTimeline: (token, candidateId) =>
    request(`/batch-owner/candidates/${candidateId}/timeline`, { token }),
  updateCandidateMarks: (token, batchId, candidateId, body) =>
    request(`/batch-owner/assigned-batches/${batchId}/candidates/${candidateId}/manual-marks`, {
      method: "PATCH",
      token,
      body
    }),
  updateCandidateEmploymentDetails: (token, batchId, candidateId, body) =>
    request(`/batch-owner/assigned-batches/${batchId}/candidates/${candidateId}/employment-details`, {
      method: "PATCH",
      token,
      body
    }),
  recordExamResult: (token, batchId, body) =>
    request(`/batch-owner/assigned-batches/${batchId}/exam-results`, {
      method: "POST",
      token,
      body
    }),
  uploadExamResults: (token, batchId, file) =>
    request(`/batch-owner/assigned-batches/${batchId}/exam-results/excel-upload`, {
      method: "POST",
      token,
      body: createFilePayload(file),
      isFormData: true
    }),
  fetchExamTemplate: (token) =>
    request("/batch-owner/assigned-batches/exam-results/template", { token }),
  fetchExamResults: (token, batchId) =>
    request(`/batch-owner/assigned-batches/${batchId}/exam-results`, { token }),
  createChangeRequest: (token, batchId, body) =>
    request(`/batch-owner/assigned-batches/${batchId}/dropout-resignation-requests`, {
      method: "POST",
      token,
      body
    }),
  fetchOwnerChangeRequests: (token, status = "") =>
    request(`/batch-owner/dropout-resignation-requests${buildQuery({ status })}`, { token }),

  fetchProgramBatches: (token) => request("/program-manager/assigned-program-batches", { token }),
  fetchProgramBatchCandidates: (token, batchId) =>
    request(`/program-manager/assigned-program-batches/${batchId}/candidates`, { token }),
  fetchProgramRuleRequests: (token, status = "") =>
    request(`/program-manager/configuration/rule-change-requests${buildQuery({ status })}`, { token })
};
