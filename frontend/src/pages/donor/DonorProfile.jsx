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

  const initial = (profile?.full_name || user?.email || "D")[0].toUpperCase();

  return (
    <div className="page-container" style={{ maxWidth: "760px" }}>
      <div className="page-header">
        <h1>Donor Profile</h1>
        <p>Manage your food donor account credentials and organization details.</p>
      </div>

      <div className="card" style={{ padding: "36px" }}>
        {/* Profile Header Block */}
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
              {profile?.full_name || "Food Donor"}
            </h2>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <span className="badge badge-approved">Donor Account</span>
              {profile?.is_verified && (
                <span className="badge badge-active">✓ Verified Donor</span>
              )}
            </div>
          </div>
        </div>

        {/* Account Details Grid */}
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
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>
              Full Name
            </label>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
              {profile?.full_name || "Not specified"}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>
              Email Address
            </label>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
              {user?.email || "Not specified"}
            </div>
          </div>

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>
              Organization / Business
            </label>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
              {profile?.organization_name || "Independent Food Donor"}
            </div>
          </div>

          {profile?.phone && (
            <div>
              <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>
                Contact Phone
              </label>
              <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-main)" }}>
                {profile.phone}
              </div>
            </div>
          )}

          <div>
            <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>
              Account Created
            </label>
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
            <Link to="/donor" className="btn btn-sm">
              + Donate Food
            </Link>
            <Link to="/donor/posts" className="btn-secondary btn-sm">
              📋 My Donations
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
