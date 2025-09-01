// src/Login.js
import React, { useState } from "react";
import { login } from "./api";

export default function Login({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await login(email, password);
      onSuccess();
    } catch (e) {
      setErr("Incorrect email or password");
    }
  };

  return (
    <div style={{ maxWidth: 380, margin: "60px auto" }}>
      <h2>Owner Login</h2>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <input placeholder="Email" type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required />
        <input placeholder="Password" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required />
        <button type="submit">Log In</button>
        {err && <div style={{ color: "crimson" }}>{err}</div>}
      </form>
    </div>
  );
}
