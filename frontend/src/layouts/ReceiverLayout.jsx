import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import './ReceiverLayout.css';
import { useTranslation } from 'react-i18next';

/**
 * Layout wrapper for all receiver routes.
 * Provides a mobile‑first header with language selector and navigation links.
 */
const ReceiverLayout = () => {
  const { i18n, t } = useTranslation();

  const changeLanguage = (e) => {
    const lng = e.target.value;
    i18n.changeLanguage(lng);
    localStorage.setItem('i18nextLng', lng);
  };

  return (
    <div className="receiver-layout">
      <header className="header">
        <h1>{t('receiver.title', 'ShareMeal Receiver')}</h1>
        <select value={i18n.language} onChange={changeLanguage} data-testid="lang-select">
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
          <option value="kn">ಕನ್ನಡ</option>
        </select>
      </header>
      <nav className="nav">
        <NavLink to="feed" className={({ isActive }) => (isActive ? 'active' : '')}>Feed</NavLink>
        <NavLink to="map" className={({ isActive }) => (isActive ? 'active' : '')}>Map</NavLink>
        <NavLink to="my-claims" className={({ isActive }) => (isActive ? 'active' : '')}>My Claims</NavLink>
        <NavLink to="impact" className={({ isActive }) => (isActive ? 'active' : '')}>Impact</NavLink>
        <NavLink to="login" className={({ isActive }) => (isActive ? 'active' : '')}>Login</NavLink>
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
};

import { Routes, Route } from 'react-router-dom';
import Login from '../pages/receiver/Login';
import Feed from '../pages/receiver/Feed';
import Map from '../pages/receiver/Map';
import ListingDetail from '../pages/receiver/ListingDetail';
import MyClaims from '../pages/receiver/MyClaims';
import Handshake from '../pages/receiver/Handshake';
import ImpactDashboard from '../pages/receiver/ImpactDashboard';

import { Routes, Route } from 'react-router-dom';
import Login from '../pages/receiver/Login';
import Feed from '../pages/receiver/Feed';
import Map from '../pages/receiver/Map';
import ListingDetail from '../pages/receiver/ListingDetail';
import MyClaims from '../pages/receiver/MyClaims';
import Handshake from '../pages/receiver/Handshake';
import ImpactDashboard from '../pages/receiver/ImpactDashboard';

export default ReceiverLayout;

// Nested routes for receiver
const ReceiverRoutes = () => (
  <Routes>
    <Route path="login" element={<Login />} />
    <Route path="feed" element={<Feed />} />
    <Route path="map" element={<Map />} />
    <Route path="listing/:id" element={<ListingDetail />} />
    <Route path="my-claims" element={<MyClaims />} />
    <Route path="handshake/:claimId" element={<Handshake />} />
    <Route path="impact" element={<ImpactDashboard />} />
    <Route index element={<Feed />} />
  </Routes>
);

// Export both layout and its routes
export { ReceiverLayout, ReceiverRoutes };


// Nested routes for receiver
const ReceiverRoutes = () => (
  <Routes>
    <Route path="login" element={<Login />} />
    <Route path="feed" element={<Feed />} />
    <Route path="map" element={<Map />} />
    <Route path="listing/:id" element={<ListingDetail />} />
    <Route path="my-claims" element={<MyClaims />} />
    <Route path="handshake/:claimId" element={<Handshake />} />
    <Route path="impact" element={<ImpactDashboard />} />
    <Route index element={<Feed />} />
  </Routes>
);

// Replace the original export with both layout and nested routes
export { ReceiverLayout, ReceiverRoutes };

