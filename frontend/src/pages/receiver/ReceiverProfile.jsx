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

  return (
    <div className="page-container" style={{ maxWidth: "700px" }}>
      <div className="page-header">
        <h1>Receiver Profile</h1>
        <p>Manage your receiver organization account and verification status.</p>
      </div>

      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "24px" }}>
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "50%",
              background: "var(--info-light)",
              color: "var(--info)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "24px",
              fontWeight: 700,
            }}
          >
            {(profile?.full_name || user?.email || "R")[0].toUpperCase()}
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: "20px", color: "var(--text-main)" }}>
              {profile?.full_name || "Receiver"}
            </h2>
            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <span className={`badge badge-${status}`}>
                Status: {status}
              </span>
              {profile?.is_verified && (
                <span className="badge badge-active">Verified Receiver</span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px", borderTop: "1px solid var(--border)", paddingTop: "20px" }}>
          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Full Name</label>
            <div style={{ fontSize: "15px", fontWeight: 500 }}>
              {profile?.full_name || "Not specified"}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Email Address</label>
            <div style={{ fontSize: "15px", fontWeight: 500 }}>
              {user?.email || "Not specified"}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Organization</label>
            <div style={{ fontSize: "15px", fontWeight: 500 }}>
              {profile?.organization_name || "Independent / Individual"}
            </div>
          </div>

          {profile?.phone && (
            <div>
              <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Phone Number</label>
              <div style={{ fontSize: "15px", fontWeight: 500 }}>{profile.phone}</div>
            </div>
          )}

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Verification &amp; Approval Status</label>
            <div style={{ fontSize: "14px", marginTop: "4px" }}>
              {status === "approved" ? (
                <span style={{ color: "var(--primary)", fontWeight: 600 }}>
                  Approved &amp; Active. You have full access to claim food donations.
                </span>
              ) : status === "rejected" ? (
                <span style={{ color: "var(--danger)", fontWeight: 600 }}>
                  Application Rejected. Please reach out to administrative support.
                </span>
              ) : (
                <span style={{ color: "var(--warning)", fontWeight: 600 }}>
                  Pending Review. An administrator must approve your application before you can claim food.
                </span>
              )}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Account Created</label>
            <div style={{ fontSize: "15px", fontWeight: 500 }}>
              {formatDate(profile?.created_at)}
            </div>
          </div>
        </div>

        <div style={{ marginTop: "32px", display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border)", paddingTop: "20px" }}>
          <div style={{ display: "flex", gap: "10px" }}>
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
