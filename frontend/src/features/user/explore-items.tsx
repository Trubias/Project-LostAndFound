'use client';

import Link from 'next/link';
import { useState } from 'react';
import { UserRecordsTable } from './records-table';

type ExploreRecord = { id: number; title: string; subtitle?: string; badge?: string; image?: string | null; href?: string; meta?: string[]; reporterName?: string; reporterUsername?: string; reporterAvatar?: string | null };

export function ExploreItemsSection({ lost, found }: { lost: ExploreRecord[]; found: ExploreRecord[] }) {
  const [selected, setSelected] = useState<'lost' | 'found'>('lost');
  const records = selected === 'lost' ? lost : found;

  return <section className="mt-12" aria-labelledby="explore-items-heading">
    <div className="text-center">
      <p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#709078]">Community board</p>
      <h2 id="explore-items-heading" className="mt-2 text-2xl font-semibold text-[#203129]">Explore lost and found items</h2>
      <p className="mt-2 text-sm text-[#829087]">Browse recent reports shared by your community.</p>
      <div className="mt-5 inline-flex border-b border-[#e3e9e1]" role="group" aria-label="Explore item type">
        {(['lost', 'found'] as const).map((type) => <button key={type} type="button" aria-pressed={selected === type} onClick={() => setSelected(type)} className={`min-w-24 border-b-2 px-5 py-2.5 text-sm font-semibold capitalize transition ${selected === type ? 'border-[#274c3b] text-[#274c3b]' : 'border-transparent text-[#68776d] hover:text-[#274c3b]'}`}>{type}</button>)}
      </div>
    </div>
    {records.length ? <UserRecordsTable records={records.map((record) => ({ ...record, badge: selected === 'lost' ? 'Lost' : 'Found', href: record.href ?? `/items/${record.id}` }))} showReporter emptyLabel={`No ${selected} reports yet.`}/> : <div className="mt-6 py-8 text-center"><p className="text-sm font-semibold text-[#405148]">No {selected} reports yet</p><p className="mt-2 text-sm leading-6 text-[#829087]">When community members share a {selected} item report, it will appear here.</p><Link href={`/items/report/${selected}`} className="mt-4 inline-flex text-xs font-semibold text-[#52765b] underline">Report a {selected} item</Link></div>}
    <div className="mt-5 text-center"><Link href={`/browse?type=${selected.toUpperCase()}`} className="text-sm font-semibold text-[#52765b] hover:underline">View all {selected} items</Link></div>
  </section>;
}
