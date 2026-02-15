import { NavLink, Route, Routes } from "react-router-dom";

import { Dashboard } from "./pages/Dashboard";
import { IngestionCenter } from "./pages/IngestionCenter";
import { ProfileExplorer } from "./pages/ProfileExplorer";
import { QueryLab } from "./pages/QueryLab";
import { RunStudio } from "./pages/RunStudio";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/runs", label: "Run Studio" },
  { to: "/profiles", label: "Profile Explorer" },
  { to: "/query-lab", label: "Query Lab" },
  { to: "/ingestion", label: "Ingestion" }
];

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <h1>LLMPsycho Profile Studio</h1>
          <p>Interactive profiling, analysis, and profile-applied query optimization.</p>
        </div>
        <nav className="nav-tabs">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "nav-tab active" : "nav-tab")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="page-shell">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<RunStudio />} />
          <Route path="/profiles" element={<ProfileExplorer />} />
          <Route path="/query-lab" element={<QueryLab />} />
          <Route path="/ingestion" element={<IngestionCenter />} />
        </Routes>
      </main>
    </div>
  );
}
