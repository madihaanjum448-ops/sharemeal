import "./Navbar.css";
import { NavLink } from "react-router-dom";

function Navbar() {
  return (
    <header>
      <h2>ShareMeal</h2>

      <nav>
        <NavLink to="/donor">Home</NavLink>
        <NavLink to="/donor/posts">My Posts</NavLink>
        <NavLink to="/donor/profile">Profile</NavLink>
      </nav>
    </header>
  );
}

export default Navbar;
