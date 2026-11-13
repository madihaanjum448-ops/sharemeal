import { useState } from "react";
function HygieneChecklist() {
  const [checkedItems, setCheckedItems] = useState([]);
  const checklistItems = [
    "Food was prepared in a clean environment",
    "Clean hands and utensils were used",
    "Food was stored safely after preparation",
    "Food is properly covered for pickup",
  ];

  return (
    <div>
      <h3>Food Hygiene Checklist</h3>
      <p>Please confirm the following before posting your donation.</p>

      {checklistItems.map((item, index) => (
        <label key={index} style={{ display: "block", marginBottom: "12px" }}>
          <input
  type="checkbox"
  checked={checkedItems.includes(item)}
  onChange={(e) => {
    if (e.target.checked) {
      setCheckedItems([...checkedItems, item]);
    } else {
      setCheckedItems(checkedItems.filter((checked) => checked !== item));
    }
  }}
/>
          {" "}{item}
        </label>
      ))}
    </div>
  );
}

export default HygieneChecklist;