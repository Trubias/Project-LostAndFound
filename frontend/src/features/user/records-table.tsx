import Link from 'next/link';
import { ArrowUpRight, PackageSearch } from 'lucide-react';

export type UserRecord = {
  id: number;
  title: string;
  subtitle?: string;
  badge?: string;
  href?: string;
  actionLabel?: string;
  meta?: string[];
  image?: string | null;
  reporterName?: string;
  reporterUsername?: string;
  reporterAvatar?: string | null;
};

export function UserRecordsTable({ records, emptyLabel = 'No records yet.', showReporter = false }: { records: UserRecord[]; emptyLabel?: string; showReporter?: boolean }) {
  return <div className="mt-5 overflow-hidden border-y border-[#e5ebe3] bg-white">
    {records.length ? <div className="max-h-[calc(100vh-18rem)] overflow-auto overscroll-contain">
      <table className="w-full min-w-[780px] border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-[#f4f6f2] text-[10px] font-bold uppercase tracking-[.12em] text-[#718078]">
          <tr className="border-b border-[#e6ece4]"><th scope="col" className="px-5 py-3">Report</th><th scope="col" className="px-5 py-3">Description</th>{showReporter ? <th scope="col" className="px-5 py-3">Reported by</th> : null}<th scope="col" className="px-5 py-3">Details</th><th scope="col" className="px-5 py-3">Status</th><th scope="col" className="px-5 py-3"><span className="sr-only">Action</span></th></tr>
        </thead>
        <tbody className="divide-y divide-[#edf0eb]">{records.map((record) => <tr key={record.id} className="align-top hover:bg-[#fbfcfa]">
          <td className="px-5 py-4"><div className="flex items-center gap-3">{record.image ? <img src={record.image} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover"/> : null}<div><p className="text-[10px] text-[#89958c]">Report #{record.id}</p><p className="mt-1 max-w-[220px] font-semibold text-[#293b30]">{record.title}</p></div></div></td>
          <td className="max-w-[300px] px-5 py-4 text-sm leading-5 text-[#718078]">{record.subtitle || '—'}</td>
          {showReporter ? <td className="px-5 py-4"><div className="flex items-center gap-2.5">{record.reporterAvatar ? <img src={record.reporterAvatar} alt="" className="h-8 w-8 rounded-full object-cover"/> : <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-full bg-[#edf2e9] text-[10px] font-semibold text-[#47634d]">{record.reporterName?.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase() || 'U'}</span>}<span><span className="block text-xs font-semibold text-[#405148]">{record.reporterName || 'Community member'}</span>{record.reporterUsername ? <span className="text-[10px] text-[#89958c]">@{record.reporterUsername}</span> : null}</span></div></td> : null}
          <td className="px-5 py-4">{record.meta?.length ? <ul className="space-y-1">{record.meta.map((detail, index) => <li key={`${record.id}-${index}`} className="text-xs leading-5 text-[#7b8780]">{detail}</li>)}</ul> : <span className="text-xs text-[#9aa59c]">—</span>}</td>
          <td className="px-5 py-4"><span className="whitespace-nowrap text-xs font-medium text-[#526b57]">{record.badge || 'Active'}</span></td>
          <td className="px-5 py-4 text-right">{record.href ? <Link href={record.href} className="inline-flex items-center gap-1 whitespace-nowrap text-xs font-semibold text-[#52765b] hover:underline">{record.actionLabel || 'View'} <ArrowUpRight size={13}/></Link> : null}</td>
        </tr>)}</tbody>
      </table>
    </div> : <div className="py-10 text-center"><PackageSearch className="mx-auto text-[#829087]" size={21}/><p className="mt-3 text-sm font-semibold text-[#405148]">{emptyLabel}</p></div>}
  </div>;
}
