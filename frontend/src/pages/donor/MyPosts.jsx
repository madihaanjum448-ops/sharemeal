import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function MyPosts() {
  const { authFetch } = useAuth();
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancellingId, setCancellingId] = useState(null);
  const [actionMessage, setActionMessage] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");

  const fetchListings = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await authFetch("/listings/my?limit=50");
      setListings(res.listings || []);
    } catch (err) {
      console.error("Failed to load listings:", err);
      setError(err.message || "Could not retrieve your listings.");
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  const handleCancel = async (listingId) => {
    if (!window.confirm("Are you sure you want to cancel this food listing?")) {
      return;
    }

    try {
      setCancellingId(listingId);
      setActionMessage("");

      await authFetch(`/listings/${listingId}/cancel`, {
        method: "POST",
      });

      setActionMessage("Listing cancelled successfully.");
      // Update local state
      setListings((prev) =>
        prev.map((item) =>
          item.id === listingId ? { ...item, status: "cancelled" } : item
        )
      );
    } catch (err) {
      console.error("Failed to cancel listing:", err);
      alert(err.message || "Could not cancel listing.");
    } finally {
      setCancellingId(null);
    }
  };

  const filteredListings = listings.filter((item) => {
    if (filterStatus === "all") return true;
    return item.status === filterStatus;
  });

  const formatDateTime = (isoString) => {
    if (!isoString) return "N/A";
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return isoString;
    }
  };

  const isExpired = (safeUntil) => {
    if (!safeUntil) return false;
    return new Date(safeUntil) < new Date();
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1>My Food Donations</h1>
          <p>Track your posted listings, claims, and collection status.</p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchListings}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
          <Link to="/donor" className="btn">
            + Donate Food
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
          <button
            type="button"
            onClick={fetchListings}
            className="btn-secondary btn-sm"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap" }}>
        {[
          { key: "all", label: `All (${listings.length})` },
          { key: "available", label: "Available" },
          { key: "claimed", label: "Claimed" },
          { key: "cancelled", label: "Cancelled" },
          { key: "completed", label: "Completed" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setFilterStatus(tab.key)}
            className={filterStatus === tab.key ? "btn btn-sm" : "btn-secondary btn-sm"}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && listings.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px" }}>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Loading your donations...</p>
        </div>
      ) : filteredListings.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <h3 style={{ marginBottom: "8px" }}>No donations found</h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "20px" }}>
            {filterStatus === "all"
              ? "You haven't posted any food donations yet."
              : `No donations with status "${filterStatus}".`}
          </p>
          <Link to="/donor" className="btn">
            Post Your First Donation
          </Link>
        </div>
      ) : (
        <div className="grid-cards">
          {filteredListings.map((item) => {
            const expired = isExpired(item.safe_until);
            const displayStatus = expired && item.status === "available" ? "expired" : item.status;

            return (
              <div key={item.id} className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px", gap: "8px" }}>
                    <h3 style={{ fontSize: "18px", margin: 0, color: "var(--text-main)" }}>
                      {item.title}
                    </h3>
                    <span className={`badge badge-${displayStatus}`}>
                      {displayStatus}
                    </span>
                  </div>

                  {item.description && (
                    <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "14px" }}>
                      {item.description}
                    </p>
                  )}

                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "14px" }}>
                    <span className={`badge badge-${item.food_category}`}>
                      {item.food_category === "human" ? "Human Food" : "Animal Feed"}
                    </span>
                    <span style={{ fontSize: "12px", background: "#f3f4f6", padding: "4px 8px", borderRadius: "4px" }}>
                      Qty: {item.quantity}
                    </span>
                    {item.servings && (
                      <span style={{ fontSize: "12px", background: "#f3f4f6", padding: "4px 8px", borderRadius: "4px" }}>
                        {item.servings} servings
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: "13px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div>
                      <strong>Safe until:</strong>{" "}
                      <span style={{ color: expired ? "var(--danger)" : "inherit" }}>
                        {formatDateTime(item.safe_until)} {expired ? "(Expired)" : ""}
                      </span>
                    </div>
                    <div>
                      <strong>Pickup Address:</strong> {item.pickup_address}
                    </div>
                    <div>
                      <strong>Posted:</strong> {formatDateTime(item.created_at)}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: "20px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
                  {item.status === "available" && !expired && (
                    <button
                      type="button"
                      onClick={() => handleCancel(item.id)}
                      disabled={cancellingId === item.id}
                      className="btn-outline-danger btn-sm"
                    >
                      {cancellingId === item.id ? "Cancelling..." : "Cancel Listing"}
                    </button>
                  )}
                  {item.status !== "available" && (
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Listing {item.status}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MyPosts;
