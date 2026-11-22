function FoodCategory({ value, onChange }) {
  return (
    <div style={{ marginBottom: "24px" }}>
      <label style={{ fontWeight: 700, fontSize: "14px", color: "var(--emerald-900)", marginBottom: "8px" }}>
        Food Category *
      </label>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
            padding: "16px",
            border: value === "human" ? "2px solid var(--primary)" : "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            background: value === "human" ? "var(--emerald-50)" : "#ffffff",
            cursor: "pointer",
            margin: 0,
            transition: "all 0.15s ease",
            boxShadow: value === "human" ? "0 2px 8px rgba(4, 120, 87, 0.08)" : "none",
          }}
        >
          <input
            type="radio"
            name="food_category"
            value="human"
            checked={value === "human"}
            onChange={(e) => onChange(e.target.value)}
            style={{ marginTop: "3px", accentColor: "var(--primary)", width: "16px", height: "16px" }}
          />
          <div>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--emerald-900)", marginBottom: "2px" }}>
              Human Consumption
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.4 }}>
              Cooked meals, pantry staples, baked goods, fresh fruits &amp; vegetables
            </div>
          </div>
        </label>

        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
            padding: "16px",
            border: value === "animal" ? "2px solid var(--primary)" : "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            background: value === "animal" ? "var(--emerald-50)" : "#ffffff",
            cursor: "pointer",
            margin: 0,
            transition: "all 0.15s ease",
            boxShadow: value === "animal" ? "0 2px 8px rgba(4, 120, 87, 0.08)" : "none",
          }}
        >
          <input
            type="radio"
            name="food_category"
            value="animal"
            checked={value === "animal"}
            onChange={(e) => onChange(e.target.value)}
            style={{ marginTop: "3px", accentColor: "var(--primary)", width: "16px", height: "16px" }}
          />
          <div>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--emerald-900)", marginBottom: "2px" }}>
              Animal Feed
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.4 }}>
              Safe for livestock, animal shelters, sanctuaries, or composting
            </div>
          </div>
        </label>
      </div>
    </div>
  );
}

export default FoodCategory;
