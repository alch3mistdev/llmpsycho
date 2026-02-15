import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { GuidedTourController } from "./components/GuidedTourController";
import { Dashboard } from "./pages/Dashboard";
import { IngestionCenter } from "./pages/IngestionCenter";
import { ProfileExplorer } from "./pages/ProfileExplorer";
import { QueryLab } from "./pages/QueryLab";
import { RunStudio } from "./pages/RunStudio";
import { useStudioStore } from "./store/useStudioStore";
import type { ExplanationMode } from "./lib/types";

const links = [
  { to: "/", label: "Mission Control", tour: "mission-control" },
  { to: "/runs", label: "Profiler Lab", tour: "run-studio" },
  { to: "/profiles", label: "Profile Anatomy", tour: "profile-anatomy" },
  { to: "/query-lab", label: "Intervention Simulator", tour: "query-lab" },
  { to: "/ingestion", label: "Artifact Intake", tour: "artifact-intake" }
];

const explanationModes: ExplanationMode[] = ["Simple", "Guided", "Technical"];

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { explanationMode, setExplanationMode, pinnedTooltip, setPinnedTooltip } = useStudioStore();
  const [commandOpen, setCommandOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKeydown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen((prev) => !prev);
      }
      if (event.key === "Escape") {
        setCommandOpen(false);
      }
    };
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, []);

  const commandLinks = useMemo(
    () => [
      ...links,
      { to: "/profiles?tab=How%20It%20Works", label: "How Profiling Works", tour: "how-it-works" }
    ],
    []
  );

  const filtered = commandLinks.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="app-shell">
      <GuidedTourController />
      <header className="topbar">
        <div className="brand-block">
          <h1>LLMPsycho Operations Cockpit</h1>
          <p>Probe -&gt; Score -&gt; Trait Shift -&gt; Intervention Impact</p>
        </div>

        <div className="mode-bar" aria-label="Explanation mode">
          <span>Explanation Mode</span>
          <div className="mode-switch" role="group" aria-label="Explanation mode selector">
            {explanationModes.map((mode) => (
              <button
                key={mode}
                type="button"
                className={mode === explanationMode ? "mode-chip active" : "mode-chip"}
                onClick={() => setExplanationMode(mode)}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="inline-actions">
          <button type="button" onClick={() => setCommandOpen(true)}>
            Command Search
          </button>
          <button
            type="button"
            data-tour="help-launcher"
            onClick={() => window.dispatchEvent(new Event("studio:start-tour"))}
          >
            Guided TLDR Tour
          </button>
          <button type="button" onClick={() => navigate("/profiles?tab=How%20It%20Works")}>
            How Profiling Works
          </button>
        </div>

        <nav className="nav-tabs" data-tour="navigation">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "nav-tab active" : "nav-tab")}
              data-tour={link.tour}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>

      {pinnedTooltip && (
        <aside className="pinned-tooltip">
          <div className="pinned-tooltip-head">
            <strong>{pinnedTooltip.title}</strong>
            <button type="button" onClick={() => setPinnedTooltip(null)}>
              Dismiss
            </button>
          </div>
          <pre>{pinnedTooltip.content}</pre>
        </aside>
      )}

      <AnimatePresence mode="wait">
        <motion.main
          key={location.pathname + location.search}
          className="page-shell view-transition-root"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <Routes location={location}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/runs" element={<RunStudio />} />
            <Route path="/profiles" element={<ProfileExplorer />} />
            <Route path="/query-lab" element={<QueryLab />} />
            <Route path="/ingestion" element={<IngestionCenter />} />
          </Routes>
        </motion.main>
      </AnimatePresence>

      {commandOpen && (
        <div className="command-overlay" role="dialog" aria-modal="true">
          <div className="command-panel">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Jump to surface..."
              autoFocus
            />
            <div className="command-list">
              {filtered.map((item) => (
                <button
                  key={item.to}
                  type="button"
                  onClick={() => {
                    navigate(item.to);
                    setCommandOpen(false);
                    setQuery("");
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
