import Link from 'next/link';
import { ArrowRight, ArrowUpRight, CalendarDays, MapPin, PackageSearch, Search, SlidersHorizontal } from 'lucide-react';
import { SiteFooter, SiteHeader } from '@/components/site-header';
import { getDjangoSession } from '@/lib/django-session';

type Item = {
  id: number;
  title: string;
  description: string;
  item_type: string;
  category: string | null;
  location: string;
  building: string;
  room: string;
  workstation: string;
  date_occurred: string;
  approximate_time: string | null;
  image: string | null;
  reporter_name?: string;
  reporter_username?: string;
  reporter_avatar?: string | null;
};

type Payload = {
  results: Item[];
  count: number;
  categories: { id: number; name: string }[];
  page: number;
  num_pages: number;
  has_previous: boolean;
  has_next: boolean;
};

type BrowseParams = { q?: string; type?: string; category?: string; page?: string; submitted?: string };

async function getItems(search: string, kind: string, category: string, page: string): Promise<Payload | null> {
  const base = process.env.DJANGO_URL ?? 'http://127.0.0.1:8000';
  try {
    const params = new URLSearchParams();
    if (search) params.set('q', search);
    if (kind) params.set('type', kind);
    if (category) params.set('category', category);
    if (page) params.set('page', page);
    const response = await fetch(`${base}/api/items/?${params.toString()}`, { cache: 'no-store' });
    if (!response.ok) return null;
    return await response.json() as Payload;
  } catch {
    return null;
  }
}

function browseHref(values: BrowseParams, page?: number) {
  const params = new URLSearchParams();
  if (values.q) params.set('q', values.q);
  if (values.type) params.set('type', values.type);
  if (values.category) params.set('category', values.category);
  if (page !== undefined) params.set('page', String(page));
  const query = params.toString();
  return `/browse/${query ? `?${query}` : ''}`;
}

