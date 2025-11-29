// frontend/src/utils/api.js
const API_URL = "http://127.0.0.1:5000/api";

export async function apiFetchSchedules() {
  const res = await fetch(`${API_URL}/list`);
  if (!res.ok) throw new Error("Failed to fetch schedules");
  return res.json();
}

export async function apiUploadInformasi(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function apiUploadRosterPreview(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/upload-roster-preview`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload roster preview failed");
  return res.json();
}

export async function apiSaveRoster(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/save-roster`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Save roster failed");
  return res.json();
}

export async function apiUploadAttendancePreview(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/upload-attendance-preview`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload attendance preview failed");
  return res.json();
}

export async function apiSaveAttendance(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/save-attendance`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Save attendance failed");
  return res.json();
}

export async function apiRunCroscek() {
  const res = await fetch(`${API_URL}/croscek`);
  if (!res.ok) throw new Error("Croscek failed");
  return res.json();
}
