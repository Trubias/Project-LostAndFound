'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowUpRight, PackageSearch } from 'lucide-react';
import { useAdminRecordDrawer } from './record-drawer';

export type AdminRecord = { id: number; title: string; subtitle?: string; badge?: string; href?: string; meta?: string[]; image?: string | null; type?: string };

export function AdminRecordsTable({ records, emptyLabel = 'No records yet.' }: { records: AdminRecord[]; emptyLabel?: string }) {
  const { openRecord } = useAdminRecordDrawer();
  const router = useRouter();
  const [updatingNotificationId, setUpdatingNotificationId] = useState<number | null>(null);
  const [notificationError, setNotificationError] = useState('');

  async function markNotificationRead(id: number) {
    setUpdatingNotificationId(id);
    setNotificationError('');
    try {
      const csrfResponse = await fetch('/api/csrf/', { cache: 'no-store' });
      if (!csrfResponse.ok) throw new Error('Could not prepare the request. Please try again.');
      const { csrfToken } = await csrfResponse.json() as { csrfToken: string };
      const response = await fetch(`/api/django/api/admin/notifications/${id}/read/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken },
      });
      if (!response.ok) throw new Error('Could not mark this notification as read. Please try again.');
      router.refresh();
    } catch (error) {
      setNotificationError(error instanceof Error ? error.message : 'Could not update the notification.');
    } finally {
      setUpdatingNotificationId(null);
    }
  }

  return <div className="mt-7 overflow-hidden rounded-[18px] border border-[#e6ebe4] bg-white">
    {notificationError ? <p role="alert" className="border-b border-[#f0d8d3] bg-[#fff8f6] px-6 py-3 text-sm text-[#9b5145]">{notificationError}</p> : null}
    {records.length ? <div className="max-h-[calc(100vh-15rem)] min-h-[300px] overflow-auto overscroll-contain">
      <table className="w-full min-w-[850px] border-collapse text-left">
        <thead className="sticky top-0 z-20 bg-[#f5f7f3] text-[10px] font-bold uppercase tracking-[.13em] text-[#89958c]">
          <tr className="border-b border-[#e9eee7]"><th scope="col" className="px-6 py-4">Record</th><th scope="col" className="px-6 py-4">Context</th><th scope="col" className="px-6 py-4">Activity &amp; audit trail</th><th scope="col" className="px-6 py-4">State</th><th scope="col" className="px-6 py-4"><span className="sr-only">Actions</span></th></tr>
        </thead>
        <tbody className="divide-y divide-[#edf0eb]">{records.map((record) => <tr key={record.id} className="align-top transition hover:bg-[#fbfcfa]">
          <td className="px-6 py-4"><p className="text-[10px] font-semibold uppercase tracking-wide text-[#9aa59c]">Record #{record.id}</p><p className="mt-1 max-w-[280px] font-semibold text-[#283a30]">{record.title}</p></td>
          <td className="px-6 py-4 text-sm leading-6 text-[#738077]">{record.subtitle || 'No additional context'}</td>
          <td className="px-6 py-4">{record.meta?.length ? <ul className="space-y-1">{record.meta.map((entry, index) => <li key={`${record.id}-${index}`} className="break-words text-xs leading-5 text-[#7d8980]">{entry}</li>)}</ul> : <span className="text-xs text-[#9aa59c]">No activity recorded</span>}</td>
          <td className="px-6 py-4">{record.href?.startsWith('/admin-dashboard/notifications/') && record.badge === 'Unread' ? <button type="button" onClick={() => { openRecord(record); void markNotificationRead(record.id); }} disabled={updatingNotificationId === record.id} className="inline-flex whitespace-nowrap rounded-full border border-[#e5ebe2] bg-[#f4f7f2] px-3 py-1.5 text-[10px] font-semibold text-[#526b57] transition hover:border-[#c9d9c9] hover:bg-[#edf3e9] disabled:cursor-wait disabled:opacity-60" aria-label={`Open and mark notification ${record.id} as read`}>{updatingNotificationId === record.id ? 'Updating…' : record.badge}</button> : <span className="inline-flex whitespace-nowrap rounded-full border border-[#e5ebe2] bg-[#f4f7f2] px-3 py-1.5 text-[10px] font-semibold text-[#526b57]">{record.badge || 'Recorded'}</span>}</td>
          <td className="px-6 py-4 text-right"><button type="button" onClick={() => openRecord(record)} className="inline-flex whitespace-nowrap items-center gap-1 text-xs font-semibold text-[#557b60] hover:underline">Open record <ArrowUpRight size={13}/></button></td>
        </tr>)}</tbody>
      </table>
    </div> : <div className="px-6 py-14 text-center"><PackageSearch className="mx-auto text-[#829087]" size={22}/><p className="mt-3 text-sm font-semibold text-[#405148]">{emptyLabel}</p><p className="mt-2 text-xs text-[#87938a]">New records and their activity will appear here.</p></div>}
  </div>;
}
