function FoodCategory({ value, onChange }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <label style={{ fontWeight: 600, marginBottom: "8px" }}>
        Food Category *
      </label>
      <div style={{ display: "flex", gap: "16px" }}>
        <label
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "12px 16px",
            border: value === "human" ? "2px solid var(--primary)" : "1px solid var(--border)",
            borderRadius: "8px",
            background: value === "human" ? "var(--primary-light)" : "#fff",
            cursor: "pointer",
            fontWeight: 500,
            margin: 0,
          }}
        >
          <input
            type="radio"
            name="food_category"
            value="human"
            checked={value === "human"}
            onChange={(e) => onChange(e.target.value)}
            style={{ margin: 0, accentColor: "var(--primary)" }}
          />
          <div>
            <div style={{ fontWeight: 600 }}>Human Consumption</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Cooked meals, groceries, fresh produce</div>
          </div>
        </label>

        <label
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "12px 16px",
            border: value === "animal" ? "2px solid var(--primary)" : "1px solid var(--border)",
            borderRadius: "8px",
            background: value === "animal" ? "var(--primary-light)" : "#fff",
            cursor: "pointer",
            fontWeight: 500,
            margin: 0,
          }}
        >
          <input
            type="radio"
            name="food_category"
            value="animal"
            checked={value === "animal"}
            onChange={(e) => onChange(e.target.value)}
            style={{ margin: 0, accentColor: "var(--primary)" }}
          />
          <div>
            <div style={{ fontWeight: 600 }}>Animal Feed</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Safe for pets, livestock, or shelters</div>
          </div>
        </label>
      </div>
    </div>
  );
}

export default FoodCategory;
