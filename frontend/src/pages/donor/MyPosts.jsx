import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function toLocalDateTime(value) {
  if (!value) return "";

  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;

  return new Date(date.getTime() - offset)
    .toISOString()
    .slice(0, 16);
}

function MyPosts() {
  const { authFetch } = useAuth();
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancellingId, setCancellingId] = useState(null);
  const [actionMessage, setActionMessage] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [editingId, setEditingId] = useState(null);
  const [savingId, setSavingId] = useState(null);
  const [editData, setEditData] = useState({});

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

  const handleEdit = (item) => {
    setEditingId(item.id);

    setEditData({
      title: item.title || "",
      description: item.description || "",
      food_category: item.food_category || "human",
      quantity: item.quantity || "",
      servings: item.servings ?? "",
      pickup_address: item.pickup_address || "",
      safe_until: toLocalDateTime(item.safe_until),
    });

    setError("");
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;

    setEditData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleUpdate = async (listingId) => {
    if (editData.title.trim().length < 3) {
      setError("Title must be at least 3 characters.");
      return;
    }

    if (!editData.quantity.trim()) {
      setError("Quantity is required.");
      return;
    }

    if (editData.pickup_address.trim().length < 5) {
      setError("Pickup address must be at least 5 characters.");
      return;
    }

    const safeUntilDate = new Date(editData.safe_until);

    if (!editData.safe_until || isNaN(safeUntilDate.getTime()) || safeUntilDate <= new Date()) {
      setError("Food availability time must be in the future.");
      return;
    }

    if (editData.servings && Number(editData.servings) <= 0) {
      setError("Servings must be greater than zero.");
      return;
    }

    const listingData = {
      title: editData.title.trim(),
      description: editData.description.trim() || null,
      food_category: editData.food_category,
      quantity: editData.quantity.trim(),
      servings: editData.servings ? Number(editData.servings) : null,
      pickup_address: editData.pickup_address.trim(),
      safe_until: safeUntilDate.toISOString(),
    };

    try {
      setSavingId(listingId);
      setError("");
      setActionMessage("");

      await authFetch(`/listings/${listingId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(listingData),
      });

      setListings((prev) =>
        prev.map((item) =>
          item.id === listingId ? { ...item, ...listingData } : item
        )
      );

      setEditingId(null);
      setEditData({});
      setActionMessage("Donation updated successfully.");
    } catch (err) {
      setError(err.message || "Failed to update donation.");
    } finally {
      setSavingId(null);
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
      {/* Page Header */}
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1>My Food Donations</h1>
          <p>Track your active listings, manage pickup details, and monitor receiver claims.</p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={fetchListings}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? "Refreshing..." : "↻ Refresh"}
          </button>
          <Link to="/donor" className="btn">
            + Post New Donation
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
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        {[
          { key: "all", label: `All (${listings.length})` },
          { key: "available", label: `Available (${listings.filter(i => i.status === "available").length})` },
          { key: "claimed", label: `Claimed (${listings.filter(i => i.status === "claimed").length})` },
          { key: "cancelled", label: `Cancelled (${listings.filter(i => i.status === "cancelled").length})` },
          { key: "completed", label: `Completed (${listings.filter(i => i.status === "completed").length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setFilterStatus(tab.key)}
            className={filterStatus === tab.key ? "btn btn-sm" : "btn-secondary btn-sm"}
            style={{ borderRadius: "var(--radius-pill)" }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && listings.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "15px" }}>
            Loading your food listings...
          </p>
        </div>
      ) : filteredListings.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "56px 24px" }}>
          <div style={{ fontSize: "36px", marginBottom: "12px" }}>🍲</div>
          <h3 style={{ fontSize: "20px", marginBottom: "8px", color: "var(--emerald-900)" }}>
            No donations found
          </h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "24px", maxWidth: "420px", margin: "0 auto 24px auto" }}>
            {filterStatus === "all"
              ? "You have not published any food listings yet. Start sharing surplus meals to support your community."
              : `No food listings found with status "${filterStatus}".`}
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
            const isEditing = editingId === item.id;

            return (
              <div
                key={item.id}
                className="card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  borderLeft: displayStatus === "available" ? "4px solid var(--primary)" : displayStatus === "claimed" ? "4px solid var(--info)" : "1px solid var(--border)",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px", gap: "10px" }}>
                    <h3 style={{ fontSize: "18px", margin: 0, color: "var(--emerald-900)", lineHeight: 1.3 }}>
                      {item.title}
                    </h3>
                    <span className={`badge badge-${displayStatus}`}>
                      {displayStatus}
                    </span>
                  </div>

                  {item.description && (
                    <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "14px", lineHeight: 1.5 }}>
                      {item.description}
                    </p>
                  )}

                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
                    <span className={`badge badge-${item.food_category}`}>
                      {item.food_category === "human" ? "Human Food" : "Animal Feed"}
                    </span>
                    <span style={{ fontSize: "12px", background: "var(--bg-cream)", color: "var(--text-main)", padding: "4px 10px", borderRadius: "var(--radius-pill)", border: "1px solid var(--border)", fontWeight: 600 }}>
                      Qty: {item.quantity}
                    </span>
                    {item.servings && (
                      <span style={{ fontSize: "12px", background: "var(--bg-cream)", color: "var(--text-main)", padding: "4px 10px", borderRadius: "var(--radius-pill)", border: "1px solid var(--border)", fontWeight: 600 }}>
                        {item.servings} servings
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: "13px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div>
                      <strong style={{ color: "var(--text-main)" }}>Safe until:</strong>{" "}
                      <span style={{ color: expired ? "var(--red-accent)" : "inherit", fontWeight: expired ? 700 : "normal" }}>
                        {formatDateTime(item.safe_until)} {expired ? "(Expired)" : ""}
                      </span>
                    </div>
                    <div>
                      <strong style={{ color: "var(--text-main)" }}>Pickup Address:</strong> {item.pickup_address}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-light)" }}>
                      Posted on {formatDateTime(item.created_at)}
                    </div>
                  </div>
                </div>

                {/* Inline Edit Donation Mode */}
                {isEditing && (
                  <div
                    style={{
                      marginTop: "20px",
                      padding: "20px",
                      background: "var(--bg-cream)",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--emerald-200)",
                    }}
                  >
                    <h4 style={{ margin: "0 0 14px 0", color: "var(--emerald-900)", fontSize: "16px" }}>
                      Edit Food Listing
                    </h4>

                    <label style={{ fontSize: "12px" }}>Food Title *</label>
                    <input
                      name="title"
                      value={editData.title}
                      onChange={handleEditChange}
                      minLength={3}
                      maxLength={120}
                      required
                      style={{ marginBottom: "12px" }}
                    />

                    <label style={{ fontSize: "12px" }}>Description</label>
                    <textarea
                      name="description"
                      value={editData.description}
                      onChange={handleEditChange}
                      style={{ marginBottom: "12px", minHeight: "70px" }}
                    />

                    <label style={{ fontSize: "12px" }}>Food Category *</label>
                    <select
                      name="food_category"
                      value={editData.food_category}
                      onChange={handleEditChange}
                      style={{ marginBottom: "12px" }}
                    >
                      <option value="human">Human Food</option>
                      <option value="animal">Animal Feed</option>
                    </select>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "12px" }}>
                      <div>
                        <label style={{ fontSize: "12px" }}>Quantity *</label>
                        <input
                          name="quantity"
                          value={editData.quantity}
                          onChange={handleEditChange}
                          required
                          style={{ marginBottom: 0 }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "12px" }}>Servings</label>
                        <input
                          type="number"
                          name="servings"
                          min="1"
                          value={editData.servings}
                          onChange={handleEditChange}
                          style={{ marginBottom: 0 }}
                        />
                      </div>
                    </div>

                    <label style={{ fontSize: "12px" }}>Pickup Address *</label>
                    <textarea
                      name="pickup_address"
                      value={editData.pickup_address}
                      onChange={handleEditChange}
                      required
                      style={{ marginBottom: "12px", minHeight: "60px" }}
                    />

                    <label style={{ fontSize: "12px" }}>Food Available Until *</label>
                    <input
                      type="datetime-local"
                      name="safe_until"
                      value={editData.safe_until}
                      onChange={handleEditChange}
                      required
                      style={{ marginBottom: "16px" }}
                    />

                    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => handleUpdate(item.id)}
                        disabled={savingId === item.id}
                      >
                        {savingId === item.id ? "Saving Changes..." : "Save Changes"}
                      </button>

                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => {
                          setEditingId(null);
                          setEditData({});
                          setError("");
                        }}
                        disabled={savingId === item.id}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Card Actions Footer */}
                <div
                  style={{
                    marginTop: "20px",
                    paddingTop: "16px",
                    borderTop: "1px solid var(--border-subtle)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", gap: "8px" }}>
                    {item.status === "available" && !expired && !isEditing && (
                      <button
                        type="button"
                        onClick={() => handleEdit(item)}
                        className="btn btn-sm"
                      >
                        Edit Donation
                      </button>
                    )}
                  </div>

                  <div>
                    {item.status === "available" && (
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
                      <span style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                        Listing is {item.status}
                      </span>
                    )}
                  </div>
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
