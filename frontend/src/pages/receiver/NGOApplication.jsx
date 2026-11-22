
import { useState } from "react";
import imageCompression from "browser-image-compression";
import { useAuth } from "../../context/AuthContext";
import {
  uploadNGOCertificate,
  submitNGOApplication,
} from "../../services/ngoService";

function NGOApplication() {
  const { authFetch } = useAuth();

  const [formData, setFormData] = useState({
    organization_name: "",
    registration_number: "",
    contact_person: "",
    contact_email: "",
    contact_phone: "",
    address: "",
  });

  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleDocumentChange = async (e) => {
    const file = e.target.files?.[0];

    if (!file) return;

    setError("");
    setSuccess("");

    const isImage = file.type.startsWith("image/");
    const isPDF = file.type === "application/pdf";

    if (!isImage && !isPDF) {
      setDocument(null);
      setError("Please select an image or PDF certificate.");
      e.target.value = "";
      return;
    }

    try {
      if (isImage) {
        const compressed = await imageCompression(file, {
          maxSizeMB: 1,
          maxWidthOrHeight: 1920,
          useWebWorker: true,
        });

        setDocument(compressed);
      } else {
        setDocument(file);
      }
    } catch (err) {
      console.error("Certificate processing failed:", err);
      setDocument(null);
      setError("Could not process the certificate. Please try again.");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    if (!document) {
      setError("Please upload your NGO registration certificate.");
      return;
    }

    try {
      setLoading(true);

      // Step 1: Upload certificate
      const uploadResponse = await uploadNGOCertificate(
        document,
        authFetch
      );

      if (!uploadResponse.certificate_url) {
        throw new Error(
          "Certificate upload response did not contain a certificate URL."
        );
      }

      // Step 2: Submit NGO application
      const applicationData = {
        ...formData,
        certificate_url: uploadResponse.certificate_url,
      };

      const response = await submitNGOApplication(
        applicationData,
        authFetch
      );

      if (!response.application_id) {
        throw new Error(
          "Application response did not contain an application ID."
        );
      }

      setSuccess(
        `Application submitted successfully! Application ID: ${response.application_id}. Status: ${response.status || "pending"}.`
      );

      setFormData({
        organization_name: "",
        registration_number: "",
        contact_person: "",
        contact_email: "",
        contact_phone: "",
        address: "",
      });

      setDocument(null);

      e.target.reset();
    } catch (err) {
      console.error("NGO application submission failed:", err);
      setError(
        err.message || "Failed to submit application. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ngo-application">
      <h1>NGO Registration Application</h1>

      <p>
        Register your organization with ShareMeal to help connect
        surplus food with people who need it.
      </p>

      <form onSubmit={handleSubmit}>
        <label>Organization Name</label>
        <input
          name="organization_name"
          value={formData.organization_name}
          onChange={handleChange}
          placeholder="Enter NGO name"
          required
        />

        <label>Registration Number</label>
        <input
          name="registration_number"
          value={formData.registration_number}
          onChange={handleChange}
          placeholder="Enter registration number"
          required
        />

        <label>Contact Person</label>
        <input
          name="contact_person"
          value={formData.contact_person}
          onChange={handleChange}
          placeholder="Enter contact person's name"
          required
        />

        <label>Email Address</label>
        <input
          type="email"
          name="contact_email"
          value={formData.contact_email}
          onChange={handleChange}
          placeholder="Enter official email"
          required
        />

        <label>Phone Number</label>
        <input
          type="tel"
          name="contact_phone"
          value={formData.contact_phone}
          onChange={handleChange}
          placeholder="Enter contact number"
          required
        />

        <label>Organization Address</label>
        <textarea
          name="address"
          value={formData.address}
          onChange={handleChange}
          placeholder="Enter complete address"
          required
        />

        <label>Registration Certificate</label>
        <input
          type="file"
          accept="image/*,.pdf"
          onChange={handleDocumentChange}
          required
        />

        {document && (
          <p>Selected certificate: {document.name}</p>
        )}

        {loading && (
          <p>
            Uploading certificate and submitting application...
          </p>
        )}

        {error && <p role="alert" style={{ color: "red" }}>{error}</p>}

        {success && (
          <p role="status" style={{ color: "green" }}>{success}</p>
        )}

        <button type="submit" disabled={loading}>
          {loading ? "Submitting..." : "Submit Application"}
        </button>
      </form>
    </div>
  );
}

export default NGOApplication;
