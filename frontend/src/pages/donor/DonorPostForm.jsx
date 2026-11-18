
import { useState } from "react";
import MapPicker from "../../components/shared/MapPicker";
import { useAuth } from "../../context/AuthContext";
import { createListing } from "../../services/listingService";

function DonorPostForm() {
  const { authFetch } = useAuth();

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    food_category: "",
    quantity: "",
    servings: "",
    pickup_address: "",
    latitude: "",
    longitude: "",
    safe_until: "",
  });

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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
      latitude: latitude.toString(),
      longitude: longitude.toString(),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setMessage("");
    setError("");

    if (!formData.latitude || !formData.longitude) {
      setError("Please select a pickup location on the map.");
      return;
    }

    if (new Date(formData.safe_until) <= new Date()) {
      setError("Food availability time must be in the future.");
      return;
    }

    const listingData = {
      title: formData.title.trim(),
      description: formData.description.trim() || null,
      food_category: formData.food_category,
      quantity: formData.quantity.trim(),
      servings: formData.servings
        ? Number(formData.servings)
        : null,
      pickup_address: formData.pickup_address.trim(),
      latitude: Number(formData.latitude),
      longitude: Number(formData.longitude),
      safe_until: new Date(formData.safe_until).toISOString(),
    };

    try {
      setSubmitting(true);

      await createListing(listingData, authFetch);

      setMessage("Food donation posted successfully!");

      setFormData({
        title: "",
        description: "",
        food_category: "",
        quantity: "",
        servings: "",
        pickup_address: "",
        latitude: "",
        longitude: "",
        safe_until: "",
      });
    } catch (err) {
      setError(err.message || "Failed to post donation. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1>Donate Food</h1>
      <p>Share surplus food with someone who needs it.</p>

      <form onSubmit={handleSubmit}>
        <label>Food Title</label>
        <input
          type="text"
          name="title"
          value={formData.title}
          onChange={handleChange}
          placeholder="e.g. Fresh vegetable pulao"
          minLength={3}
          maxLength={120}
          required
        />

        <br /><br />

        <label>Description</label>
        <textarea
          name="description"
          value={formData.description}
          onChange={handleChange}
          placeholder="Describe the food..."
        />

        <br /><br />

        <label>Food Category</label>
        <select
          name="food_category"
          value={formData.food_category}
          onChange={handleChange}
          required
        >
          <option value="">Select category</option>
          <option value="human">Human</option>
          <option value="animal">Animal</option>
        </select>

        <br /><br />

        <label>Quantity</label>
        <input
          type="text"
          name="quantity"
          value={formData.quantity}
          onChange={handleChange}
          placeholder="e.g. 5 kg"
          required
        />

        <br /><br />

        <label>Number of Servings</label>
        <input
          type="number"
          name="servings"
          min="1"
          value={formData.servings}
          onChange={handleChange}
          placeholder="e.g. 10"
        />

        <br /><br />

        <label>Pickup Address</label>
        <textarea
          name="pickup_address"
          value={formData.pickup_address}
          onChange={handleChange}
          placeholder="Enter the complete pickup address..."
          minLength={5}
          required
        />

        <br /><br />

        <label>Food Available Until</label>
        <input
          type="datetime-local"
          name="safe_until"
          value={formData.safe_until}
          onChange={handleChange}
          required
        />

        <br /><br />

        <h3>Pickup Location Coordinates</h3>

        <label>Latitude</label>
        <input
          type="number"
          name="latitude"
          value={formData.latitude}
          placeholder="Select location on map"
          readOnly
          required
        />

        <br /><br />

        <label>Longitude</label>
        <input
          type="number"
          name="longitude"
          value={formData.longitude}
          placeholder="Select location on map"
          readOnly
          required
        />

        <br /><br />

        <MapPicker onLocationSelect={handleLocationSelect} />

        <br /><br />

        <button type="submit" disabled={submitting}>
          {submitting ? "Posting..." : "Post Food Donation"}
        </button>

        {message && <p style={{ color: "green" }}>{message}</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}
      </form>

      <div>
        <h3>Form Data Preview</h3>
        <p>Title: {formData.title}</p>
        <p>Description: {formData.description}</p>
        <p>Category: {formData.food_category}</p>
        <p>Quantity: {formData.quantity}</p>
        <p>Servings: {formData.servings}</p>
        <p>Pickup Address: {formData.pickup_address}</p>
        <p>Safe Until: {formData.safe_until}</p>
        <p>Latitude: {formData.latitude}</p>
        <p>Longitude: {formData.longitude}</p>
      </div>
    </div>
  );
}

export default DonorPostForm;
