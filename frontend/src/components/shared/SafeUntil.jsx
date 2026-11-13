import { useState } from "react";

function SafeUntil() {
  const [safeUntil, setSafeUntil] = useState("");

  return (
    <div>
      <h3>Food Available Until</h3>
      <p>Select the date and time until which this listing is available.</p>

      <input
        type="datetime-local"
        value={safeUntil}
        onChange={(e) => setSafeUntil(e.target.value)}
      />

      <p>
        Selected time: {safeUntil || "No date and time selected"}
      </p>
    </div>
  );
}

export default SafeUntil;