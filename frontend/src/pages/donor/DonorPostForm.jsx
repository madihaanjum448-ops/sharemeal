
import { useState } from "react";
import MapPicker from "../../components/shared/MapPicker";

function DonorPostForm() {
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

  // Handles normal form inputs
  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData({
      ...formData,
      [name]: value,
    });
  };

  // Handles coordinates received from the map
  const handleLocationSelect = ({ latitude, longitude }) => {
    setFormData((prev) => ({
      ...prev,
      latitude: latitude.toString(),
      longitude: longitude.toString(),
    }));
  };

  return (
    <div>
      <h1>Donate Food</h1>
      <p>Share surplus food with someone who needs it.</p>

      <form>
        <label>Food Title</label>
        <input
          type="text"
          name="title"
          value={formData.title}
          onChange={handleChange}
          placeholder="e.g. Fresh vegetable pulao"
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
        />

        <br /><br />

        <label>Food Available Until</label>
        <input
          type="datetime-local"
          name="safe_until"
          value={formData.safe_until}
          onChange={handleChange}
        />

        <br /><br />

        <h3>Pickup Location Coordinates</h3>

        <label>Latitude</label>
       <input
  type="number"
  name="latitude"
  value={formData.latitude}
  onChange={handleChange}
  placeholder="Enter latitude"
  readOnly
/>
        <br /><br />

        <label>Longitude</label>
        <input
          type="number"
          name="longitude"
          value={formData.longitude}
          onChange={handleChange}
          placeholder="Enter longitude"
          readOnly
        />
        <br /><br />

<MapPicker onLocationSelect={handleLocationSelect} />
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
