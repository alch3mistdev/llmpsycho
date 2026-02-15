import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { getIngestionStatus, getMetaModels, listProfiles } from "../lib/api";

export function Dashboard() {
  const profilesQuery = useQuery({
    queryKey: ["profiles", "dashboard"],
    queryFn: () => listProfiles({ limit: 200 })
  });

  const ingestionQuery = useQuery({
    queryKey: ["ingestion", "status"],
    queryFn: getIngestionStatus,
    refetchInterval: 5000
  });

  const modelsQuery = useQuery({
    queryKey: ["meta", "models"],
    queryFn: getMetaModels
  });

  const stats = useMemo(() => {
    const items = profilesQuery.data?.profiles ?? [];
    const converged = items.filter((item) => item.converged).length;
    const overfit = items.filter((item) => item.risk_flags?.benchmark_overfit).length;
    const unstable = items.filter((item) => item.risk_flags?.instability).length;
    return {
      total: items.length,
      converged,
      overfit,
      unstable
    };
  }, [profilesQuery.data]);

  return (
    <section className="stack">
      <div className="hero-card">
        <h2>Profile Landscape</h2>
        <p>
          Monitor profiling health, ingestion, and model coverage. Launch runs from Run Studio or load imported
          profiles for intervention analysis.
        </p>
      </div>

      <div className="grid-4">
        <div className="metric-card">
          <h3>Total Profiles</h3>
          <strong>{stats.total}</strong>
        </div>
        <div className="metric-card">
          <h3>Converged</h3>
          <strong>{stats.converged}</strong>
        </div>
        <div className="metric-card">
          <h3>Overfit Flags</h3>
          <strong>{stats.overfit}</strong>
        </div>
        <div className="metric-card">
          <h3>Instability Flags</h3>
          <strong>{stats.unstable}</strong>
        </div>
      </div>

      <div className="grid-2">
        <article className="panel-card">
          <h3>Model Presets</h3>
          <ul className="flat-list">
            {(modelsQuery.data?.models ?? []).map((model, index) => (
              <li key={index}>
                <code>{String(model.provider)}</code> · <strong>{String(model.model_id)}</strong>
                <div className="hint">{String(model.available_hint ?? "")}</div>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel-card">
          <h3>Ingestion Watcher</h3>
          <div className="status-row">
            <span>Status</span>
            <strong>{ingestionQuery.data?.running ? "Running" : "Stopped"}</strong>
          </div>
          <div className="status-row">
            <span>Imported</span>
            <strong>{ingestionQuery.data?.imported_count ?? 0}</strong>
          </div>
          <div className="status-row">
            <span>Errors</span>
            <strong>{ingestionQuery.data?.error_count ?? 0}</strong>
          </div>
          <p className="hint">Last scan: {ingestionQuery.data?.last_scan_at ?? "n/a"}</p>
        </article>
      </div>

      <article className="panel-card">
        <h3>Recent Profiles</h3>
        {profilesQuery.isLoading && <p>Loading profiles...</p>}
        {profilesQuery.isError && <p className="error">Failed to load profiles.</p>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Profile</th>
                <th>Model</th>
                <th>Provider</th>
                <th>Converged</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {(profilesQuery.data?.profiles ?? []).slice(0, 8).map((profile) => (
                <tr key={profile.profile_id}>
                  <td>{profile.profile_id}</td>
                  <td>{profile.model_id}</td>
                  <td>{profile.provider}</td>
                  <td>{profile.converged ? "Yes" : "No"}</td>
                  <td>{new Date(profile.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
