'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { X } from 'lucide-react';

export type DrawerRecord = { id: number; title: string; subtitle?: string; badge?: string; href?: string; meta?: string[]; image?: string | null; type?: string };
const RecordDrawerContext = createContext<{ openRecord: (record: DrawerRecord) => void } | null>(null);

export function useAdminRecordDrawer() {
  const context = useContext(RecordDrawerContext);
  if (!context) throw new Error('useAdminRecordDrawer must be used inside AdminRecordDrawerProvider');
  return context;
}

export function AdminRecordDrawerProvider({ children }: { children: React.ReactNode }) {
  const [record, setRecord] = useState<DrawerRecord | null>(null);
  const [detail, setDetail] = useState<{ summary?: string; stats?: { label: string; value: string | number }[]; fields?: { label: string; value?: string }[]; links?: { label: string; href: string }[] } | null>(null);
  const openRecord = useCallback((next: DrawerRecord) => setRecord(next), []);
  const context = useMemo(() => ({ openRecord }), [openRecord]);

  useEffect(() => {
    if (!record) return;
    let active = true;
    setDetail(null);
    if (record.href) {
      const query = new URLSearchParams({ path: record.href });
      fetch(`/api/django/api/frontend-page/?${query}`, { credentials: 'same-origin' })
        .then((response) => response.ok ? response.json() : null)
        .then((data) => { if (active && data && data.mode !== 'error') setDetail(data); })
        .catch(() => undefined);
    }
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') setRecord(null); };
    document.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';
    return () => { active = false; document.removeEventListener('keydown', onKeyDown); document.body.style.overflow = ''; };
  }, [record]);

  return <RecordDrawerContext.Provider value={context}>{children}{record ? <div className="fixed inset-0 z-[100] flex justify-end" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setRecord(null); }}>
    <div className="absolute inset-0 bg-[#17251d]/35 backdrop-blur-[2px]"/>
    <aside role="dialog" aria-modal="true" aria-labelledby="record-drawer-title" className="relative flex h-full w-full max-w-xl animate-in slide-in-from-right flex-col bg-[#fbfcfa] shadow-2xl">
      <header className="flex items-start justify-between gap-5 border-b border-[#e7ece5] bg-white px-6 py-5 sm:px-8"><div><p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#79917c]">Record details · #{record.id}</p><h2 id="record-drawer-title" className="mt-2 text-xl font-semibold text-[#25372c]">{record.title}</h2>{record.subtitle ? <p className="mt-1 text-sm text-[#79867d]">{record.subtitle}</p> : null}</div><button type="button" onClick={() => setRecord(null)} aria-label="Close record details" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[#e5ebe3] bg-white text-[#5e7063] hover:bg-[#f2f5ef]"><X size={18}/></button></header>
      <div className="flex-1 overflow-y-auto p-6 sm:p-8">{record.image ? <img src={record.image} alt="" className="mb-6 max-h-72 w-full rounded-2xl object-cover"/> : null}
        {record.badge ? <span className="inline-flex rounded-full bg-[#edf3e9] px-3 py-1.5 text-xs font-semibold text-[#4c6c51]">{record.badge}</span> : null}
        {detail?.summary ? <p className="mt-5 rounded-2xl border border-[#e6ebe4] bg-white p-5 text-sm leading-6 text-[#617168]">{detail.summary}</p> : null}
        {detail?.stats?.length ? <dl className="mt-4 divide-y divide-[#e9eee7] rounded-2xl border border-[#e6ebe4] bg-white px-5">{detail.stats.map((stat) => <div key={stat.label} className="flex justify-between gap-5 py-3 text-sm"><dt className="text-[#879188]">{stat.label}</dt><dd className="text-right font-medium text-[#405148]">{stat.value}</dd></div>)}</dl> : null}
        {detail?.fields?.length ? <dl className="mt-4 divide-y divide-[#e9eee7] rounded-2xl border border-[#e6ebe4] bg-white px-5">{detail.fields.map((field) => <div key={field.label} className="py-3 text-sm"><dt className="text-[10px] font-bold uppercase tracking-[.12em] text-[#8a968d]">{field.label}</dt><dd className="mt-1 break-words text-[#405148]">{field.value || '—'}</dd></div>)}</dl> : null}
        {detail?.links?.length ? <nav aria-label="Record actions" className="mt-5 flex flex-wrap gap-2">{detail.links.map((link) => <Link key={link.href} href={link.href} onClick={() => setRecord(null)} className="rounded-xl bg-[#274c3b] px-4 py-2.5 text-xs font-semibold text-white hover:bg-[#1e3d2f]">{link.label}</Link>)}</nav> : null}
        {record.meta?.length ? <dl className="mt-6 divide-y divide-[#e9eee7] rounded-2xl border border-[#e6ebe4] bg-white px-5">{record.meta.map((entry, index) => { const splitAt = entry.indexOf(':'); return <div key={`${index}-${entry}`} className="py-4"><dt className="text-[10px] font-bold uppercase tracking-[.12em] text-[#8a968d]">{splitAt > 0 ? entry.slice(0, splitAt) : `Details ${index + 1}`}</dt><dd className="mt-1 break-words text-sm leading-6 text-[#405148]">{splitAt > 0 ? entry.slice(splitAt + 1).trim() : entry}</dd></div>; })}</dl> : <p className="mt-6 rounded-2xl border border-dashed border-[#dbe4d9] bg-white p-5 text-sm text-[#78857c]">No additional record details are available.</p>}
        <p className="mt-5 text-xs leading-5 text-[#8a968d]">This record is shown without leaving the current admin section.</p>
      </div>
    </aside>
  </div> : null}</RecordDrawerContext.Provider>;
}
