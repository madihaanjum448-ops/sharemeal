
import { useState, useEffect } from "react";
import imageCompression from "browser-image-compression";

function PhotoUpload() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Clean up the previous preview URL
  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  // Select and compress image
  const handleImageChange = async (e) => {
    const file = e.target.files[0];

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setUploadError("Please select a valid image.");
      return;
    }

    try {
      setLoading(true);
      setUploadError("");
      setUploadSuccess(false);
      setRetryCount(0);

      const options = {
        maxSizeMB: 1,
        maxWidthOrHeight: 1920,
        useWebWorker: true,
      };

      const compressedFile = await imageCompression(file, options);

      setImage(compressedFile);

      const previewUrl = URL.createObjectURL(compressedFile);
      setPreview(previewUrl);
    } catch (error) {
      console.error("Image compression failed:", error);
      setUploadError("Could not compress the image. Please try another photo.");
    } finally {
      setLoading(false);
    }
  };

  // Temporary connectivity test with retry handling
  const handleUpload = async () => {
    if (!image) {
      setUploadError("Please select an image first.");
      return;
    }

    if (retryCount >= 3) {
      setUploadError("Maximum retry attempts reached. Please try again later.");
      return;
    }

    setUploading(true);
    setUploadError("");
    setUploadSuccess(false);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      try {
        await fetch("https://www.google.com/favicon.ico", {
          method: "GET",
          mode: "no-cors",
          cache: "no-store",
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timeoutId);
      }

      setRetryCount(0);
      setUploadSuccess(true);
    } catch (error) {
      console.error("Connectivity test failed:", error);

      setRetryCount((prev) => prev + 1);
      setUploadError(
        error.name === "AbortError"
          ? "Network request timed out. Please retry."
          : "Network unavailable. Please check your connection and retry."
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h3>Upload Food Photo</h3>
      <p>Add a clear photo of the food you're donating.</p>

      <input
        type="file"
        accept="image/*"
        onChange={handleImageChange}
      />

      {loading && <p>Compressing image...</p>}

      {preview && !loading && (
        <div>
          <img
            src={preview}
            alt="Food preview"
            style={{ width: "200px", marginTop: "15px" }}
          />

          <p>Selected file: {image?.name}</p>

          <p>
            Compressed size: {(image.size / (1024 * 1024)).toFixed(2)} MB
          </p>
        </div>
      )}

      {image && !loading && (
        <button
          type="button"
          onClick={handleUpload}
          disabled={uploading || uploadSuccess || retryCount >= 3}
        >
          {uploading ? "Checking connection..." : "Upload Photo"}
        </button>
      )}

      {uploading && <p>Please wait...</p>}

      {uploadSuccess && (
        <p>Network test successful!</p>
      )}

      {uploadError && (
        <div>
          <p style={{ color: "red" }}>{uploadError}</p>

          {retryCount < 3 && (
            <button
              type="button"
              onClick={handleUpload}
              disabled={uploading}
            >
              Retry Upload ({retryCount}/3)
            </button>
          )}

          {retryCount >= 3 && (
            <p>Maximum retry attempts reached. Please try again later.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default PhotoUpload;
