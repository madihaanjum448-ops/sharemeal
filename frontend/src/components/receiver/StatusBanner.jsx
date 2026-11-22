import React from 'react';
import { useNavigate } from 'react-router-dom';
import './StatusBanner.css';

/**
 * Shows the receiver's approval status.
 * Banners:
 *  - pending: "Your application is pending admin approval."
 *  - approved: "You are approved. You may claim listings."
 *  - rejected: "Application rejected. Contact support."
 * The component reads the profile from sessionStorage.
 */
const StatusBanner = () => {
  const navigate = useNavigate();
  const profile = JSON.parse(sessionStorage.getItem('profile') || '{}');
  const status = profile.approval_status || 'pending';
  const isVerified = profile.is_verified || false;

  if (status === 'approved' && isVerified) {
    return <div className="status-banner approved" data-testid="status-approved">Approved – you may claim listings.</div>;
  }
  if (status === 'rejected') {
    return (
      <div className="status-banner rejected" data-testid="status-rejected">
        Application rejected. <button onClick={() => navigate('/receiver/login')}>Re‑login to check approval</button>
      </div>
    );
  }
  // pending or unverified
  return (
    <div className="status-banner pending" data-testid="status-pending">
      Your application is pending admin approval. <button onClick={() => navigate('/receiver/login')}>Re‑login to check approval</button>
    </div>
  );
};

export default StatusBanner;
