import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function ReceiverClaims() {
  const { authFetch } = useAuth();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancellingId, setCancellingId] = useState(null);
  const [actionMessage, setActionMessage] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const fetchClaims = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await authFetch("/claims/my");
      setClaims(res.claims || []);
    } catch (err) {
      console.error("Failed to fetch claims:", err);
      setError(err.message || "Could not retrieve your food claims.");
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    fetchClaims();
  }, [fetchClaims]);

  const handleCancelClaim = async (claimId) => {
    if (!window.confirm("Are you sure you want to cancel this food claim? The food will become available again to other community receivers.")) {
      return;
    }

    try {
      setCancellingId(claimId);
      setActionMessage("");

      await authFetch(`/claims/${claimId}/cancel`, {
        method: "POST",
      });

      setActionMessage("Claim cancelled successfully. The listing has been released.");
      // Update local state
      setClaims((prev) =>
        prev.map((c) =>
          c.claim.id === claimId
            ? { ...c, claim: { ...c.claim, status: "cancelled" } }
            : c
        )
      );
    } catch (err) {
      console.error("Failed to cancel claim:", err);
      alert(err.message || "Could not cancel claim.");
    } finally {
      setCancellingId(null);
    }
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return "N/A";
    try {
      return new Date(isoString).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return isoString;
    }
  };

  const isExpired = (expiresAt) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  const filteredClaims = claims.filter((item) => {
    const status = item.claim.status;
    const expired = isExpired(item.claim.expires_at);
    const effectiveStatus = expired && status === "active" ? "expired" : status;

    if (statusFilter === "all") return true;
    return effectiveStatus === statusFilter;
  });

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "var(--emerald-50)", color: "var(--primary)", padding: "4px 12px", borderRadius: "var(--radius-pill)", fontSize: "12px", fontWeight: 700, marginBottom: "8px", border: "1px solid var(--emerald-100)" }}>
            <span>📦 Claim Management</span>
          </div>
          <h1>My Food Claims</h1>
          <p>View your active food claims, unlocked pickup instructions, and navigation details.</p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={fetchClaims}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? "Refreshing..." : "↻ Refresh"}
          </button>
          <Link to="/receiver" className="btn">
            Browse More Food
          </Link>
        </div>
      </div>

      {actionMessage && (
        <div className="alert alert-success">
          <span>{actionMessage}</span>
          <button
            type="button"
            onClick={() => setActionMessage("")}
            className="close-btn"
          >
            &times;
          </button>
        </div>
      )}

      {error && (
        <div className="alert alert-danger">
          <span>{error}</span>
          <button type="button" onClick={fetchClaims} className="btn-secondary btn-sm">
            Try Again
          </button>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        {[
          { key: "all", label: `All Claims (${claims.length})` },
          { key: "active", label: `Active (${claims.filter(c => c.claim.status === "active" && !isExpired(c.claim.expires_at)).length})` },
          { key: "cancelled", label: `Cancelled (${claims.filter(c => c.claim.status === "cancelled").length})` },
          { key: "expired", label: `Expired (${claims.filter(c => isExpired(c.claim.expires_at) || c.claim.status === "expired").length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setStatusFilter(tab.key)}
            className={statusFilter === tab.key ? "btn btn-sm" : "btn-secondary btn-sm"}
            style={{ borderRadius: "var(--radius-pill)" }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && claims.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "15px" }}>Loading your food claims...</p>
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "56px 24px" }}>
          <div style={{ fontSize: "36px", marginBottom: "12px" }}>📦</div>
          <h3 style={{ fontSize: "20px", marginBottom: "8px", color: "var(--emerald-900)" }}>
            No food claims found
          </h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "24px", maxWidth: "420px", margin: "0 auto 24px auto" }}>
            {statusFilter === "all"
              ? "You haven't claimed any food donations yet. Browse available listings to rescue surplus meals."
              : `No food claims found with status "${statusFilter}".`}
          </p>
          <Link to="/receiver" className="btn">
            Browse Available Food
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {filteredClaims.map(({ claim, listing }) => {
            const expired = isExpired(claim.expires_at);
            const statusDisplay = expired && claim.status === "active" ? "expired" : claim.status;
            const hasPickupAddress = Boolean(listing?.pickup_address);

            return (
              <div
                key={claim.id}
                className="card"
                style={{
                  borderLeft: statusDisplay === "active" ? "5px solid var(--primary)" : "1px solid var(--border)",
                  padding: "28px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
                  <div>
                    <h2 style={{ fontSize: "20px", margin: "0 0 6px 0", color: "var(--emerald-900)" }}>
                      {listing?.title || "Food Item"}
                    </h2>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                      <span className={`badge badge-${statusDisplay}`}>
                        {statusDisplay}
                      </span>
                      {listing?.food_category && (
                        <span className={`badge badge-${listing.food_category}`}>
                          {listing.food_category === "human" ? "Human Food" : "Animal Feed"}
                        </span>
                      )}
                      <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                        Claimed on {formatDateTime(claim.claimed_at)}
                      </span>
                    </div>
                  </div>

                  {statusDisplay === "active" && (
                    <button
                      type="button"
                      onClick={() => handleCancelClaim(claim.id)}
                      disabled={cancellingId === claim.id}
                      className="btn-outline-danger btn-sm"
                    >
                      {cancellingId === claim.id ? "Cancelling..." : "Cancel Claim"}
                    </button>
                  )}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "20px", background: "var(--bg-cream)", padding: "16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Quantity</label>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--emerald-900)" }}>{listing?.quantity || "N/A"}</div>
                  </div>
                  {listing?.servings && (
                    <div>
                      <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Servings</label>
                      <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--emerald-900)" }}>{listing.servings}</div>
                    </div>
                  )}
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Food Safe Until</label>
                    <div style={{ fontSize: "14px", color: "var(--text-main)", fontWeight: 600 }}>{formatDateTime(listing?.safe_until)}</div>
                  </div>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "2px" }}>Claim Window Closes</label>
                    <div style={{ fontSize: "14px", fontWeight: statusDisplay === "active" ? 700 : "normal", color: statusDisplay === "active" ? "var(--warning)" : "inherit" }}>
                      {formatDateTime(claim.expires_at)}
                    </div>
                  </div>
                </div>

                {/* Pickup Address & Location - Revealed upon active unexpired claim */}
                {hasPickupAddress ? (
                  <div
                    style={{
                      background: "var(--emerald-50)",
                      border: "1px solid var(--emerald-200)",
                      borderRadius: "var(--radius-md)",
                      padding: "20px",
                      marginTop: "16px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                      <span style={{ fontSize: "16px" }}>🔓</span>
                      <h4 style={{ margin: 0, color: "var(--emerald-900)", fontSize: "15px", fontWeight: 700 }}>
                        Unlocked Pickup Location &amp; Instructions
                      </h4>
                    </div>
                    <p style={{ margin: "0 0 14px 0", fontSize: "15px", color: "var(--text-main)", fontWeight: 600, lineHeight: 1.5 }}>
                      {listing.pickup_address}
                    </p>
                    {listing.latitude && listing.longitude && (
                      <div style={{ display: "flex", gap: "14px", alignItems: "center", flexWrap: "wrap", fontSize: "13px" }}>
                        <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>
                          GPS Coordinates: {listing.latitude.toFixed(5)}, {listing.longitude.toFixed(5)}
                        </span>
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${listing.latitude},${listing.longitude}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-secondary btn-sm"
                          style={{ textDecoration: "none" }}
                        >
                          🗺️ Open in Google Maps
                        </a>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "12px" }}>
                    {statusDisplay === "expired"
                      ? "⚠️ This claim window has expired. Pickup details are no longer active."
                      : "Pickup details are only unlocked for active, unexpired food claims."}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ReceiverClaims;
