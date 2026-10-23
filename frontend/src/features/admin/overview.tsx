'use client';

import { useState } from 'react';
export type OverviewStat = { label: string; value: number | string };
export type TrendPoint = { label: string; lost: number; found: number };
export type ReportTrends = Record<'7d' | '30d' | '6m' | '1y', TrendPoint[]>;
export type AdminActivity = { id: number; title: string; subtitle?: string; badge?: string; href?: string; meta?: string[] };
export type CategoryMetric = { name: string; total: number; lost: number; found: number };
export type ClaimMetric = { label: string; value: number };

const periods = [
  { key: '7d', label: '7 days' },
  { key: '30d', label: '30 days' },
  { key: '6m', label: '6 months' },
  { key: '1y', label: '12 months' },
] as const;

function makeLine(points: TrendPoint[], series: 'lost' | 'found') {
  const width = 720;
  const height = 220;
  const padLeft = 36;
  const padRight = 12;
  const padTop = 14;
  const padBottom = 30;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;
  const maximum = Math.max(1, ...points.flatMap((point) => [point.lost, point.found]));
  const coordinates = points.map((point, index) => ({
    x: padLeft + (points.length <= 1 ? plotWidth / 2 : (index * plotWidth) / (points.length - 1)),
    y: padTop + plotHeight - (point[series] / maximum) * plotHeight,
  }));
  return coordinates.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

export function AdminOverview({ trends }: { trends: ReportTrends }) {
  const [period, setPeriod] = useState<(typeof periods)[number]['key']>('6m');
  const points = trends[period] ?? [];
  const maximum = Math.max(1, ...points.flatMap((point) => [point.lost, point.found]));
  const totalReports = points.reduce((total, point) => total + point.lost + point.found, 0);

  return <div className="mt-6">
    <section aria-labelledby="report-activity-title" className="overflow-hidden rounded-2xl border border-[#e5ebe3] bg-white shadow-sm shadow-[#274c3b]/[.025]">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#edf0eb] px-5 py-5 md:px-7">
        <div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#79917c]">Dashboard graph</p><h2 id="report-activity-title" className="mt-1 text-lg font-semibold text-[#293b30]">Lost and found reports</h2><p className="mt-1 text-xs text-[#87938a]">Reports created during the selected period.</p></div>
        <div role="group" aria-label="Select chart time range" className="flex flex-wrap gap-1 rounded-xl bg-[#f4f6f2] p-1">
          {periods.map((option) => <button key={option.key} type="button" aria-pressed={period === option.key} onClick={() => setPeriod(option.key)} className={`rounded-lg px-3 py-2 text-[11px] font-semibold transition ${period === option.key ? 'bg-white text-[#274c3b] shadow-sm' : 'text-[#7e8b81] hover:text-[#274c3b]'}`}>{option.label}</button>)}
        </div>
      </div>

      <div className="p-5 md:p-7">
        <div className="min-w-0">
          <div className="mb-3 flex items-center gap-4 text-[11px] font-medium text-[#758279]"><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#709b75]"/>Found</span><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#d2a364]"/>Lost</span></div>
          <div className="relative">
            <svg className="h-auto w-full overflow-visible" viewBox="0 0 720 220" role="img" aria-label={`Lost and found reports over ${periods.find((option) => option.key === period)?.label}`}>
              {[0, 1, 2, 3].map((line) => {
                const y = 14 + (line * 176) / 3;
                const label = Math.round((maximum * (3 - line)) / 3);
                return <g key={line}><line x1="36" x2="708" y1={y} y2={y} stroke="#edf1ec" strokeDasharray={line === 3 ? undefined : '3 5'}/><text x="25" y={y + 4} textAnchor="end" fontSize="10" fill="#9aa59c">{label}</text></g>;
              })}
              <path d={makeLine(points, 'found')} fill="none" stroke="#709b75" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
              <path d={makeLine(points, 'lost')} fill="none" stroke="#d2a364" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
              {points.map((point, index) => {
                const x = 36 + (points.length <= 1 ? 336 : (index * 672) / (points.length - 1));
                const yFor = (value: number) => 14 + 176 - (value / maximum) * 176;
                return <g key={`${point.label}-${index}`}>
                  <circle cx={x} cy={yFor(point.found)} r="4" fill="white" stroke="#709b75" strokeWidth="2"><title>{`${point.label}: ${point.found} found reports`}</title></circle>
                  <circle cx={x} cy={yFor(point.lost)} r="4" fill="white" stroke="#d2a364" strokeWidth="2"><title>{`${point.label}: ${point.lost} lost reports`}</title></circle>
                  <text x={x} y="214" textAnchor="middle" fontSize="10" fill="#9aa59c">{point.label}</text>
                </g>;
              })}
            </svg>
            {totalReports === 0 ? <p className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-center text-xs text-[#98a39b]">No reports were created in this period.</p> : null}
          </div>
        </div>
      </div>
    </section>
  </div>;
}
