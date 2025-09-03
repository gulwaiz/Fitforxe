// src/Login.js
import React, { useState } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Login({ onSuccess }) {
  const [gymName, setGymName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const toMessage = (e) => {
    // normalize ANY error to a readable string
    const msg =
      e?.response?.data?.detail ??
      e?.response?.data?.message ??
      e?.message ??
      e ??
      "Incorrect gym name, email, or password";
    return typeof msg === "string" ? msg : JSON.stringify(msg);
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      // Your FastAPI login (server.py) expects JSON: { gym_name, email, password }
      const { data } = await axios.post(`${API}/auth/login`, {
        gym_name: gymName.trim(),   // keep if your backend requires it
        email: email.trim(),
        password,
      });

      // Save token for subsequent requests
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("gym_name", gymName.trim());
      axios.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;

      onSuccess?.(); // tell App we’re logged in
    } catch (e) {
      setErr(toMessage(e));  // <-- CRITICAL: always a string
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f3f6f9",
        padding: "24px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          background: "#fff",
          borderRadius: 12,
          boxShadow: "0 10px 30px rgba(0,0,0,0.06)",
          padding: 24,
        }}
      >
        <h2 style={{ marginBottom: 16, fontWeight: 700, textAlign: "center" }}>
          Sign in to Fitforxe
        </h2>

        <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
          {/* If your backend does NOT need gym_name, you can remove this input */}
          <input
            placeholder="Gym Name"
            value={gymName}
            onChange={(e) => setGymName(e.target.value)}
            autoCapitalize="none"
            style={inputStyle}
          />
          <input
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoCapitalize="none"
            style={inputStyle}
          />
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={inputStyle}
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              height: 44,
              borderRadius: 8,
              border: 0,
              background: loading ? "#93c5fd" : "#2563eb",
              color: "#fff",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "background .2s",
            }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>

          {!!err && (
            <div style={{ color: "#b91c1c", fontSize: 14, textAlign: "center", wordBreak: "break-word" }}>
              {String(err)}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

const inputStyle = {
  height: 44,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  padding: "0 12px",
  outline: "none",
};
