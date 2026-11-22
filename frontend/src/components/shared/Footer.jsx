import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./Footer.css";

const CURRENT_YEAR = new Date().getFullYear();

function Footer() {
  const { user, profile } = useAuth();
  const role = profile?.role;

  return (
    <footer className="app-footer">
      <div className="footer-container">
        <div className="footer-brand-column">
          <Link to="/" className="footer-brand">
            <svg
              className="footer-logo-icon"
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <circle cx="16" cy="16" r="15" fill="#047857" />
              <path
                d="M16 8C13.5 10.5 11 14 11 18C11 20.76 13.24 23 16 23C18.76 23 21 20.76 21 18C21 14 18.5 10.5 16 8Z"
                fill="#FAF8F2"
              />
              <path
                d="M16 11V22M13 16C14 17.5 16 18 16 18"
                stroke="#047857"
                strokeWidth="1.75"
                strokeLinecap="round"
              />
            </svg>
            <span className="footer-brand-name">ShareMeal</span>
          </Link>
          <p className="footer-mission">
            A community-first food sharing platform bridging surplus meals from local kitchens, businesses, and neighbors to verified receivers.
          </p>
          <div className="footer-ethos-badge">
            <span className="ethos-dot"></span>
            Zero Food Waste • Dignified Community Care
          </div>
        </div>

        <div className="footer-links-grid">
          <div className="footer-col">
            <h4 className="footer-heading">Platform</h4>
            <ul>
              <li>
                <Link to="/">Home</Link>
              </li>
              <li>
                <Link to={user ? (role === "donor" ? "/donor" : "/receiver") : "/login"}>
                  {role === "donor" ? "Donate Food" : role === "receiver" ? "Browse Food" : "Get Started"}
                </Link>
              </li>
              {user && role === "donor" && (
                <li>
                  <Link to="/donor/posts">My Listings</Link>
                </li>
              )}
              {user && role === "receiver" && (
                <li>
                  <Link to="/receiver/claims">My Claims</Link>
                </li>
              )}
              <li>
                <a href="#how-it-works">How It Works</a>
              </li>
            </ul>
          </div>

          <div className="footer-col">
            <h4 className="footer-heading">Safety &amp; Standards</h4>
            <ul>
              <li>
                <span>Strict Freshness Windows</span>
              </li>
              <li>
                <span>4-Point Hygiene Verification</span>
              </li>
              <li>
                <span>Verified Receiver Network</span>
              </li>
              <li>
                <span>Donor Privacy Protection</span>
              </li>
            </ul>
          </div>

          <div className="footer-col">
            <h4 className="footer-heading">Community</h4>
            <ul>
              <li>
                <span>Surplus Rescue</span>
              </li>
              <li>
                <span>Food Sovereignty</span>
              </li>
              <li>
                <span>Neighbourhood Solidarity</span>
              </li>
              <li>
                <Link to="/login">Access Account</Link>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <div className="footer-bottom-container">
          <p>© {CURRENT_YEAR} ShareMeal Platform. Designed for sustainable, community-driven nourishment.</p>
          <div className="footer-legal">
            <span>Freshness First</span>
            <span>•</span>
            <span>Verified Exchange</span>
            <span>•</span>
            <span>Community Driven</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
