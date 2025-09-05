// src/index.js
import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import App from "./App";
import ErrorBoundary from "./ErrorBoundary";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";

const container = document.getElementById("root");
if (!container) {
  throw new Error('Root element "#root" not found');
}

const root = createRoot(container);

const Root = () => (
  <ErrorBoundary>
    <BrowserRouter>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </ErrorBoundary>
);

// Use StrictMode only in development to avoid double effects in production
if (process.env.NODE_ENV === "development") {
  root.render(
    <React.StrictMode>
      <Root />
    </React.StrictMode>
  );
} else {
  root.render(<Root />);
}

// Helpful: surface unhandled promise rejections in the console
window.addEventListener("unhandledrejection", (evt) => {
  console.error("Unhandled promise rejection:", evt.reason);
});
