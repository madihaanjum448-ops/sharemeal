
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

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
      <div className="auth-container">
        <div className="auth-card">
          <h2>Email not found</h2>
          <p>Please start by entering your email address.</p>
          <button onClick={() => navigate("/login")}>
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!/^\d{6,8}$/.test(token)) {
      setError("Enter a valid 6–8 digit OTP.");
      return;
    }

    try {
      setLoading(true);

      const payload = {
        email,
        token,
      };

      // These fields are needed when creating a new profile.
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
    <div className="auth-container">
      <div className="auth-card">
        <h1>Verify Your Email</h1>

        <p>
          Enter the OTP sent to <strong>{email}</strong>.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="otp">Email OTP</label>

          <input
            id="otp"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="Enter 6–8 digit OTP"
            value={token}
            onChange={(e) =>
              setToken(e.target.value.replace(/\D/g, "").slice(0, 8))
            }
            required
          />

          <h3>New to ShareMeal?</h3>
          <p>
            If you are creating a new account, complete these
            profile details. Existing users can leave them blank.
          </p>

          <label htmlFor="fullName">Full Name</label>
          <input
            id="fullName"
            type="text"
            placeholder="Enter your full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />

          <label htmlFor="role">I want to join as</label>
          <select
            id="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="">Select your role</option>
            <option value="donor">Donor</option>
            <option value="receiver">Receiver</option>
          </select>

          <label htmlFor="organizationName">
            Organization Name (optional)
          </label>
          <input
            id="organizationName"
            type="text"
            placeholder="Enter organization name"
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
          />

          {error && <p className="auth-error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? "Verifying..." : "Verify OTP"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => navigate("/login")}
        >
          Back to Login
        </button>
      </div>
    </div>
  );
}

export default VerifyOTP;
