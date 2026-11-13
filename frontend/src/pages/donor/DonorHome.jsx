import HygieneChecklist from "../../components/shared/HygieneChecklist";
import FoodCategory from "../../components/shared/FoodCategory";
import SafeUntil from "../../components/shared/SafeUntil";
function DonorHome() {
  return (
    <div>
      <h1>Welcome to ShareMeal</h1>
      <HygieneChecklist />
      <FoodCategory />
      <SafeUntil />
    </div>
  );
}

export default DonorHome;