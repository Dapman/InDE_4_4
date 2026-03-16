/**
 * PositioningMapRenderer - Renders 2D positioning/perceptual maps
 *
 * Displays competitive positioning on a 2D grid with labeled axes
 * and positioned data points.
 */

import { useMemo } from 'react';
import { cn } from '../../../lib/utils';

// Default colors for points
const POINT_COLORS = [
  '#8b5cf6', // violet (primary - "us")
  '#64748b', // slate (competitors)
  '#06b6d4', // cyan
  '#f59e0b', // amber
  '#10b981', // emerald
  '#f43f5e', // rose
];

export function PositioningMapRenderer({ artifact }) {
  const data = artifact.data || parseMapData(artifact.content);

  if (!data) {
    return (
      <div className="text-center text-zinc-500 py-8">
        Unable to parse positioning map data
      </div>
    );
  }

  const {
    xAxis = { label: 'X Axis', min: 0, max: 100 },
    yAxis = { label: 'Y Axis', min: 0, max: 100 },
    points = [],
    quadrants = [],
    title,
  } = data;

  // Calculate point positions as percentages
  const normalizedPoints = useMemo(() => {
    return points.map((point, index) => ({
      ...point,
      xPercent: ((point.x - xAxis.min) / (xAxis.max - xAxis.min)) * 100,
      yPercent: 100 - ((point.y - yAxis.min) / (yAxis.max - yAxis.min)) * 100, // Invert Y
      color: point.color || POINT_COLORS[index % POINT_COLORS.length],
    }));
  }, [points, xAxis, yAxis]);

  return (
    <div className="w-full">
      {/* Title */}
      {title && (
        <h3 className="text-body-md font-medium text-zinc-200 mb-4 text-center">
          {title}
        </h3>
      )}

      {/* Map container */}
      <div className="relative aspect-square max-w-[500px] mx-auto">
        {/* Y-axis label */}
        <div className="absolute -left-8 top-1/2 -translate-y-1/2 -rotate-90 text-caption text-zinc-500 whitespace-nowrap">
          {yAxis.label}
        </div>

        {/* X-axis label */}
        <div className="absolute bottom-[-24px] left-1/2 -translate-x-1/2 text-caption text-zinc-500 whitespace-nowrap">
          {xAxis.label}
        </div>

        {/* Grid */}
        <div className="absolute inset-0 border border-surface-border rounded-lg bg-surface-3/30">
          {/* Grid lines */}
          <div className="absolute inset-0">
            {/* Horizontal center line */}
            <div className="absolute left-0 right-0 top-1/2 border-t border-surface-border/50" />
            {/* Vertical center line */}
            <div className="absolute top-0 bottom-0 left-1/2 border-l border-surface-border/50" />

            {/* Additional grid lines (25%, 75%) */}
            <div className="absolute left-0 right-0 top-1/4 border-t border-surface-border/30 border-dashed" />
            <div className="absolute left-0 right-0 top-3/4 border-t border-surface-border/30 border-dashed" />
            <div className="absolute top-0 bottom-0 left-1/4 border-l border-surface-border/30 border-dashed" />
            <div className="absolute top-0 bottom-0 left-3/4 border-l border-surface-border/30 border-dashed" />
          </div>

          {/* Quadrant labels */}
          {quadrants.length > 0 && (
            <>
              {quadrants.map((q) => (
                <div
                  key={q.position}
                  className={cn(
                    'absolute text-caption text-zinc-600 px-2',
                    q.position === 'top-left' && 'top-2 left-2',
                    q.position === 'top-right' && 'top-2 right-2',
                    q.position === 'bottom-left' && 'bottom-2 left-2',
                    q.position === 'bottom-right' && 'bottom-2 right-2',
                  )}
                >
                  {q.label}
                </div>
              ))}
            </>
          )}

          {/* Points */}
          {normalizedPoints.map((point, index) => (
            <div
              key={point.id || index}
              className="absolute transform -translate-x-1/2 -translate-y-1/2 group"
              style={{
                left: `${point.xPercent}%`,
                top: `${point.yPercent}%`,
              }}
            >
              {/* Point */}
              <div
                className="w-4 h-4 rounded-full border-2 border-white shadow-lg"
                style={{ backgroundColor: point.color }}
              />

              {/* Label */}
              <div
                className={cn(
                  'absolute whitespace-nowrap px-2 py-1 rounded text-caption font-medium',
                  'bg-surface-2 border border-surface-border shadow-lg',
                  'opacity-0 group-hover:opacity-100 transition-opacity z-10',
                  // Position label based on point position
                  point.xPercent > 70 ? 'right-6' : 'left-6',
                  point.yPercent > 70 ? 'bottom-0' : 'top-0',
                )}
              >
                <span style={{ color: point.color }}>{point.label}</span>
                <span className="text-zinc-500 ml-2">
                  ({point.x}, {point.y})
                </span>
              </div>

              {/* Always visible label */}
              <div
                className={cn(
                  'absolute whitespace-nowrap text-caption font-medium',
                  point.xPercent > 70 ? 'right-5' : 'left-5',
                )}
                style={{ color: point.color }}
              >
                {point.label}
              </div>
            </div>
          ))}
        </div>

        {/* Axis values */}
        <div className="absolute -bottom-2 left-0 text-[10px] text-zinc-600">
          {xAxis.min}
        </div>
        <div className="absolute -bottom-2 right-0 text-[10px] text-zinc-600">
          {xAxis.max}
        </div>
        <div className="absolute -left-2 bottom-0 text-[10px] text-zinc-600">
          {yAxis.min}
        </div>
        <div className="absolute -left-2 top-0 text-[10px] text-zinc-600">
          {yAxis.max}
        </div>
      </div>

      {/* Legend */}
      {normalizedPoints.length > 0 && (
        <div className="mt-6 flex flex-wrap justify-center gap-4">
          {normalizedPoints.map((point, index) => (
            <div key={point.id || index} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: point.color }}
              />
              <span className="text-caption text-zinc-400">{point.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Helper to parse map data from string content
function parseMapData(content) {
  if (!content) return null;

  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export default PositioningMapRenderer;
