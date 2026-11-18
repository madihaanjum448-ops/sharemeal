
import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  cancelListing,
  updateListing,
} from "../../services/listingService";

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

  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancellingId, setCancellingId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [savingId, setSavingId] = useState(null);

  const [editData, setEditData] = useState({});

  useEffect(() => {
    const fetchMyPosts = async () => {
      try {
        setLoading(true);
        setError("");

        const data = await authFetch("/listings/my");
        setPosts(data.listings || []);
      } catch (err) {
        setError(err.message || "Failed to load your donations.");
      } finally {
        setLoading(false);
      }
    };

    fetchMyPosts();
  }, [authFetch]);

  const handleCancel = async (listingId) => {
    const confirmed = window.confirm(
      "Are you sure you want to cancel this donation?"
    );

    if (!confirmed) return;

    try {
      setCancellingId(listingId);
      setError("");

      await cancelListing(listingId, authFetch);

      setPosts((prevPosts) =>
        prevPosts.map((post) =>
          post.id === listingId
            ? { ...post, status: "cancelled" }
            : post
        )
      );
    } catch (err) {
      setError(err.message || "Failed to cancel donation.");
    } finally {
      setCancellingId(null);
    }
  };

  const handleEdit = (post) => {
    setEditingId(post.id);

    setEditData({
      title: post.title || "",
      description: post.description || "",
      food_category: post.food_category || "",
      quantity: post.quantity || "",
      servings: post.servings ?? "",
      pickup_address: post.pickup_address || "",
      safe_until: toLocalDateTime(post.safe_until),
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
    if (new Date(editData.safe_until) <= new Date()) {
      setError("Food availability time must be in the future.");
      return;
    }

    const listingData = {
      title: editData.title.trim(),
      description: editData.description.trim() || null,
      food_category: editData.food_category,
      quantity: editData.quantity.trim(),
      servings: editData.servings
        ? Number(editData.servings)
        : null,
      pickup_address: editData.pickup_address.trim(),
      safe_until: new Date(editData.safe_until).toISOString(),
    };

    try {
      setSavingId(listingId);
      setError("");

      await updateListing(listingId, listingData, authFetch);

      setPosts((prevPosts) =>
        prevPosts.map((post) =>
          post.id === listingId
            ? { ...post, ...listingData }
            : post
        )
      );

      setEditingId(null);
      setEditData({});
    } catch (err) {
      setError(err.message || "Failed to update donation.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div>
      <h1>My Food Donations</h1>

      {loading && <p>Loading your donations...</p>}

      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && !error && posts.length === 0 && (
        <p>You haven't posted any food donations yet.</p>
      )}

      {!loading && posts.length > 0 && (
        <div>
          <p>Total donations: {posts.length}</p>

          {posts.map((post) => (
            <div
              key={post.id}
              style={{
                border: "1px solid #ccc",
                padding: "16px",
                marginBottom: "16px",
                borderRadius: "8px",
              }}
            >
              {editingId === post.id ? (
                <div>
                  <h2>Edit Donation</h2>

                  <label>Food Title</label>
                  <input
                    name="title"
                    value={editData.title}
                    onChange={handleEditChange}
                    minLength={3}
                    maxLength={120}
                    required
                  />

                  <br /><br />

                  <label>Description</label>
                  <textarea
                    name="description"
                    value={editData.description}
                    onChange={handleEditChange}
                  />

                  <br /><br />

                  <label>Food Category</label>
                  <select
                    name="food_category"
                    value={editData.food_category}
                    onChange={handleEditChange}
                    required
                  >
                    <option value="human">Human</option>
                    <option value="animal">Animal</option>
                  </select>

                  <br /><br />

                  <label>Quantity</label>
                  <input
                    name="quantity"
                    value={editData.quantity}
                    onChange={handleEditChange}
                    required
                  />

                  <br /><br />

                  <label>Number of Servings</label>
                  <input
                    type="number"
                    name="servings"
                    min="1"
                    value={editData.servings}
                    onChange={handleEditChange}
                  />

                  <br /><br />

                  <label>Pickup Address</label>
                  <textarea
                    name="pickup_address"
                    value={editData.pickup_address}
                    onChange={handleEditChange}
                    minLength={5}
                    required
                  />

                  <br /><br />

                  <label>Food Available Until</label>
                  <input
                    type="datetime-local"
                    name="safe_until"
                    value={editData.safe_until}
                    onChange={handleEditChange}
                    required
                  />

                  <br /><br />

                  <button
                    onClick={() => handleUpdate(post.id)}
                    disabled={savingId === post.id}
                  >
                    {savingId === post.id
                      ? "Saving..."
                      : "Save Changes"}
                  </button>

                  <button
                    onClick={() => {
                      setEditingId(null);
                      setEditData({});
                      setError("");
                    }}
                    disabled={savingId === post.id}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div>
                  <h2>{post.title}</h2>
                  <p>{post.description}</p>
                  <p>Category: {post.food_category}</p>
                  <p>Quantity: {post.quantity}</p>
                  <p>Servings: {post.servings ?? "Not specified"}</p>
                  <p>Pickup address: {post.pickup_address}</p>
                  <p>Status: {post.status}</p>

                  <p>
                    Available until:{" "}
                    {post.safe_until
                      ? new Date(post.safe_until).toLocaleString()
                      : "Not specified"}
                  </p>

                  {post.status === "available" && (
                    <>
                      <button onClick={() => handleEdit(post)}>
                        Edit Donation
                      </button>

                      <button
                        onClick={() => handleCancel(post.id)}
                        disabled={cancellingId === post.id}
                      >
                        {cancellingId === post.id
                          ? "Cancelling..."
                          : "Cancel Donation"}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default MyPosts;
