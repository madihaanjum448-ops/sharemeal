import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function ReceiverProfile() {
  const { profile, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const formatDate = (isoString) => {
    if (!isoString) return "N/A";
    try {
      return new Date(isoString).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return isoString;
    }
  };

  const status = profile?.approval_status || "pending";
  const initial = (profile?.full_name || user?.email || "R")[0].toUpperCase();

  return (
    <div className="page-container" style={{ maxWidth: "760px" }}>
      <div className="page-header">
        <h1>Receiver Profile</h1>
        <p>Manage your receiver organization account and administrative approval status.</p>
      </div>

      <div className="card" style={{ padding: "36px" }}>
        {/* Profile Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "28px" }}>
          <div
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "var(--emerald-100)",
              color: "var(--emerald-900)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "28px",
              fontWeight: 800,
              boxShadow: "0 0 0 4px var(--emerald-50)",
              flexShrink: 0,
            }}
          >
            {initial}
          </div>
          <div>
            <h2 style={{ margin: "0 0 6px 0", fontSize: "22px", color: "var(--emerald-900)" }}>
              {profile?.full_name || "Food Receiver"}
            </h2>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <span className={`badge badge-${status}`}>
                Status: {status}
              </span>
              {profile?.is_verified && (
                <span className="badge badge-active">✓ Verified Receiver</span>
              )}
            </div>
          </div>
        </div>

        {/* Account Details */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "20px",
            borderTop: "1px solid var(--border-subtle)",
            paddingTop: "24px",
            marginBottom: "28px",
          }}
        >
          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Full Name</label>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
              {profile?.full_name || "Not specified"}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Email Address</label>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
              {user?.email || "Not specified"}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Organization</label>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
              {profile?.organization_name || "Independent Receiver"}
            </div>
          </div>

          {profile?.phone && (
            <div>
              <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Phone Number</label>
              <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>{profile.phone}</div>
            </div>
          )}

          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "4px" }}>
              Verification &amp; Approval Status
            </label>
            <div
              style={{
                fontSize: "14px",
                padding: "12px 16px",
                borderRadius: "var(--radius-sm)",
                background: status === "approved" ? "var(--emerald-50)" : status === "rejected" ? "var(--red-light)" : "#fffbeb",
                color: status === "approved" ? "var(--emerald-900)" : status === "rejected" ? "#991b1b" : "#92400e",
                border: status === "approved" ? "1px solid var(--emerald-200)" : status === "rejected" ? "1px solid #fecaca" : "1px solid #fde68a",
                fontWeight: 500,
              }}
            >
              {status === "approved" ? (
                <span>✓ <strong>Approved &amp; Active.</strong> You have full verified credentials to claim available food listings.</span>
              ) : status === "rejected" ? (
                <span>✕ <strong>Application Rejected.</strong> Your receiver application was not approved. Please contact administrative support.</span>
              ) : (
                <span>⏳ <strong>Pending Administrative Review.</strong> An administrator must verify your application before food claiming is enabled.</span>
              )}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Account Created</label>
            <div style={{ fontSize: "15px", fontWeight: 500, color: "var(--text-main)" }}>
              {formatDate(profile?.created_at)}
            </div>
          </div>
        </div>

        {/* Actions Bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderTop: "1px solid var(--border-subtle)",
            paddingTop: "24px",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <Link to="/receiver" className="btn btn-sm">
              Browse Food
            </Link>
            <Link to="/receiver/claims" className="btn-secondary btn-sm">
              My Claims
            </Link>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="btn-danger btn-sm"
          >
            Log Out
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReceiverProfile;
