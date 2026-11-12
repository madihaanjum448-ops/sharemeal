
import { Outlet } from "react-router-dom";
import Navbar from "../components/shared/Navbar";
import "./DonorLayout.css";

function DonorLayout() {
  return (
    <div className="donor-layout">
      <Navbar />

      <main className="donor-main">
        <Outlet />
      </main>
    </div>
  );
}

export default DonorLayout;
