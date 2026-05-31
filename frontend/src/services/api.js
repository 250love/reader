import axios from "axios";
import { clearAuth, getToken } from "./auth";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api/v1",
  timeout: 15000
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuth();
      if (window.location.pathname !== "/auth") {
        window.location.href = "/auth";
      }
    }
    return Promise.reject(error);
  }
);

export async function sendRegisterCode(payload) {
  const { data } = await api.post("/auth/send-code", payload);
  return data;
}

export async function register(payload) {
  const { data } = await api.post("/auth/register", payload);
  return data;
}

export async function login(payload) {
  const { data } = await api.post("/auth/login", payload);
  return data;
}

export async function recommendPassword(payload) {
  const { data } = await api.post("/auth/recommend-password", payload);
  return data;
}

export async function fetchMe() {
  const { data } = await api.get("/auth/me");
  return data.user;
}

export async function fetchPapers(params = {}) {
  const { data } = await api.get("/papers", { params });
  return data.items || [];
}

export async function createPaper(payload) {
  const { data } = await api.post("/papers", payload);
  return data;
}

export async function updatePaper(id, payload) {
  const { data } = await api.patch(`/papers/${id}`, payload);
  return data;
}

export async function deletePaper(id) {
  const { data } = await api.delete(`/papers/${id}`);
  return data;
}

export async function uploadPaperPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/papers/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
  return data;
}

export async function fetchPaperById(id) {
  const { data } = await api.get(`/papers/${id}`);
  return data;
}

export async function generatePaperCitations(payload) {
  const { data } = await api.post("/papers/citations", payload);
  return data;
}

export async function fetchPaperCitationMetadata(id) {
  const { data } = await api.get(`/papers/${id}/citation-metadata`);
  return data.citationMetadata || {};
}

export async function extractPaperCitationMetadata(id) {
  const { data } = await api.post(`/papers/${id}/citation-metadata/extract`);
  return data.citationMetadata || {};
}

export async function updatePaperCitationMetadata(id, citationMetadata) {
  const { data } = await api.patch(`/papers/${id}/citation-metadata`, { citationMetadata });
  return data.citationMetadata || {};
}

export async function markPaperOpened(id) {
  const { data } = await api.post(`/papers/${id}/open`);
  return data;
}

export async function translateSelection(paperId, payload) {
  const { data } = await api.post(`/papers/${paperId}/translate-selection`, payload);
  return data;
}

export async function extractPaperFigures(paperId, payload = { force: true }) {
  const { data } = await api.post(`/papers/${paperId}/figures/extract`, payload);
  return data;
}

export async function fetchPaperFigures(paperId) {
  const { data } = await api.get(`/papers/${paperId}/figures`);
  return data.items || [];
}

export async function updatePaperFigure(paperId, figureId, payload) {
  const { data } = await api.patch(`/papers/${paperId}/figures/${figureId}`, payload);
  return data;
}

export async function fetchPaperAnnotations(paperId) {
  const { data } = await api.get(`/papers/${paperId}/annotations`);
  return data.items || [];
}

export async function createPaperAnnotation(paperId, payload) {
  const { data } = await api.post(`/papers/${paperId}/annotations`, payload);
  return data;
}

export async function updatePaperAnnotation(paperId, annotationId, payload) {
  const { data } = await api.patch(`/papers/${paperId}/annotations/${annotationId}`, payload);
  return data;
}

export async function deletePaperAnnotation(paperId, annotationId) {
  const { data } = await api.delete(`/papers/${paperId}/annotations/${annotationId}`);
  return data;
}

export async function fetchFolders() {
  const { data } = await api.get("/folders");
  return data.items || [];
}

export async function createFolder(payload) {
  const { data } = await api.post("/folders", payload);
  return data;
}

export async function updateFolder(id, payload) {
  const { data } = await api.patch(`/folders/${id}`, payload);
  return data;
}

export async function deleteFolder(id) {
  const { data } = await api.delete(`/folders/${id}`);
  return data;
}

export async function fetchProviders() {
  const { data } = await api.get("/providers");
  return data.items || [];
}

export async function createProvider(payload) {
  const { data } = await api.post("/providers", payload);
  return data;
}

export default api;
