// src/api.js
import axios from "axios";

export const BASE = process.env.REACT_APP_BACKEND_URL;
export const API = axios.create({
  baseURL: `${BASE}/api`,
});

// attach token to every request if present
API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token"); // we store it after login
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ---- Auth calls ----
export async function login(email, password) {
  // FastAPI login expects form-encoded
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);

  const { data } = await axios.post(`${BASE}/api/auth/login`, body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  // data: { access_token, token_type, expires_in }
  localStorage.setItem("token", data.access_token);
  return data;
}

export function logout() {
  localStorage.removeItem("token");
}

// ---- App data calls (now auto-send token) ----
export const getProfile = async () => (await API.get("/profile")).data;
export const upsertProfile = async (payload) => (await API.post("/profile", payload)).data;
export const updateProfile = async (payload) => (await API.put("/profile", payload)).data;

export const getMembers = async (params={}) => (await API.get("/members", { params })).data;
export const createMember = async (payload) => (await API.post("/members", payload)).data;
export const updateMember = async (id, payload) => (await API.put(`/members/${id}`, payload)).data;
export const deleteMember = async (id) => (await API.delete(`/members/${id}`)).data;

export const getPayments = async (params={}) => (await API.get("/payments", { params })).data;
export const recordPayment = async (payload) => (await API.post("/payments", payload)).data;

export const getAttendance = async (params={}) => (await API.get("/attendance", { params })).data;
export const checkIn = async (payload) => (await API.post("/attendance/checkin", payload)).data;
export const checkOut = async (memberId) => (await API.post(`/attendance/checkout/${memberId}`)).data;
