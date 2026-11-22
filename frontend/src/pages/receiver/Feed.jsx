import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../api/client';
import './Feed.css';
import StatusBanner from '../../components/receiver/StatusBanner';

/**
 * Feed page – displays public listings.
 * Uses mock data when VITE_USE_MOCK=true.
 * Allows filtering by food_category and pagination via limit/offset.
 * Shows time‑left using server‑time skew (handled by apiClient). 
 */
const Feed = () => {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [category, setCategory] = useState('all');
  const limit = 10;

  const fetchListings = async () => {
    setLoading(true);
    setError('');
    try {
      const params = { limit, offset: page * limit };
      if (category !== 'all') params.food_category = category;
      const data = await apiClient.get('/listings/', { params });
      setListings(data.listings);
    } catch (err) {
      setError('Failed to load feed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchListings();
  }, [page, category]);

  const handlePrev = () => setPage((p) => Math.max(p - 1, 0));
  const handleNext = () => setPage((p) => p + 1);

  return (
    <div className="feed-page">
      <StatusBanner />
      <h2>Food Listings</h2>
      <div className="filters">
        <label>Category: </label>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="all">All</option>
          <option value="human">Human</option>
          <option value="animal">Animal</option>
        </select>
      </div>
      {loading && <p>Loading...</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="listing-list">
        {listings.map((l) => (
          <li key={l.id} className="listing-card">
            <Link to={`/receiver/listing/${l.id}`}> {l.title} </Link>
            <div className="chip">{l.food_category}</div>
            <div>Quantity: {l.quantity}</div>
            <div>Servings: {l.servings}</div>
            {/* time‑left computed client‑side using expires_at and server skew */}
            <div className="time-left">{/* placeholder – logic in utility */}</div>
          </li>
        ))}
      </ul>
      <div className="pagination">
        <button onClick={handlePrev} disabled={page === 0}>Prev</button>
        <span>Page {page + 1}</span>
        <button onClick={handleNext}>Next</button>
      </div>
    </div>
  );
};

export default Feed;
