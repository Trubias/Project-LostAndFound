'use client';

import Link from 'next/link';
import type { OverviewStat, ReportTrends } from './overview';
import type { AdminRecord } from './records-table';
import { useAdminRecordDrawer } from './record-drawer';

type CategoryMetric = { name: string; total: number; lost: number; found: number };
type ClaimMetric = { label: string; value: number };

export function ReportsAnalytics({ stats, trends, categories, claims, activity }: {
  stats: OverviewStat[]; trends: ReportTrends; categories: CategoryMetric[]; claims: ClaimMetric[]; activity: AdminRecord[];
}) {
  const { openRecord } = useAdminRecordDrawer();
  const points = trends['1y'] ?? [];
  const maxReports = Math.max(1, ...points.map((point) => point.lost + point.found));
  const maxCategory = Math.max(1, ...categories.map((row) => row.total));
  const maxClaim = Math.max(1, ...claims.map((row) => row.value));
  const totalClaims = claims.reduce((total, row) => total + row.value, 0);

  return <div className="mt-8 flex flex-col gap-5">
    <section className="order-1 overflow-hidden rounded-[22px] border border-[#e6ebe4] bg-white shadow-[0_18px_55px_-42px_rgba(25,55,37,.28)]">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[#edf0eb] px-6 py-5 md:px-7"><div><p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#79917c]">12 month view</p><h2 className="mt-1 text-lg font-semibold text-[#293b30]">Lost and found reports</h2><p className="mt-1 text-xs text-[#87938a]">Number of reports created in each month.</p></div><div className="flex gap-4 text-[11px] font-medium text-[#758279]"><span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[#709b75]"/>Found</span><span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[#d2a364]"/>Lost</span></div></div>
      <div className="p-5 md:p-7"><svg className="h-auto w-full" viewBox="0 0 760 250" role="img" aria-label="Monthly lost and found report totals over the last 12 months">
        {[0, 1, 2, 3].map((row) => { const y = 18 + row * 58; return <g key={row}><line x1="44" x2="748" y1={y} y2={y} stroke="#edf1ec" strokeDasharray={row === 3 ? undefined : '4 5'}/><text x="32" y={y + 4} textAnchor="end" fontSize="10" fill="#9aa59c">{Math.round(maxReports * (3 - row) / 3)}</text></g>; })}
        {points.map((point, index) => { const x = 48 + (index * 696) / Math.max(points.length - 1, 1); const foundHeight = (point.found / maxReports) * 174; const lostHeight = (point.lost / maxReports) * 174; return <g key={`${point.label}-${index}`}><rect x={x - 11} y={192 - foundHeight} width="10" height={foundHeight} rx="4" fill="#709b75"><title>{`${point.label}: ${point.found} found`}</title></rect><rect x={x + 1} y={192 - lostHeight} width="10" height={lostHeight} rx="4" fill="#d2a364"><title>{`${point.label}: ${point.lost} lost`}</title></rect><text x={x} y="218" textAnchor="middle" fontSize="9" fill="#8d9990">{point.label}</text></g>; })}
      </svg></div>
    </section>

    <section aria-label="Report metrics" className="order-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{stats.map((stat) => <article key={stat.label} className="rounded-2xl border border-[#e7ece5] bg-white p-5 shadow-[0_14px_36px_-30px_rgba(31,60,42,.28)]"><p className="text-[10px] font-semibold uppercase tracking-[.13em] text-[#87938a]">{stat.label}</p><p className="mt-2 text-3xl font-semibold tracking-tight text-[#34483a]">{stat.value}</p><p className="mt-2 text-[11px] text-[#89958c]">All time</p></article>)}</section>

    <div className="order-3 grid gap-6 xl:grid-cols-2">
      <section className="rounded-[22px] border border-[#e6ebe4] bg-white p-6 shadow-[0_18px_55px_-42px_rgba(25,55,37,.28)]"><div><p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#79917c]">Report distribution</p><h2 className="mt-1 text-lg font-semibold text-[#293b30]">Popular categories</h2><p className="mt-1 text-xs text-[#87938a]">Lost and found reports recorded under each category.</p></div>
        {categories.length ? <div className="mt-6 space-y-5">{categories.map((category) => <div key={category.name}><div className="mb-2 flex items-center justify-between gap-3 text-xs"><span className="font-semibold text-[#45564b]">{category.name}</span><span className="text-[#89958c]">{category.total} total</span></div><div className="flex h-2.5 overflow-hidden rounded-full bg-[#eff2ed]"><span className="bg-[#709b75]" style={{ width: `${category.lost / maxCategory * 100}%` }}/><span className="bg-[#d2a364]" style={{ width: `${category.found / maxCategory * 100}%` }}/></div><div className="mt-1.5 flex gap-4 text-[10px] text-[#8a968d]"><span>Lost {category.lost}</span><span>Found {category.found}</span></div></div>)}</div> : <p className="mt-7 text-sm text-[#829087]">No category activity recorded.</p>}
        <div className="mt-5 flex gap-4 border-t border-[#edf0eb] pt-4 text-[10px] text-[#829087]"><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-[#709b75]"/>Lost</span><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-[#d2a364]"/>Found</span></div>
      </section>

      <section className="rounded-[22px] border border-[#e6ebe4] bg-white p-6 shadow-[0_18px_55px_-42px_rgba(25,55,37,.28)]"><div><p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#79917c]">Resolution transparency</p><h2 className="mt-1 text-lg font-semibold text-[#293b30]">Claim outcomes</h2><p className="mt-1 text-xs text-[#87938a]">Status of every claim in the system.</p></div>
        <div className="mt-6 flex h-36 items-end gap-3 border-b border-[#edf0eb] pb-0">{claims.map((claim) => <div key={claim.label} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2"><span className="text-[10px] font-semibold text-[#617267]">{claim.value}</span><div className="w-full max-w-16 rounded-t-lg bg-[#729b76] transition-all" style={{ height: `${Math.max(claim.value ? 8 : 2, claim.value / maxClaim * 82)}%`, opacity: claim.value ? .9 : .28 }}/><span className="mb-2 max-w-full truncate text-center text-[9px] text-[#89958c]">{claim.label}</span></div>)}</div>
        <p className="mt-4 text-[11px] text-[#87938a]">{totalClaims} claims recorded across all statuses.</p>
      </section>
    </div>

    <section className="order-4 overflow-hidden rounded-[22px] border border-[#e6ebe4] bg-white shadow-[0_18px_55px_-42px_rgba(25,55,37,.28)]"><div className="flex items-center justify-between gap-3 border-b border-[#edf0eb] px-6 py-5"><div><p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#79917c]">Audit trail</p><h2 className="mt-1 text-lg font-semibold text-[#293b30]">Recent community activity</h2></div><Link href="/admin-dashboard/items" className="text-xs font-semibold text-[#557b60] hover:underline">Open records</Link></div>
      {activity.length ? <div className="divide-y divide-[#edf0eb]">{activity.map((record) => <button type="button" key={`${record.href}-${record.id}`} onClick={() => openRecord(record)} className="flex w-full flex-wrap items-start justify-between gap-4 px-6 py-4 text-left transition hover:bg-[#fbfcfa]"><div><p className="text-sm font-semibold text-[#35473a]">{record.title}</p><p className="mt-1 text-xs text-[#829087]">{record.subtitle}</p><p className="mt-2 text-[10px] leading-5 text-[#94a097]">{record.meta?.join(' · ')}</p></div><span className="rounded-full bg-[#f2f5ef] px-3 py-1.5 text-[10px] font-semibold text-[#55705d]">{record.badge}</span></button>)}</div> : <p className="px-6 py-10 text-center text-sm text-[#829087]">No activity has been recorded yet.</p>}</section>
  </div>;
}
