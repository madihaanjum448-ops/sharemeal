import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function DonorProfile() {
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

  return (
    <div className="page-container" style={{ maxWidth: "700px" }}>
      <div className="page-header">
        <h1>Donor Profile</h1>
        <p>Manage your account and view your registration details.</p>
      </div>

      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "24px" }}>
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "50%",
              background: "var(--primary-light)",
              color: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "24px",
              fontWeight: 700,
            }}
          >
            {(profile?.full_name || user?.email || "D")[0].toUpperCase()}
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: "20px", color: "var(--text-main)" }}>
              {profile?.full_name || "Food Donor"}
            </h2>
            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <span className="badge badge-approved">Donor Account</span>
              {profile?.is_verified && (
                <span className="badge badge-active">Verified</span>
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

          {profile?.phone && (
            <div>
              <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Phone Number</label>
              <div style={{ fontSize: "15px", fontWeight: 500 }}>{profile.phone}</div>
            </div>
          )}

          {profile?.organization_name && (
            <div>
              <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Organization</label>
              <div style={{ fontSize: "15px", fontWeight: 500 }}>{profile.organization_name}</div>
            </div>
          )}

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Account Created</label>
            <div style={{ fontSize: "15px", fontWeight: 500 }}>
              {formatDate(profile?.created_at)}
            </div>
          </div>
        </div>

        <div style={{ marginTop: "32px", display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border)", paddingTop: "20px" }}>
          <div style={{ display: "flex", gap: "10px" }}>
            <Link to="/donor" className="btn btn-sm">
              Donate Food
            </Link>
            <Link to="/donor/posts" className="btn-secondary btn-sm">
              My Donations
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

export default DonorProfile;
