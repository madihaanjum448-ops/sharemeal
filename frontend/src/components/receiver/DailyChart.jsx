import React from 'react';
import './DailyChart.css';

/**
 * Simple line chart for the last‑30‑day series.
 * `series` is an array of objects: { date: 'YYYY‑MM‑DD', count: number }
 */
const DailyChart = ({ series }) => {
  if (!series || series.length === 0) return null;

  // Determine dimensions
  const width = 300;
  const height = 120;
  const padding = 20;

  const dates = series.map((d) => new Date(d.date));
  const counts = series.map((d) => d.count);
  const maxCount = Math.max(...counts, 1);
  const minCount = Math.min(...counts, 0);

  const xScale = (i) =>
    padding + (i / (series.length - 1)) * (width - 2 * padding);
  const yScale = (v) =>
    height - padding - ((v - minCount) / (maxCount - minCount)) * (height - 2 * padding);

  const points = series.map((d, i) => `${xScale(i)},${yScale(d.count)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="daily-chart" data-testid="daily-chart">
      <polyline
        fill="none"
        stroke="#3b82f6"
        strokeWidth="2"
        points={points}
      />
      {/* Axes */}
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#888" />
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#888" />
    </svg>
  );
};

export default DailyChart;
