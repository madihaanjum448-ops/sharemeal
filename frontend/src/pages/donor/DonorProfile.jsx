
import { useAuth } from "../../context/AuthContext";
import { useNavigate } from "react-router-dom";

function DonorProfile() {
  const { user, profile, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div>
      <h1>Donor Profile</h1>

      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "20px",
          maxWidth: "500px",
        }}
      >
        <h2>Account Information</h2>

        <p>
          <strong>Name:</strong>{" "}
          {profile?.full_name || "Not available"}
        </p>

        <p>
          <strong>Email:</strong>{" "}
          {profile?.email || user?.email || "Not available"}
        </p>

        <p>
          <strong>Role:</strong>{" "}
          {profile?.role || "Donor"}
        </p>

        <p>
          <strong>Organization:</strong>{" "}
          {profile?.organization_name || "Not specified"}
        </p>

        <button onClick={handleLogout}>
          Logout
        </button>
      </div>
    </div>
  );
}

export default DonorProfile;
