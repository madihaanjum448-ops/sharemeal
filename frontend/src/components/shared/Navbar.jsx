import { NavLink, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./Navbar.css";

function Navbar() {
  const { profile, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const role = profile?.role || "donor";
  const homePath = `/${role}`;

  return (
    <header className="app-navbar">
      <Link to={homePath} className="nav-brand">
        <h2>ShareMeal</h2>
        <span className="brand-tagline">Food Share</span>
      </Link>

      <nav className="nav-links">
        {role === "donor" && (
          <>
            <NavLink to="/donor" end>
              Donate Food
            </NavLink>
            <NavLink to="/donor/posts">
              My Posts
            </NavLink>
            <NavLink to="/donor/profile">
              Profile
            </NavLink>
          </>
        )}

        {role === "receiver" && (
          <>
            <NavLink to="/receiver" end>
              Browse Food
            </NavLink>
            <NavLink to="/receiver/claims">
              My Claims
            </NavLink>
            <NavLink to="/receiver/profile">
              Profile
            </NavLink>
          </>
        )}

        {role === "admin" && (
          <>
            <NavLink to="/admin" end>
              Pending Receivers
            </NavLink>
            <NavLink to="/admin/profile">
              Profile
            </NavLink>
          </>
        )}
      </nav>

      <div className="nav-user-section">
        <div className="user-pill">
          <span>{profile?.full_name || user?.email || "User"}</span>
          <span className={`user-role-badge user-role-${role}`}>
            {role}
          </span>
        </div>

        <button onClick={handleLogout} className="btn-logout" type="button">
          Log Out
        </button>
      </div>
    </header>
  );
}

export default Navbar;
