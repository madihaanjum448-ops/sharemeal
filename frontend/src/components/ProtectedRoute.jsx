
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function ProtectedRoute({ allowedRole }) {
  const { user, profile, isLoading } = useAuth();

  if (isLoading) {
    return <p>Loading your account...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRole && profile?.role !== allowedRole) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
