import { useState } from "react";
import imageCompression from "browser-image-compression";

function PhotoUpload({ onPhotoSelect, previewUrl, onPhotoClear }) {
  const [compressing, setCompressing] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file (JPG, PNG).");
      return;
    }

    try {
      setCompressing(true);
      setError("");

      const options = {
        maxSizeMB: 0.8,
        maxWidthOrHeight: 1280,
        useWebWorker: true,
      };

      const compressedFile = await imageCompression(file, options);
      const url = URL.createObjectURL(compressedFile);

      if (onPhotoSelect) {
        onPhotoSelect(compressedFile, url);
      }
    } catch (err) {
      console.error("Compression error:", err);
      setError("Image optimization failed. Please try a different photo.");
    } finally {
      setCompressing(false);
    }
  };

  return (
    <div style={{ marginBottom: "20px" }}>
      <label style={{ fontWeight: 600, marginBottom: "6px" }}>
        Food Photo (Optional)
      </label>
      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
        Photos help receivers quickly identify food and packaging.
      </span>

      {previewUrl ? (
        <div style={{ position: "relative", display: "inline-block" }}>
          <img
            src={previewUrl}
            alt="Food preview"
            style={{
              width: "100%",
              maxWidth: "280px",
              height: "180px",
              objectFit: "cover",
              borderRadius: "8px",
              border: "1px solid var(--border)",
            }}
          />
          <button
            type="button"
            onClick={onPhotoClear}
            className="btn-danger btn-sm"
            style={{
              position: "absolute",
              top: "8px",
              right: "8px",
              padding: "4px 8px",
            }}
          >
            Remove
          </button>
        </div>
      ) : (
        <div>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            disabled={compressing}
            style={{ marginBottom: "6px" }}
          />
          {compressing && (
            <p style={{ fontSize: "12px", color: "var(--primary)" }}>
              Optimizing image...
            </p>
          )}
          {error && (
            <p style={{ fontSize: "12px", color: "var(--danger)" }}>
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default PhotoUpload;
