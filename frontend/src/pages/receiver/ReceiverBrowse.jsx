import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function ReceiverBrowse() {
  const { authFetch, profile } = useAuth();
  const navigate = useNavigate();

  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [categoryFilter, setCategoryFilter] = useState("");
  const [useLocation, setUseLocation] = useState(false);
  const [coords, setCoords] = useState(null);
  const [radiusKm, setRadiusKm] = useState(15);
  const [locLoading, setLocLoading] = useState(false);

  // Selected listing for modal
  const [selectedListing, setSelectedListing] = useState(null);
  const [claiming, setClaiming] = useState(false);
  const [claimError, setClaimError] = useState("");
  const [claimSuccess, setClaimSuccess] = useState(null);

  const fetchListings = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      let url = "/listings/?limit=50";
      if (categoryFilter) {
        url += `&food_category=${categoryFilter}`;
      }
      if (useLocation && coords) {
        url += `&lat=${coords.latitude}&lng=${coords.longitude}&radius_km=${radiusKm}`;
      }

      const res = await authFetch(url);
      setListings(res.listings || []);
    } catch (err) {
      console.error("Failed to load listings:", err);
      setError(err.message || "Could not retrieve food listings.");
    } finally {
      setLoading(false);
    }
  }, [authFetch, categoryFilter, useLocation, coords, radiusKm]);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  const handleToggleLocation = () => {
    if (!useLocation) {
      if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        return;
      }
      setLocLoading(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setCoords({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          });
          setUseLocation(true);
          setLocLoading(false);
        },
        (err) => {
          alert("Could not detect location. Please check browser permissions.");
          setLocLoading(false);
        }
      );
    } else {
      setUseLocation(false);
      setCoords(null);
    }
  };

  const handleClaim = async (listingId) => {
    setClaimError("");
    setClaimSuccess(null);

    if (profile?.approval_status !== "approved" || !profile?.is_verified) {
      setClaimError("Your account must be approved by an administrator before claiming food.");
      return;
    }

    try {
      setClaiming(true);

      const res = await authFetch("/claims/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listing_id: listingId }),
      });

      setClaimSuccess(res.claim || { message: "Food claimed successfully!" });

      // Refresh listings list
      fetchListings();
    } catch (err) {
      console.error("Claim failed:", err);
      setClaimError(err.message || "Failed to claim listing. It may already be claimed or expired.");
    } finally {
      setClaiming(false);
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

  const isApproved = profile?.approval_status === "approved" && profile?.is_verified;

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1>Available Food Donations</h1>
          <p>Browse fresh surplus food posted by verified donors near you.</p>
        </div>
        <button
          type="button"
          onClick={fetchListings}
          disabled={loading}
          className="btn-secondary"
        >
          {loading ? "Refreshing..." : "Refresh Listings"}
        </button>
      </div>

      {error && (
        <div className="alert alert-danger">
          <span>{error}</span>
          <button type="button" onClick={fetchListings} className="btn-secondary btn-sm">
            Try Again
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: "16px 20px", marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-main)" }}>
              Category:
            </span>
            {[
              { val: "", label: "All" },
              { val: "human", label: "Human Food" },
              { val: "animal", label: "Animal Feed" },
            ].map((cat) => (
              <button
                key={cat.val}
                type="button"
                onClick={() => setCategoryFilter(cat.val)}
                className={categoryFilter === cat.val ? "btn btn-sm" : "btn-secondary btn-sm"}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={handleToggleLocation}
              disabled={locLoading}
              className={useLocation ? "btn btn-sm" : "btn-secondary btn-sm"}
            >
              {locLoading ? "Locating..." : useLocation ? "Distance: Nearby (< " + radiusKm + " km)" : "Filter by Distance"}
            </button>

            {useLocation && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <label htmlFor="radius-select" style={{ margin: 0, fontSize: "13px" }}>Radius:</label>
                <select
                  id="radius-select"
                  aria-label="Radius"
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                  style={{ width: "auto", margin: 0, padding: "6px 10px" }}
                >
                  <option value={5}>5 km</option>
                  <option value={10}>10 km</option>
                  <option value={15}>15 km</option>
                  <option value={25}>25 km</option>
                  <option value={50}>50 km</option>
                </select>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Listings Grid */}
      {loading && listings.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px" }}>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Searching for available food donations...</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 20px" }}>
          <h3 style={{ marginBottom: "8px" }}>No food listings available right now</h3>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>
            {useLocation
              ? "No food found within " + radiusKm + " km of your location. Try expanding the radius or checking back soon."
              : "Check back soon as donors regularly post fresh surplus meals."}
          </p>
        </div>
      ) : (
        <div className="grid-cards">
          {listings.map((item) => (
            <div
              key={item.id}
              className="card"
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                transition: "transform 0.15s ease, box-shadow 0.15s ease",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px", gap: "8px" }}>
                  <h3 style={{ fontSize: "18px", margin: 0, color: "var(--text-main)" }}>
                    {item.title}
                  </h3>
                  <span className={`badge badge-${item.food_category}`}>
                    {item.food_category === "human" ? "Human" : "Animal"}
                  </span>
                </div>

                {item.description && (
                  <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "14px" }}>
                    {item.description}
                  </p>
                )}

                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "14px" }}>
                  <span style={{ fontSize: "12px", background: "#f3f4f6", padding: "4px 8px", borderRadius: "4px" }}>
                    Qty: {item.quantity}
                  </span>
                  {item.servings && (
                    <span style={{ fontSize: "12px", background: "#f3f4f6", padding: "4px 8px", borderRadius: "4px" }}>
                      {item.servings} servings
                    </span>
                  )}
                  {item.distance_km !== null && item.distance_km !== undefined && (
                    <span style={{ fontSize: "12px", background: "#e0f2fe", color: "#0369a1", padding: "4px 8px", borderRadius: "4px", fontWeight: 600 }}>
                      ~{item.distance_km} km away
                    </span>
                  )}
                </div>

                <div style={{ fontSize: "13px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div>
                    <strong>Safe until:</strong> {formatDateTime(item.safe_until)}
                  </div>
                  <div style={{ fontSize: "12px", color: "#6b7280" }}>
                    Pickup location unlocked upon claim
                  </div>
                </div>
              </div>

              <div style={{ marginTop: "20px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="badge badge-available">Available</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedListing(item);
                    setClaimError("");
                    setClaimSuccess(null);
                  }}
                  className="btn btn-sm"
                >
                  View &amp; Claim
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Listing Detail & Claim Modal */}
      {selectedListing && (
        <div className="modal-overlay" onClick={() => setSelectedListing(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedListing.title}</h2>
              <button
                type="button"
                onClick={() => setSelectedListing(null)}
                className="close-btn"
              >
                &times;
              </button>
            </div>

            {claimSuccess ? (
              <div className="alert alert-success" style={{ flexDirection: "column", alignItems: "flex-start" }}>
                <h4 style={{ margin: "0 0 6px 0", color: "var(--primary)" }}>
                  Listing Claimed Successfully!
                </h4>
                <p style={{ margin: "0 0 14px 0", fontSize: "14px" }}>
                  You have successfully claimed this food donation. The pickup address and coordinates are now unlocked in your Claims tab.
                </p>
                <button
                  type="button"
                  onClick={() => navigate("/receiver/claims")}
                  className="btn"
                >
                  View Pickup Details in My Claims
                </button>
              </div>
            ) : (
              <div>
                <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
                  <span className={`badge badge-${selectedListing.food_category}`}>
                    {selectedListing.food_category === "human" ? "Human Food" : "Animal Feed"}
                  </span>
                  <span className="badge badge-available">Available</span>
                  {selectedListing.distance_km && (
                    <span className="badge" style={{ background: "#e0f2fe", color: "#0369a1" }}>
                      ~{selectedListing.distance_km} km away
                    </span>
                  )}
                </div>

                {selectedListing.description && (
                  <div style={{ marginBottom: "16px" }}>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Description</label>
                    <p style={{ margin: 0, fontSize: "14px" }}>{selectedListing.description}</p>
                  </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "20px" }}>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Quantity</label>
                    <div style={{ fontSize: "15px", fontWeight: 600 }}>{selectedListing.quantity}</div>
                  </div>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Servings</label>
                    <div style={{ fontSize: "15px", fontWeight: 600 }}>{selectedListing.servings || "N/A"}</div>
                  </div>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Safe Until</label>
                    <div style={{ fontSize: "14px" }}>{formatDateTime(selectedListing.safe_until)}</div>
                  </div>
                  <div>
                    <label style={{ color: "var(--text-muted)", fontSize: "12px" }}>Approx. Location</label>
                    <div style={{ fontSize: "14px" }}>
                      {selectedListing.approx_latitude && selectedListing.approx_longitude
                        ? `${selectedListing.approx_latitude}, ${selectedListing.approx_longitude}`
                        : "Area shared upon claim"}
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    background: "#f0fdf4",
                    border: "1px solid #bbf7d0",
                    borderRadius: "8px",
                    padding: "14px",
                    marginBottom: "20px",
                    fontSize: "13px",
                    color: "#166534",
                  }}
                >
                  <strong>Donor Privacy Protection:</strong> Exact pickup address and GPS coordinates are unlocked as soon as you confirm this claim. Please ensure you can collect the food before the safe-until time.
                </div>

                {!isApproved && (
                  <div className="alert alert-warning" style={{ fontSize: "13px" }}>
                    Your receiver account is pending administrator verification. Food claiming is disabled until verified.
                  </div>
                )}

                {claimError && (
                  <div className="alert alert-danger" style={{ fontSize: "13px" }}>
                    {claimError}
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "24px" }}>
                  <button
                    type="button"
                    onClick={() => setSelectedListing(null)}
                    className="btn-secondary"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    onClick={() => handleClaim(selectedListing.id)}
                    disabled={claiming || !isApproved}
                    className="btn"
                  >
                    {claiming ? "Claiming Food..." : "Claim This Food"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ReceiverBrowse;
