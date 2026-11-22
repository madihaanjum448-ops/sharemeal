import { Outlet } from "react-router-dom";
import Navbar from "../components/shared/Navbar";
import Footer from "../components/shared/Footer";
import "./DonorLayout.css";

function DonorLayout() {
  return (
    <div className="donor-layout">
      <Navbar />

      <main className="donor-main">
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}

export default DonorLayout;
