
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import DonorLayout from "./layouts/DonorLayout";
import DonorHome from "./pages/donor/DonorHome";
import MyPosts from "./pages/donor/MyPosts";
import DonorProfile from "./pages/donor/DonorProfile";

import EmailLogin from "./pages/auth/EmailLogin";
import VerifyOTP from "./pages/auth/VerifyOTP";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public authentication routes */}
        <Route path="/login" element={<EmailLogin />} />
        <Route path="/verify-otp" element={<VerifyOTP />} />

        {/* Protected donor routes */}
        <Route element={<ProtectedRoute allowedRole="donor" />}>
          <Route path="/donor" element={<DonorLayout />}>
            <Route index element={<DonorHome />} />
            <Route path="posts" element={<MyPosts />} />
            <Route path="profile" element={<DonorProfile />} />
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
