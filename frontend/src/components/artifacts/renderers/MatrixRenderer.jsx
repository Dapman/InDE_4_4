/**
 * MatrixRenderer - Renders matrix/table-based artifacts
 *
 * Supports: SWOT analysis, 2x2 matrices, comparison tables
 */

import { cn } from '../../../lib/utils';

export function MatrixRenderer({ artifact }) {
  const data = artifact.data || parseMatrixData(artifact.content);

  if (!data) {
    return (
      <div className="text-center text-zinc-500 py-8">
        Unable to parse matrix data
      </div>
    );
  }

  const matrixType = data.type || artifact.type || 'swot';

  return (
    <div className="w-full">
      {/* Title */}
      {data.title && (
        <h3 className="text-body-md font-medium text-zinc-200 mb-4 text-center">
          {data.title}
        </h3>
      )}

      {/* Render based on matrix type */}
      {matrixType === 'swot' && <SWOTMatrix data={data} />}
      {matrixType === '2x2' && <TwoByTwoMatrix data={data} />}
      {matrixType === '2x2_matrix' && <TwoByTwoMatrix data={data} />}
      {(matrixType === 'table' || matrixType === 'comparison_matrix' || matrixType === 'matrix') && (
        <TableMatrix data={data} />
      )}
    </div>
  );
}

function SWOTMatrix({ data }) {
  const { strengths = [], weaknesses = [], opportunities = [], threats = [] } = data;

  return (
    <div className="grid grid-cols-2 gap-4 max-w-3xl mx-auto">
      {/* Strengths */}
      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
        <h4 className="text-body-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-emerald-500/20 flex items-center justify-center text-xs">
            S
          </span>
          Strengths
        </h4>
        <ul className="space-y-2">
          {strengths.map((item, i) => (
            <li key={i} className="text-caption text-zinc-300 flex items-start gap-2">
              <span className="text-emerald-400 mt-0.5">•</span>
              {item}
            </li>
          ))}
          {strengths.length === 0 && (
            <li className="text-caption text-zinc-600 italic">No items</li>
          )}
        </ul>
      </div>

      {/* Weaknesses */}
      <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-4">
        <h4 className="text-body-sm font-semibold text-rose-400 mb-3 flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-rose-500/20 flex items-center justify-center text-xs">
            W
          </span>
          Weaknesses
        </h4>
        <ul className="space-y-2">
          {weaknesses.map((item, i) => (
            <li key={i} className="text-caption text-zinc-300 flex items-start gap-2">
              <span className="text-rose-400 mt-0.5">•</span>
              {item}
            </li>
          ))}
          {weaknesses.length === 0 && (
            <li className="text-caption text-zinc-600 italic">No items</li>
          )}
        </ul>
      </div>

      {/* Opportunities */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <h4 className="text-body-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-blue-500/20 flex items-center justify-center text-xs">
            O
          </span>
          Opportunities
        </h4>
        <ul className="space-y-2">
          {opportunities.map((item, i) => (
            <li key={i} className="text-caption text-zinc-300 flex items-start gap-2">
              <span className="text-blue-400 mt-0.5">•</span>
              {item}
            </li>
          ))}
          {opportunities.length === 0 && (
            <li className="text-caption text-zinc-600 italic">No items</li>
          )}
        </ul>
      </div>

      {/* Threats */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
        <h4 className="text-body-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-amber-500/20 flex items-center justify-center text-xs">
            T
          </span>
          Threats
        </h4>
        <ul className="space-y-2">
          {threats.map((item, i) => (
            <li key={i} className="text-caption text-zinc-300 flex items-start gap-2">
              <span className="text-amber-400 mt-0.5">•</span>
              {item}
            </li>
          ))}
          {threats.length === 0 && (
            <li className="text-caption text-zinc-600 italic">No items</li>
          )}
        </ul>
      </div>
    </div>
  );
}

function TwoByTwoMatrix({ data }) {
  const { quadrants = {}, xAxisLabel, yAxisLabel } = data;

  const positions = ['topLeft', 'topRight', 'bottomLeft', 'bottomRight'];
  const defaultLabels = {
    topLeft: 'Top Left',
    topRight: 'Top Right',
    bottomLeft: 'Bottom Left',
    bottomRight: 'Bottom Right',
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Axis labels */}
      {yAxisLabel && (
        <div className="text-caption text-zinc-500 text-center mb-2">
          ↑ {yAxisLabel}
        </div>
      )}

      <div className="flex items-center gap-4">
        {/* Grid */}
        <div className="flex-1 grid grid-cols-2 gap-3">
          {positions.map((pos) => {
            const quadrant = quadrants[pos] || {};
            const label = quadrant.label || defaultLabels[pos];
            const items = quadrant.items || [];

            return (
              <div
                key={pos}
                className="bg-surface-3 border border-surface-border rounded-lg p-4 min-h-[150px]"
              >
                <h4 className="text-caption font-semibold text-zinc-400 mb-2">
                  {label}
                </h4>
                <ul className="space-y-1">
                  {items.map((item, i) => (
                    <li key={i} className="text-caption text-zinc-300">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>

      {xAxisLabel && (
        <div className="text-caption text-zinc-500 text-center mt-2">
          {xAxisLabel} →
        </div>
      )}
    </div>
  );
}

function TableMatrix({ data }) {
  const { headers = [], rows = [] } = data;

  if (headers.length === 0 && rows.length === 0) {
    return (
      <div className="text-center text-zinc-500 py-4">
        No table data available
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        {headers.length > 0 && (
          <thead>
            <tr>
              {headers.map((header, i) => (
                <th
                  key={i}
                  className="bg-surface-3 px-4 py-2 text-left text-caption font-semibold text-zinc-300 border border-surface-border"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-surface-2' : 'bg-surface-3/50'}>
              {(Array.isArray(row) ? row : [row]).map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="px-4 py-2 text-caption text-zinc-400 border border-surface-border"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Helper to parse matrix data from string content
function parseMatrixData(content) {
  if (!content) return null;

  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export default MatrixRenderer;
