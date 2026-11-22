import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Navbar from "../../components/shared/Navbar";
import Footer from "../../components/shared/Footer";
import "./Auth.css";

function EmailLogin() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const { sendOTP } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }

    try {
      setLoading(true);

      await sendOTP(email.trim().toLowerCase());

      setMessage("OTP sent successfully! Redirecting...");

      navigate("/verify-otp", {
        state: { email: email.trim().toLowerCase() },
      });
    } catch (err) {
      setError(err.message || "Unable to send OTP.");
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
            <span>✨ Passwordless Login</span>
          </div>

          <h1>Welcome to ShareMeal</h1>
          <p className="auth-subtitle">
            Enter your email to receive a secure, one-time login code. No passwords required.
          </p>

          <form onSubmit={handleSubmit}>
            <label htmlFor="email">Email Address</label>

            <input
              id="email"
              type="email"
              placeholder="e.g. name@community.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />

            {error && <div className="auth-error">{error}</div>}
            {message && <div className="auth-success">{message}</div>}

            <button type="submit" disabled={loading} className="auth-submit-btn">
              {loading ? "Sending One-Time Code..." : "Send Verification Code"}
            </button>
          </form>

          <div className="auth-footer-nav">
            <Link to="/" className="auth-back-link">
              ← Return to Home
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default EmailLogin;
