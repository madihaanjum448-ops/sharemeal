import { useState } from "react";
import { NavLink, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./Navbar.css";

function Navbar() {
  const { profile, user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    setMobileMenuOpen(false);
    navigate("/login", { replace: true });
  };

  const role = profile?.role || user?.role || "donor";
  const homePath = user ? (role === "receiver" ? "/receiver" : "/donor") : "/";

  const closeMenu = () => setMobileMenuOpen(false);

  return (
    <header className="app-navbar">
      <div className="navbar-container">
        {/* Brand Logo & Name */}
        <Link to={homePath} className="nav-brand" onClick={closeMenu}>
          <div className="brand-icon-wrapper">
            <svg
              className="brand-logo-icon"
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
          </div>
          <div className="brand-text-group">
            <span className="brand-title">ShareMeal</span>
            <span className="brand-tagline">Food Share</span>
          </div>
        </Link>

        {/* Mobile Hamburger Toggle Button */}
        <button
          className="mobile-nav-toggle"
          type="button"
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <span className={`hamburger-bar ${mobileMenuOpen ? "open" : ""}`}></span>
          <span className={`hamburger-bar ${mobileMenuOpen ? "open" : ""}`}></span>
          <span className={`hamburger-bar ${mobileMenuOpen ? "open" : ""}`}></span>
        </button>

        {/* Navigation Links and User Section */}
        <div className={`nav-menu-wrapper ${mobileMenuOpen ? "open" : ""}`}>
          <nav className="nav-links">
            {user ? (
              <>
                {role === "donor" && (
                  <>
                    <NavLink to="/donor" end onClick={closeMenu}>
                      Donate Food
                    </NavLink>
                    <NavLink to="/donor/posts" onClick={closeMenu}>
                      My Posts
                    </NavLink>
                    <NavLink to="/donor/profile" onClick={closeMenu}>
                      Profile
                    </NavLink>
                  </>
                )}

                {role === "receiver" && (
                  <>
                    <NavLink to="/receiver" end onClick={closeMenu}>
                      Browse Food
                    </NavLink>
                    <NavLink to="/receiver/claims" onClick={closeMenu}>
                      My Claims
                    </NavLink>
                    <NavLink to="/receiver/profile" onClick={closeMenu}>
                      Profile
                    </NavLink>
                  </>
                )}

                {role === "admin" && (
                  <>
                    <NavLink to="/admin" end onClick={closeMenu}>
                      Pending Receivers
                    </NavLink>
                    <NavLink to="/admin/profile" onClick={closeMenu}>
                      Profile
                    </NavLink>
                  </>
                )}
              </>
            ) : (
              <>
                <Link to="/" onClick={closeMenu}>
                  Home
                </Link>
                <a href="/#how-it-works" onClick={closeMenu}>
                  How It Works
                </a>
                <a href="/#impact" onClick={closeMenu}>
                  Our Mission
                </a>
              </>
            )}
          </nav>

          <div className="nav-user-section">
            {user ? (
              <>
                <div className="user-pill">
                  <span className="user-pill-name">
                    {profile?.full_name || user?.email || "User"}
                  </span>
                  <span className={`user-role-badge user-role-${role}`}>
                    {role}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="btn-logout"
                  type="button"
                >
                  Log Out
                </button>
              </>
            ) : (
              <div className="auth-nav-buttons">
                <Link to="/login" className="btn-secondary btn-sm" onClick={closeMenu}>
                  Sign In
                </Link>
                <Link to="/login" className="btn btn-sm" onClick={closeMenu}>
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
