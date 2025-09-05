import React, { useState } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = `${BACKEND_URL}/api`;

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [gymName, setGymName] = useState("");
  const [msg, setMsg] = useState("");
  const [link, setLink] = useState(""); // dev only

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");
    setLink("");
    try {
      const { data } = await axios.post(`${API}/auth/request-reset`, {
        email,
        gym_name: gymName,
      });
      setMsg("If the account exists, a reset email has been sent.");
      if (data?.reset_url) setLink(data.reset_url); // dev helper
    } catch {
      setMsg("If the account exists, a reset email has been sent.");
    }
  };

  return (
    <div style={wrap}>
      <form onSubmit={submit} style={card}>
        <h2>Forgot password</h2>
        <input style={inp} placeholder="Gym name" value={gymName} onChange={e=>setGymName(e.target.value)} />
        <input style={inp} placeholder="Email" type="email" value={email} onChange={e=>setEmail(e.target.value)} />
        <button style={btn}>Send reset link</button>
        {!!msg && <p style={{marginTop:8}}>{msg}</p>}
        {!!link && <p style={{fontSize:12, wordBreak:"break-all"}}>Dev link: <a href={link}>{link}</a></p>}
      </form>
    </div>
  );
}
const wrap={minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:"#f3f6f9"};
const card={width:360,background:"#fff",padding:20,borderRadius:12,boxShadow:"0 8px 24px rgba(0,0,0,.06)",display:"grid",gap:10};
const inp={height:44,border:"1px solid #e5e7eb",borderRadius:8,padding:"0 12px"};
const btn={height:44,border:0,borderRadius:8,background:"#2563eb",color:"#fff",fontWeight:600,cursor:"pointer"};
