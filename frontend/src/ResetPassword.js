import React, { useState, useMemo } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = `${BACKEND_URL}/api`;

export default function ResetPassword() {
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token") || "", []);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");
    if (password.length < 8) { setMsg("Use at least 8 characters."); return; }
    if (password !== confirm) { setMsg("Passwords do not match."); return; }

    try {
      await axios.post(`${API}/auth/reset`, { token, new_password: password });
      setMsg("Password updated. You can now sign in.");
      setTimeout(() => (window.location.href = "/"), 1200);
    } catch {
      setMsg("Reset failed. The link may be expired.");
    }
  };

  if (!token) return <div style={wrap}><div style={card}>Missing token.</div></div>;

  return (
    <div style={wrap}>
      <form onSubmit={submit} style={card}>
        <h2>Set a new password</h2>
        <input style={inp} type="password" placeholder="New password" value={password} onChange={e=>setPassword(e.target.value)} />
        <input style={inp} type="password" placeholder="Confirm password" value={confirm} onChange={e=>setConfirm(e.target.value)} />
        <button style={btn}>Update password</button>
        {!!msg && <p style={{marginTop:8}}>{msg}</p>}
      </form>
    </div>
  );
}
const wrap={minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:"#f3f6f9"};
const card={width:360,background:"#fff",padding:20,borderRadius:12,boxShadow:"0 8px 24px rgba(0,0,0,.06)",display:"grid",gap:10};
const inp={height:44,border:"1px solid #e5e7eb",borderRadius:8,padding:"0 12px"};
const btn={height:44,border:0,borderRadius:8,background:"#2563eb",color:"#fff",fontWeight:600,cursor:"pointer"};
