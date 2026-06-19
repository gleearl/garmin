"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { shortDate } from "@/lib/format";

const AXIS = { stroke: "#ffffff40", fontSize: 11 };
const GRID = "#ffffff12";

const tooltipStyle = {
  background: "#111",
  border: "1px solid #ffffff22",
  borderRadius: 8,
  fontSize: 12,
};


export function LineTrend<T extends object>({
  data,
  dataKey,
  color = "#60a5fa",
  unit = "",
}: {
  data: T[];
  dataKey: string;
  color?: string;
  unit?: string;
}) {
  return (
    <div className="h-44 sm:h-56">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} {...AXIS} minTickGap={24} />
        <YAxis {...AXIS} width={40} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${v}${unit}`} />
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
    </div>
  );
}

export function AreaTrend<T extends object>({
  data,
  dataKey,
  color = "#34d399",
  unit = "",
}: {
  data: T[];
  dataKey: string;
  color?: string;
  unit?: string;
}) {
  return (
    <div className="h-44 sm:h-56">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id={`g-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.5} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} {...AXIS} minTickGap={24} />
        <YAxis {...AXIS} width={40} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${v}${unit}`} />
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          fill={`url(#g-${dataKey})`}
          connectNulls
        />
      </AreaChart>
    </ResponsiveContainer>
    </div>
  );
}

export interface StackSeries {
  key: string;
  color: string;
  label: string;
}

export function StackedBars<T extends object>({
  data,
  series,
  unit = "",
}: {
  data: T[];
  series: StackSeries[];
  unit?: string;
}) {
  return (
    <div className="h-52 sm:h-64">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} {...AXIS} minTickGap={24} />
        <YAxis {...AXIS} width={40} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${v}${unit}`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s) => (
          <Bar
            key={s.key}
            dataKey={s.key}
            name={s.label}
            stackId="a"
            fill={s.color}
            radius={s.key === series[series.length - 1].key ? [3, 3, 0, 0] : 0}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
    </div>
  );
}
