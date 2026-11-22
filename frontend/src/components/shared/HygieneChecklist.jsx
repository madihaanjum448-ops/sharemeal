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
        background: isAllChecked ? "var(--emerald-50)" : "#ffffff",
        border: isAllChecked ? "1px solid var(--emerald-200)" : "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "20px 22px",
        marginBottom: "28px",
        transition: "all 0.2s ease",
        boxShadow: "var(--shadow-card)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "16px" }}>🛡️</span>
          <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--emerald-900)" }}>
            Food Hygiene &amp; Safety Protocol
          </h4>
        </div>
        <button
          type="button"
          onClick={handleCheckAll}
          className="btn-secondary btn-sm"
          style={{ padding: "4px 10px", fontSize: "12px" }}
        >
          {isAllChecked ? "Uncheck All" : "Select All 4 Items"}
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
                alignItems: "flex-start",
                gap: "10px",
                margin: 0,
                fontSize: "13px",
                cursor: "pointer",
                color: checked ? "var(--emerald-900)" : "var(--text-muted)",
                fontWeight: checked ? 600 : 400,
                lineHeight: 1.4,
              }}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => handleToggle(item)}
                style={{
                  width: "16px",
                  height: "16px",
                  marginTop: "2px",
                  accentColor: "var(--primary)",
                  cursor: "pointer",
                }}
              />
              <span>{item}</span>
            </label>
          );
        })}
      </div>

      {!isAllChecked ? (
        <p style={{ margin: "12px 0 0 0", fontSize: "12px", color: "var(--warning)", fontWeight: 600 }}>
          ⚠️ All 4 hygiene safety criteria must be confirmed before posting.
        </p>
      ) : (
        <p style={{ margin: "12px 0 0 0", fontSize: "12px", color: "var(--primary)", fontWeight: 700 }}>
          ✓ All hygiene protocols verified. Ready to publish!
        </p>
      )}
    </div>
  );
}

export default HygieneChecklist;
