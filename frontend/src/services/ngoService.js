
export const uploadNGOCertificate = async (file, authFetch) => {
  const formData = new FormData();
  formData.append("file", file);

  return authFetch("/ngo/applications/certificate", {
    method: "POST",
    body: formData,
  });
};

export const submitNGOApplication = async (applicationData, authFetch) => {
  return authFetch("/ngo/applications", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(applicationData),
  });
};
