export const getPickupCode = async (claimId, authFetch) => {
  return authFetch(`/handshake/claims/${claimId}/code`);
};
export const getDonorClaims = async (authFetch) => {
  return authFetch("/claims/donor/my");
};