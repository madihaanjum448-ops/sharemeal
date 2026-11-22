import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import './Login.css';

/**
 * OTP Login screen for receivers.
 * In mock mode (VITE_USE_MOCK=true) a demo badge is shown.
 */
const Login = () => {
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState('email'); // 'email' | 'otp'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSendOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/auth/send-otp', { email });
      setStep('otp');
    } catch (err) {
      const code = err?.response?.status;
      if (code === 429) setError('Too many requests – please try later.');
      else setError('Failed to send OTP.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await apiClient.post('/auth/verify-otp', {
        email,
        token: otp,
        role: 'receiver',
      });
      // store session tokens & profile
      const { access_token, refresh_token } = data.session;
      sessionStorage.setItem('access_token', access_token);
      sessionStorage.setItem('refresh_token', refresh_token);
      sessionStorage.setItem('profile', JSON.stringify(data.profile));
      navigate('/receiver/feed');
    } catch (err) {
      const code = err?.response?.status;
      if (code === 401) setError('Invalid or expired OTP.');
      else if (code === 429) setError('Too many attempts – please wait.');
      else setError('Verification failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {process.env.VITE_USE_MOCK === 'true' && (
        <div className="demo-badge" data-testid="demo-badge">DEMO DATA</div>
      )}
      {step === 'email' && (
        <form onSubmit={handleSendOtp} className="login-form">
          <h2>Receiver Login – OTP</h2>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="submit" disabled={loading}>Send OTP</button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
      )}
      {step === 'otp' && (
        <form onSubmit={handleVerifyOtp} className="login-form">
          <h2>Enter OTP</h2>
          <label htmlFor="otp">Code</label>
          <input
            id="otp"
            type="text"
            required
            pattern="[0-9]{6,8}"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
          />
          <button type="submit" disabled={loading}>Verify & Login</button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
      )}
    </div>
  );
};

export default Login;
