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
    if (!window.confirm("Are you sure you want to cancel this food claim? The food will become available to other receivers.")) {
      return;
    }

    try {
      setCancellingId(claimId);
      setActionMessage("");

      await authFetch(`/claims/${claimId}/cancel`, {
        method: "POST",
      });

      setActionMessage("Claim cancelled successfully.");
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
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1>My Food Claims</h1>
          <p>View your active and previous food claims, pickup instructions, and addresses.</p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchClaims}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? "Refreshing..." : "Refresh"}
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
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap" }}>
        {[
          { key: "all", label: `All Claims (${claims.length})` },
          { key: "active", label: "Active" },
          { key: "cancelled", label: "Cancelled" },
          { key: "expired", label: "Expired" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setStatusFilter(tab.key)}
            className={statusFilter === tab.key ? "btn btn-sm" : "btn-secondary btn-sm"}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && claims.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px" }}>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Loading your claims...</p>
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <h3 style={{ marginBottom: "8px" }}>No food claims found</h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "20px" }}>
            {statusFilter === "all"
              ? "You haven't claimed any food yet."
              : `No claims with status "${statusFilter}".`}
          </p>
          <Link to="/receiver" className="btn">
            Browse Available Food
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {filteredClaims.map(({ claim, listing }) => {
            const expired = isExpired(claim.expires_at);
            const statusDisplay = expired && claim.status === "active" ? "expired" : claim.status;
            const hasPickupAddress = Boolean(listing?.pickup_address);

            return (
              <div key={claim.id} className="card" style={{ borderLeft: statusDisplay === "active" ? "5px solid var(--primary)" : "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px", marginBottom: "14px" }}>
                  <div>
                    <h2 style={{ fontSize: "20px", margin: "0 0 6px 0", color: "var(--text-main)" }}>
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
                        Claimed: {formatDateTime(claim.claimed_at)}
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

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Quantity</label>
                    <div style={{ fontSize: "14px", fontWeight: 600 }}>{listing?.quantity || "N/A"}</div>
                  </div>
                  {listing?.servings && (
                    <div>
                      <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Servings</label>
                      <div style={{ fontSize: "14px", fontWeight: 600 }}>{listing.servings}</div>
                    </div>
                  )}
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Food Safe Until</label>
                    <div style={{ fontSize: "14px" }}>{formatDateTime(listing?.safe_until)}</div>
                  </div>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Claim Window Expires</label>
                    <div style={{ fontSize: "14px", fontWeight: statusDisplay === "active" ? 600 : "normal", color: statusDisplay === "active" ? "var(--warning)" : "inherit" }}>
                      {formatDateTime(claim.expires_at)}
                    </div>
                  </div>
                </div>

                {/* Pickup Address & Location - Revealed upon active unexpired claim */}
                {hasPickupAddress ? (
                  <div
                    style={{
                      background: "#f0fdf4",
                      border: "1px solid #bbf7d0",
                      borderRadius: "8px",
                      padding: "16px",
                      marginTop: "12px",
                    }}
                  >
                    <h4 style={{ margin: "0 0 8px 0", color: "#166534", fontSize: "14px", fontWeight: 700 }}>
                      Unlocked Pickup Location &amp; Instructions
                    </h4>
                    <p style={{ margin: "0 0 10px 0", fontSize: "15px", color: "var(--text-main)", fontWeight: 500 }}>
                      {listing.pickup_address}
                    </p>
                    {listing.latitude && listing.longitude && (
                      <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap", fontSize: "13px" }}>
                        <span style={{ color: "var(--text-muted)" }}>
                          Coordinates: {listing.latitude.toFixed(5)}, {listing.longitude.toFixed(5)}
                        </span>
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${listing.latitude},${listing.longitude}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-secondary btn-sm"
                          style={{ textDecoration: "none" }}
                        >
                          Open in Google Maps
                        </a>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "10px" }}>
                    {statusDisplay === "expired"
                      ? "This claim window has expired. Pickup details are no longer available."
                      : "Pickup details are only revealed for active, unexpired claims."}
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
