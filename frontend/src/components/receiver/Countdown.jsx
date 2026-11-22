import React, { useEffect, useState, useRef } from 'react';
import apiClient from '../../api/client';
import './Countdown.css';

/**
 * Countdown timer for a claim's expires_at.
 * Props:
 *   - expiresAt: ISO string (UTC)
 *   - onExpire: callback when timer reaches zero
 */
const Countdown = ({ expiresAt, onExpire }) => {
  const [remaining, setRemaining] = useState(() => calculateRemaining());
  const intervalRef = useRef(null);

  function calculateRemaining() {
    // Use client clock; mock server skew is negligible for demo.
    const now = new Date();
    const target = new Date(expiresAt);
    const diff = target - now;
    return diff > 0 ? diff : 0;
  }

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      const secs = Math.max(0, Math.round(calculateRemaining() / 1000));
      setRemaining(secs * 1000);
      if (secs <= 0) {
        clearInterval(intervalRef.current);
        if (onExpire) onExpire();
      }
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [expiresAt]);

  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);
  const warn = remaining <= 3 * 60 * 1000 && remaining > 0;

  return (
    <div className={`countdown ${warn ? 'warning' : ''}`} data-testid="countdown">
      {remaining > 0 ? `${minutes}:${seconds.toString().padStart(2, '0')}` : 'Expired'}
    </div>
  );
};

export default Countdown;
