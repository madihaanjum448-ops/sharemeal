import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import FoodCategory from "../../components/shared/FoodCategory";
import HygieneChecklist from "../../components/shared/HygieneChecklist";
import MapPicker from "../../components/shared/MapPicker";
import PhotoUpload from "../../components/shared/PhotoUpload";
import SafeUntil from "../../components/shared/SafeUntil";

function DonorPostForm() {
  const { authFetch } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    food_category: "human",
    quantity: "",
    servings: "",
    pickup_address: "",
    latitude: null,
    longitude: null,
    safe_until: "",
  });

  const [hygieneConfirmed, setHygieneConfirmed] = useState(false);
  const [photoPreview, setPhotoPreview] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleLocationSelect = ({ latitude, longitude }) => {
    setFormData((prev) => ({
      ...prev,
      latitude,
      longitude,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess(null);

    // Frontend validations matching backend Pydantic schema
    if (!formData.title.trim() || formData.title.trim().length < 3) {
      setError("Title must be at least 3 characters long.");
      return;
    }

    if (!formData.food_category) {
      setError("Please select a food category (Human or Animal).");
      return;
    }

    if (!formData.quantity.trim()) {
      setError("Quantity is required (e.g. 5 kg or 10 boxes).");
      return;
    }

    if (!formData.pickup_address.trim() || formData.pickup_address.trim().length < 5) {
      setError("Pickup address must be at least 5 characters.");
      return;
    }

    if (formData.latitude === null || formData.longitude === null) {
      setError("Please select a pickup location on the map.");
      return;
    }

    if (!formData.safe_until) {
      setError("Please specify the date and time until which food is safe.");
      return;
    }

    const safeUntilDate = new Date(formData.safe_until);
    if (isNaN(safeUntilDate.getTime()) || safeUntilDate <= new Date()) {
      setError("Safe-until date and time must be strictly in the future.");
      return;
    }

    if (!hygieneConfirmed) {
      setError("Please verify and check all 4 hygiene checklist requirements.");
      return;
    }

    // Build payload matching FoodListingCreate
    const payload = {
      title: formData.title.trim(),
      description: formData.description.trim() || null,
      food_category: formData.food_category,
      quantity: formData.quantity.trim(),
      servings: formData.servings ? parseInt(formData.servings, 10) : null,
      pickup_address: formData.pickup_address.trim(),
      latitude: parseFloat(formData.latitude),
      longitude: parseFloat(formData.longitude),
      safe_until: safeUntilDate.toISOString(),
    };

    try {
      setLoading(true);

      const res = await authFetch("/listings/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      setSuccess(res.listing || { title: payload.title });

      // Reset form
      setFormData({
        title: "",
        description: "",
        food_category: "human",
        quantity: "",
        servings: "",
        pickup_address: "",
        latitude: null,
        longitude: null,
        safe_until: "",
      });
      setPhotoPreview(null);
    } catch (err) {
      console.error("Listing creation failed:", err);
      setError(err.message || "Failed to create food listing. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: "860px", margin: "0 auto", padding: "36px" }}>
      <div style={{ marginBottom: "28px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "18px" }}>
        <h2 style={{ fontSize: "24px", color: "var(--emerald-900)", marginBottom: "6px" }}>
          Post Food Donation
        </h2>
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "14px" }}>
          Fill in the details below to share surplus food with verified receivers in your community.
        </p>
      </div>

      {success && (
        <div className="alert alert-success" style={{ flexDirection: "column", alignItems: "flex-start", padding: "18px" }}>
          <div style={{ fontWeight: 800, fontSize: "15px", marginBottom: "4px" }}>
            🎉 Food Listing Posted Successfully!
          </div>
          <p style={{ margin: "0 0 14px 0", fontSize: "14px", color: "var(--emerald-900)" }}>
            Your donation <strong>&quot;{success.title}&quot;</strong> is now active and visible to nearby verified community receivers.
          </p>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => navigate("/donor/posts")}
              className="btn btn-sm"
            >
              View in My Posts
            </button>
            <button
              type="button"
              onClick={() => setSuccess(null)}
              className="btn-secondary btn-sm"
            >
              Post Another Donation
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "24px" }}>
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Section 1: Food Details */}
        <div style={{ marginBottom: "24px" }}>
          <label htmlFor="title">Food Title *</label>
          <input
            id="title"
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="e.g. Fresh vegetable curry, 20 meal packs, or artisan bread loaves"
            required
          />

          <label htmlFor="description">Description (Optional)</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Describe ingredients, allergens, preparation timestamp, or packaging details..."
          />

          <FoodCategory
            value={formData.food_category}
            onChange={(val) => setFormData((prev) => ({ ...prev, food_category: val }))}
          />
        </div>

        {/* Section 2: Quantity & Availability */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "20px", marginBottom: "24px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label htmlFor="quantity">Quantity &amp; Units *</label>
              <input
                id="quantity"
                type="text"
                name="quantity"
                value={formData.quantity}
                onChange={handleChange}
                placeholder="e.g. 5 kg, 12 boxes, or 3 trays"
                required
              />
            </div>

            <div>
              <label htmlFor="servings">Estimated Servings (Optional)</label>
              <input
                id="servings"
                type="number"
                name="servings"
                min="1"
                value={formData.servings}
                onChange={handleChange}
                placeholder="e.g. 15"
              />
            </div>
          </div>

          <SafeUntil
            value={formData.safe_until}
            onChange={(val) => setFormData((prev) => ({ ...prev, safe_until: val }))}
          />
        </div>

        {/* Section 3: Pickup Location */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "20px", marginBottom: "24px" }}>
          <label htmlFor="pickup_address">Complete Pickup Address *</label>
          <textarea
            id="pickup_address"
            name="pickup_address"
            value={formData.pickup_address}
            onChange={handleChange}
            placeholder="Street address, building name, floor/unit, and pickup instructions (e.g. ring back kitchen door)..."
            required
          />

          <MapPicker
            initialPosition={
              formData.latitude && formData.longitude
                ? { latitude: formData.latitude, longitude: formData.longitude }
                : null
            }
            onLocationSelect={handleLocationSelect}
          />

          <PhotoUpload
            previewUrl={photoPreview}
            onPhotoSelect={(_file, url) => setPhotoPreview(url)}
            onPhotoClear={() => setPhotoPreview(null)}
          />
        </div>

        {/* Section 4: Safety & Confirmation */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "20px" }}>
          <HygieneChecklist onHygieneConfirmed={setHygieneConfirmed} />

          <button
            type="submit"
            disabled={loading || !hygieneConfirmed}
            className="btn btn-lg"
            style={{ width: "100%", marginTop: "8px" }}
          >
            {loading ? "Publishing Food Donation..." : "Publish Food Donation"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default DonorPostForm;
