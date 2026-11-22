import React, { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import './ImpactDashboard.css';
import DailyChart from '../../components/receiver/DailyChart';
import htmlToImage from 'html-to-image';

/**
 * Impact dashboard – shows aggregate impact metrics.
 * Uses GET /impact/summary (mocked until real endpoint exists).
 * Shows a "DEMO DATA" badge when `is_demo` is true.
 */
const ImpactDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchImpact = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await apiClient.get('/impact/summary');
      setData(resp);
    } catch (e) {
      setError('Failed to load impact data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImpact();
  }, []);

  const handleExport = async () => {
    if (!data) return;
    const node = document.getElementById('impact-card');
    const dataUrl = await htmlToImage.toPng(node);
    const link = document.createElement('a');
    link.download = 'impact.png';
    link.href = dataUrl;
    link.click();
  };

  if (loading) return <p>Loading impact...</p>;
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data) return null;

  const {
    is_demo,
    generated_at,
    completed_pickups,
    meals_rescued,
    distinct_donors,
    distinct_receiver_orgs,
    category_breakdown,
    last_30_days,
  } = data;

  return (
    <div className="impact-dashboard">
      {is_demo && <div className="demo-badge" data-testid="demo-badge">DEMO DATA</div>}
      <h2>Impact Summary</h2>
      <div className="counters">
        <div className="counter"><strong>{completed_pickups}</strong><span>Completed Pickups</span></div>
        <div className="counter"><strong>{meals_rescued}</strong><span>Meals Rescued</span></div>
        <div className="counter"><strong>{distinct_donors}</strong><span>Donors</span></div>
        <div className="counter"><strong>{distinct_receiver_orgs}</strong><span>Receiver Orgs</span></div>
        <div className="counter"><strong>{category_breakdown.human}</strong><span>Human</span></div>
        <div className="counter"><strong>{category_breakdown.animal}</strong><span>Animal</span></div>
      </div>
      <h3>Last 30 days</h3>
      {last_30_days.length === 0 ? (
        <p>No data for the last 30 days.</p>
      ) : (
        <DailyChart series={last_30_days} />
      )}
      <div id="impact-card" className="share-card">
        <h4>Share this impact</h4>
        <p>Generated at: {new Date(generated_at).toLocaleString()}</p>
        <p>Figures reflect completed pickups recorded in ShareMeal.</p>
        <button onClick={handleExport}>Download PNG</button>
      </div>
    </div>
  );
};

export default ImpactDashboard;
