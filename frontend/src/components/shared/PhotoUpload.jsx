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
    <div style={{ marginBottom: "24px" }}>
      <label style={{ fontWeight: 700, fontSize: "14px", color: "var(--emerald-900)", marginBottom: "4px" }}>
        Food Photo (Optional)
      </label>
      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "10px" }}>
        A clear photo helps community receivers identify the meal and packaging.
      </span>

      {previewUrl ? (
        <div style={{ position: "relative", display: "inline-block" }}>
          <img
            src={previewUrl}
            alt="Food preview"
            style={{
              width: "100%",
              maxWidth: "320px",
              height: "190px",
              objectFit: "cover",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-card)",
              display: "block",
            }}
          />
          <button
            type="button"
            onClick={onPhotoClear}
            className="btn-danger btn-sm"
            style={{
              position: "absolute",
              top: "10px",
              right: "10px",
              padding: "4px 10px",
              fontSize: "12px",
            }}
          >
            ✕ Remove
          </button>
        </div>
      ) : (
        <div
          style={{
            border: "2px dashed var(--border)",
            borderRadius: "var(--radius-md)",
            padding: "20px",
            textAlign: "center",
            background: "#ffffff",
          }}
        >
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            disabled={compressing}
            id="photo-file-input"
            style={{ marginBottom: "6px", maxWidth: "280px" }}
          />
          {compressing && (
            <p style={{ fontSize: "12px", color: "var(--primary)", fontWeight: 600, margin: "6px 0 0 0" }}>
              ⏳ Optimizing image for web...
            </p>
          )}
          {error && (
            <p style={{ fontSize: "12px", color: "var(--red-accent)", margin: "6px 0 0 0" }}>
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default PhotoUpload;
