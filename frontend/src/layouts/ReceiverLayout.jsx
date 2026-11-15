import { Outlet } from "react-router-dom";
import Navbar from "../components/shared/Navbar";
import { useAuth } from "../context/AuthContext";

function ReceiverLayout() {
  const { profile } = useAuth();

  const isPending = profile?.approval_status === "pending";
  const isRejected = profile?.approval_status === "rejected";

  return (
    <div className="receiver-layout" style={{ minHeight: "100vh", backgroundColor: "var(--bg-page)" }}>
      <Navbar />

      <div className="page-container" style={{ paddingBottom: "10px" }}>
        {isPending && (
          <div className="alert alert-warning" style={{ margin: "0 0 20px 0" }}>
            <div>
              <strong>Account Pending Verification:</strong> Your receiver application is currently being reviewed by an administrator. You can explore available food listings, but claiming food requires approval.
            </div>
          </div>
        )}

        {isRejected && (
          <div className="alert alert-danger" style={{ margin: "0 0 20px 0" }}>
            <div>
              <strong>Application Not Approved:</strong> Your receiver verification application was rejected by the administration. You will not be able to claim food listings. Please contact support.
            </div>
          </div>
        )}
      </div>

      <main>
        <Outlet />
      </main>
    </div>
  );
}

export default ReceiverLayout;
