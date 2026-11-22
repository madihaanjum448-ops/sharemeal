
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import LandingPage from "./pages/LandingPage";

import DonorLayout from "./layouts/DonorLayout";
import ReceiverLayout from "./layouts/ReceiverLayout";

import DonorHome from "./pages/donor/DonorHome";
import MyPosts from "./pages/donor/MyPosts";
import DonorProfile from "./pages/donor/DonorProfile";

import ReceiverBrowse from "./pages/receiver/ReceiverBrowse";
import ReceiverClaims from "./pages/receiver/ReceiverClaims";
import ReceiverProfile from "./pages/receiver/ReceiverProfile";
import NGOApplication from "./pages/receiver/NGOApplication";

import EmailLogin from "./pages/auth/EmailLogin";
import VerifyOTP from "./pages/auth/VerifyOTP";

import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<EmailLogin />} />
        <Route path="/verify-otp" element={<VerifyOTP />} />

        {/* Donor routes */}
        <Route element={<ProtectedRoute allowedRole="donor" />}>
          <Route path="/donor" element={<DonorLayout />}>
            <Route index element={<DonorHome />} />
            <Route path="posts" element={<MyPosts />} />
            <Route path="profile" element={<DonorProfile />} />
          </Route>
        </Route>

        {/* Receiver routes */}
        <Route element={<ProtectedRoute allowedRole="receiver" />}>
          <Route path="/receiver" element={<ReceiverLayout />}>
            <Route index element={<ReceiverBrowse />} />
            <Route path="claims" element={<ReceiverClaims />} />
            <Route path="profile" element={<ReceiverProfile />} />
            <Route path="apply" element={<NGOApplication />} />
          </Route>
        </Route>

        {/* Unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
