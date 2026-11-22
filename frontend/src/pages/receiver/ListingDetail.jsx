import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import ClaimButton from '../../components/receiver/ClaimButton';
import './ListingDetail.css';

/**
 * Detail page for a single listing.
 * Shows public fields; exact address/coordinates only if returned by API.
 */
const ListingDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDetail = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiClient.get(`/listings/${id}`);
      setListing(data.listing);
    } catch (err) {
      setError('Failed to load listing.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!listing) return null;

  return (
    <div className="listing-detail">
      <h2>{listing.title}</h2>
      <p>{listing.description}</p>
      <div>Category: {listing.food_category}</div>
      <div>Quantity: {listing.quantity}</div>
      <div>Servings: {listing.servings}</div>
      {listing.pickup_address && (
        <div className="address">Pickup address: {listing.pickup_address}</div>
      )}
      {listing.latitude && listing.longitude && (
        <div className="coords">Location: {listing.latitude}, {listing.longitude}</div>
      )}
      <ClaimButton listingId={id} onSuccess={() => navigate('/receiver/my-claims')} />
    </div>
  );
};

export default ListingDetail;
