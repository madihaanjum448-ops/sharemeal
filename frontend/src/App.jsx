
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import DonorLayout from "./layouts/DonorLayout";
import DonorHome from "./pages/donor/DonorHome";
import MyPosts from "./pages/donor/MyPosts";
import DonorProfile from "./pages/donor/DonorProfile";

import ReceiverLayout from "./layouts/ReceiverLayout";
import ReceiverBrowse from "./pages/receiver/ReceiverBrowse";
import ReceiverClaims from "./pages/receiver/ReceiverClaims";
import ReceiverProfile from "./pages/receiver/ReceiverProfile";

import EmailLogin from "./pages/auth/EmailLogin";
import VerifyOTP from "./pages/auth/VerifyOTP";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public authentication pages */}
        <Route path="/login" element={<EmailLogin />} />
        <Route path="/verify-otp" element={<VerifyOTP />} />

        {/* Donor-only pages */}
        <Route element={<ProtectedRoute allowedRole="donor" />}>
          <Route path="/donor" element={<DonorLayout />}>
            <Route index element={<DonorHome />} />
            <Route path="posts" element={<MyPosts />} />
            <Route path="profile" element={<DonorProfile />} />
          </Route>
        </Route>

        {/* Receiver-only pages */}
        <Route element={<ProtectedRoute allowedRole="receiver" />}>
          <Route path="/receiver" element={<ReceiverLayout />}>
            <Route index element={<Navigate to="browse" replace />} />
            <Route path="browse" element={<ReceiverBrowse />} />
            <Route path="claims" element={<ReceiverClaims />} />
            <Route path="profile" element={<ReceiverProfile />} />
          </Route>
        </Route>

        {/* Default route */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
