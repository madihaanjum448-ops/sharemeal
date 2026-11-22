import { useState, useEffect } from "react";
import L from "leaflet";
import {
  MapContainer,
  TileLayer,
  Marker,
  useMapEvents,
  useMap,
} from "react-leaflet";

import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function LocationMarker({ position, setPosition, onLocationSelect }) {
  useMapEvents({
    click(e) {
      const newPos = [e.latlng.lat, e.latlng.lng];
      setPosition(newPos);
      onLocationSelect({
        latitude: parseFloat(e.latlng.lat.toFixed(6)),
        longitude: parseFloat(e.latlng.lng.toFixed(6)),
      });
    },
  });

  return position ? <Marker position={position} icon={defaultIcon} /> : null;
}

function RecenterMap({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.setView(position, Math.max(map.getZoom(), 13));
    }
  }, [position, map]);
  return null;
}

function MapPicker({ initialPosition, onLocationSelect }) {
  const [position, setPosition] = useState(
    initialPosition ? [initialPosition.latitude, initialPosition.longitude] : null
  );
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState("");

  const defaultCenter = [20.5937, 78.9629]; // Default geographic center
  const center = position || defaultCenter;
  const initialZoom = position ? 13 : 5;

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGeoError("Geolocation is not supported by your browser");
      return;
    }

    setGeoLoading(true);
    setGeoError("");

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGeoLoading(false);
        const lat = parseFloat(pos.coords.latitude.toFixed(6));
        const lng = parseFloat(pos.coords.longitude.toFixed(6));
        setPosition([lat, lng]);
        onLocationSelect({ latitude: lat, longitude: lng });
      },
      (_err) => {
        setGeoLoading(false);
        setGeoError("Unable to detect location. Click directly on the map to pin.");
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  return (
    <div style={{ marginTop: "16px", marginBottom: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
        <div>
          <label style={{ margin: 0, fontWeight: 700, fontSize: "14px", color: "var(--emerald-900)" }}>
            Pickup Location Pin *
          </label>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Click anywhere on the map to place your pickup pin
          </span>
        </div>
        <button
          type="button"
          onClick={handleUseCurrentLocation}
          disabled={geoLoading}
          className="btn-secondary btn-sm"
        >
          {geoLoading ? "Detecting GPS..." : "📍 Use Current Location"}
        </button>
      </div>

      {geoError && (
        <div className="alert alert-danger" style={{ padding: "8px 12px", fontSize: "12px", marginBottom: "8px" }}>
          {geoError}
        </div>
      )}

      <div style={{ borderRadius: "var(--radius-md)", overflow: "hidden", border: "1px solid var(--border)", boxShadow: "var(--shadow-card)" }}>
        <MapContainer
          center={center}
          zoom={initialZoom}
          style={{ height: "300px", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <LocationMarker
            position={position}
            setPosition={setPosition}
            onLocationSelect={onLocationSelect}
          />
          {position && <RecenterMap position={position} />}
        </MapContainer>
      </div>

      <div style={{ marginTop: "10px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        {position ? (
          <span style={{ fontSize: "12px", color: "var(--primary)", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
            <span>✓ Pin Selected:</span>
            <span>{position[0].toFixed(5)}, {position[1].toFixed(5)}</span>
          </span>
        ) : (
          <span style={{ fontSize: "12px", color: "var(--red-accent)", fontWeight: 500 }}>
            * Please click on the map to pin pickup coordinates
          </span>
        )}
      </div>
    </div>
  );
}

export default MapPicker;
