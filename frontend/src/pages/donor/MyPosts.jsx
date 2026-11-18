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
                {editingId === item.id && (
  <div style={{ marginTop: "20px", padding: "16px", background: "var(--bg-secondary)", borderRadius: "8px" }}>
    <h3>Edit Donation</h3>

    <label>Food Title</label>
    <input
      name="title"
      value={editData.title}
      onChange={handleEditChange}
      minLength={3}
      maxLength={120}
      required
    />

    <label>Description</label>
    <textarea
      name="description"
      value={editData.description}
      onChange={handleEditChange}
    />

    <label>Food Category</label>
    <select
      name="food_category"
      value={editData.food_category}
      onChange={handleEditChange}
    >
      <option value="human">Human Food</option>
      <option value="animal">Animal Feed</option>
    </select>

    <label>Quantity</label>
    <input
      name="quantity"
      value={editData.quantity}
      onChange={handleEditChange}
      required
    />

    <label>Servings</label>
    <input
      type="number"
      name="servings"
      min="1"
      value={editData.servings}
      onChange={handleEditChange}
    />

    <label>Pickup Address</label>
    <textarea
      name="pickup_address"
      value={editData.pickup_address}
      onChange={handleEditChange}
      required
    />

    <label>Food Available Until</label>
    <input
      type="datetime-local"
      name="safe_until"
      value={editData.safe_until}
      onChange={handleEditChange}
      required
    />

    <div style={{ display: "flex", gap: "10px", marginTop: "16px" }}>
      <button
        type="button"
        className="btn"
        onClick={() => handleUpdate(item.id)}
        disabled={savingId === item.id}
      >
        {savingId === item.id ? "Saving..." : "Save Changes"}
      </button>

      <button
        type="button"
        className="btn-secondary"
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
                <div style={{ marginTop: "20px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
                  
                  {item.status === "available" && !expired && (
  <button
    type="button"
    onClick={() => handleEdit(item)}
    className="btn btn-sm"
  >
    Edit Donation
  </button>
)}
                    <button
                      type="button"
                      onClick={() => handleCancel(item.id)}
                      disabled={cancellingId === item.id}
                      className="btn-outline-danger btn-sm"
                    >
                      {cancellingId === item.id ? "Cancelling..." : "Cancel Listing"}
                    </button>
                  
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
