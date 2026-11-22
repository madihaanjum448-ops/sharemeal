import { Outlet } from "react-router-dom";
import Navbar from "../components/shared/Navbar";
import Footer from "../components/shared/Footer";
import { useAuth } from "../context/AuthContext";

function ReceiverLayout() {
  const { profile } = useAuth();

  const isPending = profile?.approval_status === "pending";
  const isRejected = profile?.approval_status === "rejected";

  return (
    <div className="receiver-layout" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg-cream)" }}>
      <Navbar />

      <div className="page-container" style={{ paddingBottom: "10px" }}>
        {isPending && (
          <div className="alert alert-warning" style={{ margin: "0 0 24px 0", borderRadius: "var(--radius-md)" }}>
            <div>
              <strong style={{ display: "block", marginBottom: "2px" }}>Account Pending Administrator Verification:</strong>
              Your receiver registration is currently under review. You can browse active food listings in your area, but claiming donations requires administrator approval.
            </div>
          </div>
        )}

        {isRejected && (
          <div className="alert alert-danger" style={{ margin: "0 0 24px 0", borderRadius: "var(--radius-md)" }}>
            <div>
              <strong style={{ display: "block", marginBottom: "2px" }}>Application Review Not Approved:</strong>
              Your receiver verification request was not approved by the administrative team. You will not be able to claim food donations. Please contact community support for assistance.
            </div>
          </div>
        )}
      </div>

      <main style={{ flex: 1 }}>
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}

export default ReceiverLayout;
