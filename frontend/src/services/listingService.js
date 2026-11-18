
export const createListing = async (listingData, authFetch) => {
  return authFetch("/listings/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(listingData),
  });
};

export const cancelListing = async (listingId, authFetch) => {
  return authFetch(`/listings/${listingId}/cancel`, {
    method: "POST",
  });
};

export const updateListing = async (listingId, listingData, authFetch) => {
  return authFetch(`/listings/${listingId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(listingData),
  });
};
