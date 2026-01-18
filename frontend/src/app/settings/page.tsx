"use client";

import { useState } from "react";

import { getApiBaseUrl, getApiKey, setApiBaseUrl, setApiKey } from "../../lib/api";

const SettingsPage = () => {
  const [baseUrl, setBaseUrl] = useState(getApiBaseUrl());
  const [apiKey, updateApiKey] = useState(getApiKey());
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setApiBaseUrl(baseUrl);
    setApiKey(apiKey);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="content fade-in">
      <section className="card">
        <h2 className="section-title">Settings</h2>
        <p className="muted">
          API base URL and API key live only in memory. Reloading clears them.
        </p>
        <div className="grid" style={{ gap: 12, marginTop: 16 }}>
          <input
            placeholder="http://127.0.0.1:8000"
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
          />
          <input
            placeholder="API key"
            value={apiKey}
            onChange={(event) => updateApiKey(event.target.value)}
            type="password"
          />
          <button className="btn btn-primary" onClick={handleSave}>
            Save settings
          </button>
          {saved ? <span className="muted">Saved.</span> : null}
        </div>
      </section>
    </div>
  );
};

export default SettingsPage;
