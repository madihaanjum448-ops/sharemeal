import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import DonorPostForm from "./DonorPostForm";

function DonorHome() {
  const { profile } = useAuth();

  return (
    <div className="page-container">
      {/* Donor Welcome & Banner */}
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "20px" }}>
        <div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "var(--emerald-50)", color: "var(--primary)", padding: "4px 12px", borderRadius: "var(--radius-pill)", fontSize: "12px", fontWeight: 700, marginBottom: "8px", border: "1px solid var(--emerald-100)" }}>
            <span>🌱 Donor Portal</span>
          </div>
          <h1>Welcome, {profile?.full_name || "Food Donor"}!</h1>
          <p>
            Share fresh surplus food with verified receivers in your area. Every donation diverts waste and supports community wellbeing.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <Link to="/donor/posts" className="btn-secondary btn-sm" style={{ padding: "8px 16px" }}>
            📋 View My Posts
          </Link>
          <Link to="/donor/profile" className="btn-secondary btn-sm" style={{ padding: "8px 16px" }}>
            👤 Profile
          </Link>
        </div>
      </div>

      {/* Donor Quick Tips Strip */}
      <div
        style={{
          background: "#ffffff",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "16px 20px",
          marginBottom: "28px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "16px",
          boxShadow: "var(--shadow-card)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--emerald-100)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", flexShrink: 0 }}>
            ⏰
          </div>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--emerald-900)" }}>Safe-Until Freshness</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Set a realistic time for safe pickup</div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--emerald-100)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", flexShrink: 0 }}>
            🛡️
          </div>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--emerald-900)" }}>Donor Privacy</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Address unlocks only after a claim</div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--emerald-100)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", flexShrink: 0 }}>
            🧼
          </div>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--emerald-900)" }}>4-Point Hygiene</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Verify safe prep &amp; clean packaging</div>
          </div>
        </div>
      </div>

      <DonorPostForm />
    </div>
  );
}

export default DonorHome;
