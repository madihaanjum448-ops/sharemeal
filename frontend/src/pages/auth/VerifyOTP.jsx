import { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Navbar from "../../components/shared/Navbar";
import Footer from "../../components/shared/Footer";
import "./Auth.css";

function VerifyOTP() {
  const location = useLocation();
  const navigate = useNavigate();

  const { verifyOTP } = useAuth();

  const email = location.state?.email || "";

  const [token, setToken] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("");
  const [organizationName, setOrganizationName] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!email) {
    return (
      <div className="auth-page-wrapper">
        <Navbar />
        <main className="auth-container">
          <div className="auth-card" style={{ textAlign: "center" }}>
            <h2>Email session not found</h2>
            <p className="auth-subtitle">Please enter your email address to receive an access code.</p>
            <button onClick={() => navigate("/login")} className="auth-submit-btn">
              Go to Login
            </button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!/^\d{6,8}$/.test(token)) {
      setError("Enter a valid 6–8 digit numeric OTP.");
      return;
    }

    try {
      setLoading(true);

      const payload = {
        email,
        token,
      };

      // These fields are needed when creating a new profile
      if (fullName.trim()) {
        payload.full_name = fullName.trim();
      }

      if (role) {
        payload.role = role;
      }

      if (organizationName.trim()) {
        payload.organization_name = organizationName.trim();
      }

      const data = await verifyOTP(payload);

      const userRole =
        data.profile?.role ||
        data.user?.role ||
        data.role;

      if (userRole === "donor") {
        navigate("/donor", { replace: true });
      } else if (userRole === "receiver") {
        navigate("/receiver", { replace: true });
      } else {
        navigate("/login", { replace: true });
      }
    } catch (err) {
      setError(err.message || "OTP verification failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page-wrapper">
      <Navbar />

      <main className="auth-container">
        <div className="auth-card">
          <div className="auth-brand-badge">
            <span>🔐 Verification Code</span>
          </div>

          <h1>Verify Your Email</h1>
          <p className="auth-subtitle">
            We sent a verification code to <strong>{email}</strong>. Enter it below to proceed.
          </p>

          <form onSubmit={handleSubmit}>
            <label htmlFor="otp">6–8 Digit Access Code</label>

            <input
              id="otp"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="e.g. 123456"
              value={token}
              onChange={(e) =>
                setToken(e.target.value.replace(/\D/g, "").slice(0, 8))
              }
              style={{
                fontSize: "18px",
                letterSpacing: "4px",
                textAlign: "center",
                fontWeight: 700,
              }}
              required
              autoFocus
            />

            {/* Registration details for new accounts */}
            <div
              style={{
                marginTop: "16px",
                padding: "20px 18px",
                background: "var(--bg-cream)",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border)",
                marginBottom: "20px",
              }}
            >
              <h3 style={{ marginTop: 0, fontSize: "14px", fontWeight: 700, color: "var(--emerald-900)" }}>
                New to ShareMeal? (Optional for existing users)
              </h3>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "0 0 16px 0" }}>
                If you are registering for the first time, provide your name and role below.
              </p>

              <label htmlFor="fullName">Full Name</label>
              <input
                id="fullName"
                type="text"
                placeholder="Your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                style={{ marginBottom: "14px" }}
              />

              <label htmlFor="role">I want to join as:</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "14px" }}>
                <button
                  type="button"
                  onClick={() => setRole("donor")}
                  style={{
                    padding: "10px",
                    borderRadius: "var(--radius-sm)",
                    border: role === "donor" ? "2px solid var(--primary)" : "1px solid var(--border)",
                    background: role === "donor" ? "var(--emerald-50)" : "#ffffff",
                    color: role === "donor" ? "var(--emerald-900)" : "var(--text-main)",
                    fontWeight: role === "donor" ? 700 : 500,
                    fontSize: "13px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                    boxShadow: "none",
                    transform: "none",
                  }}
                >
                  <span>🍲 Food Donor</span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "normal" }}>Share surplus</span>
                </button>

                <button
                  type="button"
                  onClick={() => setRole("receiver")}
                  style={{
                    padding: "10px",
                    borderRadius: "var(--radius-sm)",
                    border: role === "receiver" ? "2px solid var(--primary)" : "1px solid var(--border)",
                    background: role === "receiver" ? "var(--emerald-50)" : "#ffffff",
                    color: role === "receiver" ? "var(--emerald-900)" : "var(--text-main)",
                    fontWeight: role === "receiver" ? 700 : 500,
                    fontSize: "13px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                    boxShadow: "none",
                    transform: "none",
                  }}
                >
                  <span>🤝 Food Receiver</span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "normal" }}>Claim food</span>
                </button>
              </div>

              {/* Hidden select kept for fallback accessibility */}
              <select
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{ display: "none" }}
              >
                <option value="">Select your role</option>
                <option value="donor">Donor</option>
                <option value="receiver">Receiver</option>
              </select>

              <label htmlFor="organizationName">Organization Name (Optional)</label>
              <input
                id="organizationName"
                type="text"
                placeholder="e.g. Community Kitchen, Shelter, Bakery"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                style={{ marginBottom: 0 }}
              />
            </div>

            {error && <div className="auth-error">{error}</div>}

            <button type="submit" disabled={loading} className="auth-submit-btn">
              {loading ? "Verifying..." : "Verify & Log In"}
            </button>
          </form>

          <div style={{ marginTop: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="btn-secondary btn-sm"
              style={{ padding: "6px 12px" }}
            >
              ← Back to Login
            </button>
            <Link to="/" style={{ fontSize: "13px", color: "var(--text-muted)", textDecoration: "none" }}>
              Home
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default VerifyOTP;
