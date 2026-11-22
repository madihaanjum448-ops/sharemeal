import React, { useState } from 'react';
import apiClient from '../../api/client';
import './ClaimButton.css';

/**
 * ClaimButton handles the claim POST request and displays status.
 * Props:
 *   - listingId: string
 *   - onSuccess: callback after successful claim
 */
const ClaimButton = ({ listingId, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [claimed, setClaimed] = useState(false);

  const handleClaim = async () => {
    if (claimed) return; // idempotent guard
    setLoading(true);
    setError('');
    try {
      const resp = await apiClient.post('/claims/create', { listing_id: listingId });
      // Assume response contains claim.id and expires_at
      setClaimed(true);
      if (onSuccess) onSuccess();
    } catch (err) {
      const code = err?.response?.status;
      if (code === 409) setError('Someone just claimed it.');
      else if (code === 410) setError('Listing expired.');
      else if (code === 403) setError('Not approved to claim.');
      else if (code === 422) setError('Invalid request.');
      else if (code === 429) setError('Rate limited – try later.');
      else setError('Claim failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="claim-button-container">
      {error && <p className="error" role="alert" data-testid="claim-error">{error}</p>}
      <button
        onClick={handleClaim}
        disabled={loading || claimed}
        className={claimed ? 'claimed' : ''}
        data-testid="claim-btn"
      >
        {claimed ? 'Claimed' : loading ? 'Claiming...' : 'Claim'}
      </button>
    </div>
  );
};

export default ClaimButton;
