import HygieneChecklist from "../../components/shared/HygieneChecklist";
import FoodCategory from "../../components/shared/FoodCategory";
import SafeUntil from "../../components/shared/SafeUntil";
import DonorPostForm from "./DonorPostForm";
import PhotoUpload from "../../components/shared/PhotoUpload";
function DonorHome() {
  return (
    <div>
      <h1>Welcome to ShareMeal</h1>
      <HygieneChecklist />
      <FoodCategory />
      <SafeUntil />
      <DonorPostForm />
      <PhotoUpload />
    </div>
  );
}

export default DonorHome;