import { useState } from "react";

function SafeUntil({ value, onChange }) {
  const [minDateTime] = useState(() => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  });

  // Sets time relative to current local time
  const handlePreset = (hours) => {
    const d = new Date();
    d.setHours(d.getHours() + hours);
    const pad = (n) => String(n).padStart(2, "0");
    const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    onChange(formatted);
  };

  return (
    <div style={{ marginBottom: "24px" }}>
      <label style={{ fontWeight: 700, fontSize: "14px", color: "var(--emerald-900)", marginBottom: "4px" }}>
        Safe Until (Freshness Expiry) *
      </label>
      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "10px" }}>
        Until when is this batch safe and wholesome for collection?
      </span>

      <div style={{ display: "flex", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => handlePreset(2)}
          className="btn-secondary btn-sm"
          style={{ padding: "6px 12px", fontSize: "12px" }}
        >
          +2 Hours
        </button>
        <button
          type="button"
          onClick={() => handlePreset(4)}
          className="btn-secondary btn-sm"
          style={{ padding: "6px 12px", fontSize: "12px" }}
        >
          +4 Hours
        </button>
        <button
          type="button"
          onClick={() => handlePreset(8)}
          className="btn-secondary btn-sm"
          style={{ padding: "6px 12px", fontSize: "12px" }}
        >
          +8 Hours
        </button>
        <button
          type="button"
          onClick={() => handlePreset(24)}
          className="btn-secondary btn-sm"
          style={{ padding: "6px 12px", fontSize: "12px" }}
        >
          +24 Hours (Next Day)
        </button>
      </div>

      <input
        type="datetime-local"
        min={minDateTime}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        style={{ margin: 0 }}
      />
    </div>
  );
}

export default SafeUntil;
