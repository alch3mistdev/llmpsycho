import { ChangeEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getIngestionStatus, importProfile, scanIngestion } from "../lib/api";

export function IngestionCenter() {
  const [message, setMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const statusQuery = useQuery({
    queryKey: ["ingestion", "status"],
    queryFn: getIngestionStatus,
    refetchInterval: 5000
  });

  const scanMutation = useMutation({
    mutationFn: scanIngestion,
    onSuccess: (result) => {
      setMessage(`Scanned ${result.scanned} file(s).`);
      queryClient.invalidateQueries({ queryKey: ["ingestion", "status"] });
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
    onError: (error) => setMessage(String(error))
  });

  const importMutation = useMutation({
    mutationFn: importProfile,
    onSuccess: (result) => {
      setMessage(`Imported profile ${result.profile_id} (${result.status}).`);
      queryClient.invalidateQueries({ queryKey: ["ingestion", "status"] });
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
    onError: (error) => setMessage(String(error))
  });

  const onUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    importMutation.mutate(file);
    event.target.value = "";
  };

  return (
    <section className="stack" data-tour="artifact-intake">
      <div className="hero-card">
        <h2>Artifact Intake</h2>
        <p>Monitor watched folder sync, trigger manual scans, and upload profile JSON files directly.</p>
      </div>

      <div className="grid-3">
        <div className="metric-card">
          <h3>Watcher</h3>
          <strong>{statusQuery.data?.running ? "Running" : "Stopped"}</strong>
        </div>
        <div className="metric-card">
          <h3>Imported</h3>
          <strong>{statusQuery.data?.imported_count ?? 0}</strong>
        </div>
        <div className="metric-card">
          <h3>Errors</h3>
          <strong>{statusQuery.data?.error_count ?? 0}</strong>
        </div>
      </div>

      <div className="panel-card inline-actions">
        <button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
          {scanMutation.isPending ? "Scanning..." : "Scan Ingestion Folder"}
        </button>
        <label className="upload-button">
          Upload Profile JSON
          <input type="file" accept="application/json" onChange={onUpload} />
        </label>
        {message && <p className="hint">{message}</p>}
      </div>

      <article className="panel-card">
        <h3>Recent Ingestion Events</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Path</th>
                <th>Profile ID</th>
                <th>Updated</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {(statusQuery.data?.recent ?? []).map((row, index) => (
                <tr key={index}>
                  <td>{String(row.status ?? "")}</td>
                  <td>{String(row.path ?? "")}</td>
                  <td>{String(row.profile_id ?? "")}</td>
                  <td>{String(row.updated_at ?? "")}</td>
                  <td>{String(row.error_text ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