export default async function BrowsePage({ searchParams }: { searchParams: Promise<BrowseParams> }) {
  const params = await searchParams;
  const q = params.q ?? '';
  const type = params.type ?? '';
  const category = params.category ?? '';
  const [data, session] = await Promise.all([
    getItems(q, type, category, params.page ?? '1'),
    getDjangoSession(),
  ]);

  return <main className="min-h-screen bg-[#f8f9f6]"><SiteHeader active="/browse" />
    <section className="mx-auto max-w-7xl px-6 pb-16 pt-12 md:px-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#709078]">Let’s bring something home</p>
          <h1 className="mt-2 text-4xl font-semibold md:text-5xl">The community <span className="serif text-[#598467]">board.</span></h1>
          <p className="mt-3 text-sm text-[#7c8980]">{data ? `${data.count} active ${data.count === 1 ? 'report' : 'reports'} from your community` : 'Community reports are temporarily unavailable'}</p>
        </div>
        {session.authenticated ? <div className="flex gap-2">
          <Link href="/items/report/lost/" className="rounded-xl border border-[#e2e8e1] bg-white px-4 py-3 text-xs font-semibold text-[#405148]">Report lost</Link>
          <Link href="/items/report/found/" className="rounded-xl bg-[#274c3b] px-4 py-3 text-xs font-semibold text-white">Report found</Link>
        </div> : <Link href="/login/" className="text-sm font-semibold text-[#55705d]">Sign in to view your activity <ArrowRight size={15} className="ml-1 inline"/></Link>}
      </div>

      {params.submitted === '1' ? <p role="status" className="mt-6 rounded-xl border border-[#dce8dc] bg-[#eff5eb] px-5 py-4 text-sm font-medium text-[#42664b]">Your {type === 'LOST' ? 'lost' : 'found'} report was posted. It is now visible in Explore Items.</p> : null}

      <form action="/browse/" className="mt-8 grid gap-3 rounded-2xl border border-[#e8ece5] bg-white p-4 md:grid-cols-[1fr_180px_200px_auto]">
        <label className="flex items-center gap-3 rounded-xl bg-[#f7f8f5] px-4"><Search size={17} className="text-[#8b968e]"/><input className="w-full bg-transparent py-3 text-sm outline-none placeholder:text-[#a3aaa4]" type="search" name="q" defaultValue={q} placeholder="Search a name, place, or category..."/></label>
        <label className="flex items-center gap-2 rounded-xl bg-[#f7f8f5] px-3"><SlidersHorizontal size={16} className="text-[#87958a]"/><select name="type" defaultValue={type} className="w-full bg-transparent py-3 text-sm text-[#506056] outline-none"><option value="">Everything</option><option value="LOST">Lost items</option><option value="FOUND">Found items</option></select></label>
        <label className="rounded-xl bg-[#f7f8f5] px-3"><select name="category" defaultValue={category} className="w-full bg-transparent py-3 text-sm text-[#506056] outline-none"><option value="">All categories</option>{data?.categories.map((cat) => <option key={cat.id} value={cat.id}>{cat.name}</option>)}</select></label>
        <button className="rounded-xl bg-[#274c3b] px-6 py-3 text-sm font-semibold text-white">Search</button>
      </form>

      <div className="mt-5 flex flex-wrap gap-2">{[['', 'All items'], ['FOUND', 'Found'], ['LOST', 'Lost']].map(([value, label]) => <Link key={value} href={browseHref({ q, category, type: value })} className={`rounded-full px-4 py-2 text-xs font-semibold ${type === value ? 'bg-[#274c3b] text-white' : 'border border-[#e6eae4] bg-white text-[#708078]'}`}>{label}</Link>)}</div>

      {!data ? <div role="alert" className="mt-8 rounded-2xl border border-[#efd9d2] bg-white px-6 py-12 text-center">
        <h2 className="text-xl font-semibold text-[#78574d]">Reports are temporarily unavailable.</h2>
        <p className="mt-2 text-sm text-[#829087]">We couldn’t reach the report service. Your filters are saved; try again in a moment.</p>
        <Link href={browseHref(params, Number(params.page) || 1)} className="mt-5 inline-flex rounded-xl bg-[#274c3b] px-5 py-3 text-sm font-semibold text-white">Retry</Link>
      </div> : data.results.length ? <>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.results.map((item) => <Link href={`/items/${item.id}/`} key={item.id} className="group overflow-hidden rounded-2xl border border-[#e8ece5] bg-white transition hover:-translate-y-1 hover:shadow-xl hover:shadow-[#274c3b]/[.07]">
          <div className="relative grid h-52 place-items-center overflow-hidden bg-[#edf1e9]">{item.image ? <img className="h-full w-full object-cover transition duration-500 group-hover:scale-105" src={item.image} alt={item.title}/> : <div className="grid h-16 w-16 place-items-center rounded-2xl bg-white/80 text-[#739076]"><PackageSearch size={28}/></div>}<span className={`absolute left-4 top-4 rounded-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${item.item_type === 'FOUND' ? 'bg-[#e1eddb] text-[#527254]' : 'bg-[#f7e9d4] text-[#936b32]'}`}>{item.item_type === 'FOUND' ? 'Found' : 'Lost'}</span></div>
          <div className="p-5"><div className="flex items-start justify-between gap-3"><h2 className="text-lg font-semibold">{item.title}</h2><ArrowUpRight size={16} className="mt-1 shrink-0 text-[#8b968e] transition group-hover:text-[#426e51]"/></div>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-[#7d8981]">{item.description}</p>
            <div className="mt-4 flex items-center gap-2.5 border-t border-[#edf0eb] pt-4"><span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-full bg-[#e9f0e7] text-xs font-semibold text-[#47634d]">{item.reporter_avatar ? <img src={item.reporter_avatar} alt="" className="h-full w-full object-cover"/> : (item.reporter_name || 'Community member').split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span><span className="min-w-0"><span className="block truncate text-xs font-semibold text-[#405148]">{item.reporter_name || 'Community member'}</span><span className="block truncate text-[10px] text-[#8b968e">@{item.reporter_username || 'member'} · Reporter</span></span></div>
            <div className="mt-4 border-t border-[#edf0eb] pt-3 text-[11px] text-[#869188]"><span className="block"><MapPin size={13} className="mr-1 inline"/>{[item.location, item.building, item.room, item.workstation].filter(Boolean).join(' | ')}</span><span className="mt-2 block"><CalendarDays size={13} className="mr-1 inline"/>{item.date_occurred}{item.approximate_time ? ` | around ${item.approximate_time.slice(0, 5)}` : ''}</span>{item.item_type === 'FOUND' ? <span className="mt-4 inline-flex rounded-lg bg-[#eff5eb] px-3 py-2 text-xs font-semibold text-[#42664b]">View details to claim <ArrowRight size={14} className="ml-1"/></span> : null}</div>
          </div>
        </Link>)}</div>
        {data.num_pages > 1 ? <nav aria-label="Browse pages" className="mt-8 flex items-center justify-center gap-4">
          <Link aria-disabled={!data.has_previous} className={`rounded-lg border px-4 py-2 text-sm ${data.has_previous ? 'border-[#dce5da] bg-white text-[#49624f]' : 'pointer-events-none border-[#edf0eb] text-[#aab2aa]'}`} href={browseHref(params, Math.max(1, data.page - 1))}>Previous</Link>
          <span aria-live="polite" className="text-sm text-[#718078]">Page {data.page} of {data.num_pages}</span>
          <Link aria-disabled={!data.has_next} className={`rounded-lg border px-4 py-2 text-sm ${data.has_next ? 'border-[#dce5da] bg-white text-[#49624f]' : 'pointer-events-none border-[#edf0eb] text-[#aab2aa]'}`} href={browseHref(params, Math.min(data.num_pages, data.page + 1))}>Next</Link>
        </nav> : null}
      </> : <div className="mt-8 rounded-2xl border border-dashed border-[#dce4d9] bg-white px-6 py-20 text-center"><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#eff4eb] text-[#658267]"><PackageSearch size={24}/></div><h2 className="mt-5 text-xl font-semibold">It’s quiet around here.</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-[#829087]">{q ? 'Try a different search, or clear your filters to see more items.' : 'There are no active reports just yet. Share a lost or found item to help your community get started.'}</p><Link href="/items/report/found/" className="mt-6 inline-flex items-center rounded-xl bg-[#274c3b] px-5 py-3 text-sm font-semibold text-white">Share a found item <ArrowRight size={15} className="ml-2"/></Link></div>}
    </section><SiteFooter />
  </main>;
}
