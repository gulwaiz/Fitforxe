// src/Dashboard.js
import React from "react";

export default function Dashboard() {
  return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <h1>Welcome to your Dashboard</h1>
      <p>You're logged in as: <strong>{localStorage.getItem("gym_name")}</strong></p>
    </div>
  );
}
