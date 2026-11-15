import { useAuth } from "../../context/AuthContext";
import DonorPostForm from "./DonorPostForm";

function DonorHome() {
  const { profile } = useAuth();

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1>Welcome, {profile?.full_name || "Food Donor"}!</h1>
          <p>
            You are preventing food waste and feeding those in need. Fill out the form below to post a donation.
          </p>
        </div>
      </div>

      <DonorPostForm />
    </div>
  );
}

export default DonorHome;
