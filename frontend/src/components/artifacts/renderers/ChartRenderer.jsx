/**
 * ChartRenderer - Renders chart artifacts using Recharts
 *
 * Supports: bar_chart, line_chart, pie_chart, strategy_canvas
 */

import {
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import { cn } from '../../../lib/utils';

// Default colors for chart elements
const COLORS = [
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#f59e0b', // amber
  '#10b981', // emerald
  '#f43f5e', // rose
  '#6366f1', // indigo
  '#ec4899', // pink
  '#14b8a6', // teal
];

export function ChartRenderer({ artifact }) {
  const data = artifact.data || parseChartData(artifact.content);

  if (!data) {
    return (
      <div className="text-center text-zinc-500 py-8">
        Unable to parse chart data
      </div>
    );
  }

  const chartType = data.chartType || artifact.type?.replace('_chart', '') || 'bar';

  return (
    <div className="w-full">
      {/* Title if present */}
      {data.title && (
        <h3 className="text-body-md font-medium text-zinc-200 mb-4 text-center">
          {data.title}
        </h3>
      )}

      {/* Chart */}
      <div className="h-[400px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' && <BarChartComponent data={data} />}
          {chartType === 'line' && <LineChartComponent data={data} />}
          {chartType === 'pie' && <PieChartComponent data={data} />}
          {chartType === 'strategy_canvas' && <StrategyCanvasComponent data={data} />}
        </ResponsiveContainer>
      </div>

      {/* Description if present */}
      {data.description && (
        <p className="text-caption text-zinc-500 mt-4 text-center">
          {data.description}
        </p>
      )}
    </div>
  );
}

function BarChartComponent({ data }) {
  const chartData = data.data || data.values || [];

  return (
    <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
      <XAxis
        dataKey="name"
        stroke="#9ca3af"
        tick={{ fill: '#9ca3af', fontSize: 12 }}
        angle={-45}
        textAnchor="end"
        height={60}
      />
      <YAxis
        stroke="#9ca3af"
        tick={{ fill: '#9ca3af', fontSize: 12 }}
        label={data.yAxisLabel ? {
          value: data.yAxisLabel,
          angle: -90,
          position: 'insideLeft',
          fill: '#9ca3af',
        } : undefined}
      />
      <Tooltip
        contentStyle={{
          backgroundColor: '#1f2937',
          border: '1px solid #374151',
          borderRadius: '8px',
        }}
        labelStyle={{ color: '#f3f4f6' }}
        itemStyle={{ color: '#d1d5db' }}
      />
      <Legend wrapperStyle={{ color: '#9ca3af' }} />
      <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
        {chartData.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
        ))}
      </Bar>
    </BarChart>
  );
}

function LineChartComponent({ data }) {
  const chartData = data.data || data.values || [];
  const lines = data.lines || [{ dataKey: 'value', name: 'Value' }];

  return (
    <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
      <XAxis
        dataKey="name"
        stroke="#9ca3af"
        tick={{ fill: '#9ca3af', fontSize: 12 }}
        angle={-45}
        textAnchor="end"
        height={60}
      />
      <YAxis
        stroke="#9ca3af"
        tick={{ fill: '#9ca3af', fontSize: 12 }}
      />
      <Tooltip
        contentStyle={{
          backgroundColor: '#1f2937',
          border: '1px solid #374151',
          borderRadius: '8px',
        }}
        labelStyle={{ color: '#f3f4f6' }}
        itemStyle={{ color: '#d1d5db' }}
      />
      <Legend wrapperStyle={{ color: '#9ca3af' }} />
      {lines.map((line, index) => (
        <Line
          key={line.dataKey}
          type="monotone"
          dataKey={line.dataKey}
          name={line.name}
          stroke={line.color || COLORS[index % COLORS.length]}
          strokeWidth={2}
          dot={{ fill: line.color || COLORS[index % COLORS.length] }}
        />
      ))}
    </LineChart>
  );
}

function PieChartComponent({ data }) {
  const chartData = data.data || data.values || [];

  return (
    <PieChart>
      <Pie
        data={chartData}
        cx="50%"
        cy="50%"
        labelLine={true}
        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
        outerRadius={150}
        fill="#8884d8"
        dataKey="value"
      >
        {chartData.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
        ))}
      </Pie>
      <Tooltip
        contentStyle={{
          backgroundColor: '#1f2937',
          border: '1px solid #374151',
          borderRadius: '8px',
        }}
        labelStyle={{ color: '#f3f4f6' }}
        itemStyle={{ color: '#d1d5db' }}
      />
      <Legend wrapperStyle={{ color: '#9ca3af' }} />
    </PieChart>
  );
}

function StrategyCanvasComponent({ data }) {
  // Strategy canvas is a line chart with multiple competitors
  const factors = data.factors || [];
  const competitors = data.competitors || [];

  // Transform data for Recharts
  const chartData = factors.map((factor, index) => {
    const point = { name: factor };
    competitors.forEach(comp => {
      point[comp.name] = comp.values?.[index] || 0;
    });
    return point;
  });

  return (
    <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
      <XAxis
        dataKey="name"
        stroke="#9ca3af"
        tick={{ fill: '#9ca3af', fontSize: 12 }}
        angle={-45}
        textAnchor="end"
        height={60}
      />
      <YAxis
        stroke="#9ca3af"
        tick={{ fill: '#9ca3af', fontSize: 12 }}
        domain={[0, 10]}
      />
      <Tooltip
        contentStyle={{
          backgroundColor: '#1f2937',
          border: '1px solid #374151',
          borderRadius: '8px',
        }}
        labelStyle={{ color: '#f3f4f6' }}
        itemStyle={{ color: '#d1d5db' }}
      />
      <Legend wrapperStyle={{ color: '#9ca3af' }} />
      {competitors.map((comp, index) => (
        <Line
          key={comp.name}
          type="monotone"
          dataKey={comp.name}
          stroke={comp.color || COLORS[index % COLORS.length]}
          strokeWidth={2}
          dot={{ fill: comp.color || COLORS[index % COLORS.length], r: 4 }}
        />
      ))}
    </LineChart>
  );
}

// Helper to parse chart data from string content
function parseChartData(content) {
  if (!content) return null;

  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export default ChartRenderer;
