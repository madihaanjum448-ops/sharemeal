import React, { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import './MyClaims.css';
import ClaimButton from '../../components/receiver/ClaimButton';
import Countdown from '../../components/receiver/Countdown';

/**
 * My Claims page – groups claims by status.
 * Uses mock `/claims/my` which returns an array with status field.
 */
const MyClaims = () => {
  const [claims, setClaims] = useState({ active: [], completed: [], cancelled: [], expired: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchClaims = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiClient.get('/claims/my');
      const grouped = { active: [], completed: [], cancelled: [], expired: [] };
      data.claims.forEach((c) => {
        const status = c.status || 'active';
        if (grouped[status]) grouped[status].push(c);
        else grouped.active.push(c);
      });
      setClaims(grouped);
    } catch (err) {
      setError('Failed to load your claims.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, []);

  const handleCancel = async (claimId) => {
    try {
      await apiClient.post(`/claims/${claimId}/cancel`);
      // Re‑fetch after cancel
      fetchClaims();
    } catch (e) {
      // 409 may indicate already expired – show generic error
      alert('Could not cancel (maybe already expired).');
    }
  };

  const renderGroup = (title, list) => (
    <section>
      <h3>{title}</h3>
      {list.length === 0 && <p>No {title.toLowerCase()}.</p>}
      <ul>
        {list.map((c) => (
          <li key={c.id} className="claim-card">
            <div>Listing ID: {c.listing_id}</div>
            {c.status === 'active' && (
              <>
                <Countdown expiresAt={c.expires_at} />
                <button onClick={() => handleCancel(c.id)} className="cancel-btn">Cancel</button>
              </>
            )}
            {c.status === 'completed' && <span>Completed</span>}
            {c.status === 'cancelled' && <span>Cancelled</span>}
            {c.status === 'expired' && <span>Expired</span>}
          </li>
        ))}
      </ul>
    </section>
  );

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="error" role="alert">{error}</p>;

  return (
    <div className="my-claims-page">
      <h2>My Claims</h2>
      {renderGroup('Active', claims.active)}
      {renderGroup('Completed', claims.completed)}
      {renderGroup('Cancelled', claims.cancelled)}
      {renderGroup('Expired', claims.expired)}
    </div>
  );
};

export default MyClaims;
