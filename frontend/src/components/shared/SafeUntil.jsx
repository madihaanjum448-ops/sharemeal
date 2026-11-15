function SafeUntil({ value, onChange }) {
  // Sets time relative to current local time
  const handlePreset = (hours) => {
    const d = new Date();
    d.setHours(d.getHours() + hours);
    // Format to YYYY-MM-DDTHH:MM for datetime-local
    const pad = (n) => String(n).padStart(2, "0");
    const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    onChange(formatted);
  };

  // Min datetime is current minute
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const minDateTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;

  return (
    <div style={{ marginBottom: "20px" }}>
      <label style={{ fontWeight: 600, marginBottom: "6px" }}>
        Safe Until (Date & Time) *
      </label>
      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
        Until when is this food safe and fresh for pickup?
      </span>

      <div style={{ display: "flex", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => handlePreset(2)}
          className="btn-secondary btn-sm"
        >
          +2 Hours
        </button>
        <button
          type="button"
          onClick={() => handlePreset(4)}
          className="btn-secondary btn-sm"
        >
          +4 Hours
        </button>
        <button
          type="button"
          onClick={() => handlePreset(8)}
          className="btn-secondary btn-sm"
        >
          +8 Hours
        </button>
        <button
          type="button"
          onClick={() => handlePreset(24)}
          className="btn-secondary btn-sm"
        >
          +24 Hours
        </button>
      </div>

      <input
        type="datetime-local"
        min={minDateTime}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
      />
    </div>
  );
}

export default SafeUntil;
