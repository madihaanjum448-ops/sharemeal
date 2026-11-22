import { useState, useEffect } from "react";

const CHECKLIST_ITEMS = [
  "Food was prepared in a hygienic, sanitary environment",
  "Clean utensils, surfaces, and hands were used during preparation",
  "Food was kept at safe temperatures after cooking",
  "Food is properly packaged and covered for transit",
];

function HygieneChecklist({ onHygieneConfirmed }) {
  const [checkedItems, setCheckedItems] = useState([]);

  const isAllChecked = checkedItems.length === CHECKLIST_ITEMS.length;

  useEffect(() => {
    if (onHygieneConfirmed) {
      onHygieneConfirmed(isAllChecked);
    }
  }, [isAllChecked, onHygieneConfirmed]);

  const handleToggle = (item) => {
    setCheckedItems((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  const handleCheckAll = () => {
    if (isAllChecked) {
      setCheckedItems([]);
    } else {
      setCheckedItems([...CHECKLIST_ITEMS]);
    }
  };

  return (
    <div
      style={{
        background: "#f9fafb",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "16px",
        marginBottom: "20px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "12px",
        }}
      >
        <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-main)" }}>
          Food Hygiene & Safety Checklist
        </h4>
        <button
          type="button"
          onClick={handleCheckAll}
          className="btn-secondary btn-sm"
        >
          {isAllChecked ? "Uncheck All" : "Check All"}
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {CHECKLIST_ITEMS.map((item, index) => {
          const checked = checkedItems.includes(item);
          return (
            <label
              key={index}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                margin: 0,
                fontSize: "13px",
                cursor: "pointer",
                color: checked ? "var(--text-main)" : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => handleToggle(item)}
                style={{ width: "16px", height: "16px", margin: 0, accentColor: "var(--primary)" }}
              />
              <span>{item}</span>
            </label>
          );
        })}
      </div>

      {!isAllChecked && (
        <p style={{ margin: "10px 0 0 0", fontSize: "12px", color: "var(--warning)", fontWeight: 500 }}>
          * All 4 hygiene safety items must be verified to donate food.
        </p>
      )}
    </div>
  );
}

export default HygieneChecklist;
