
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import DonorLayout from "./layouts/DonorLayout";
import DonorHome from "./pages/donor/DonorHome";
import MyPosts from "./pages/donor/MyPosts";
import DonorProfile from "./pages/donor/DonorProfile";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/donor" replace />} />

        <Route path="/donor" element={<DonorLayout />}>
          <Route index element={<DonorHome />} />
          <Route path="posts" element={<MyPosts />} />
          <Route path="profile" element={<DonorProfile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
