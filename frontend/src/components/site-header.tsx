import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { getDjangoSession } from '@/lib/django-session';
import { AccountMenu } from '@/components/account-menu';

const links = [
  { href: '/browse', label: 'Explore items' },
  { href: '/how-it-works', label: 'How it works' },
  { href: '/community', label: 'Our community' },
];

export async function SiteHeader({ active, showNavigation = false }: { active?: string; showNavigation?: boolean }) {
  const session = await getDjangoSession();
  return (
    <header className="mx-auto w-full max-w-[1440px] px-6 md:px-12">
      <div className="flex min-h-[72px] items-center justify-between gap-4">
        <Link href="/" aria-label="f. findly. home" className="flex shrink-0 items-center gap-2.5 text-[17px] font-bold tracking-tight">
          <span aria-hidden="true" className="grid h-[30px] w-[30px] place-items-center rounded-[10px] bg-[#274c3b] text-[12px] text-white">f.</span>
          <span aria-hidden="true">findly<span className="-ml-2 text-[#8b9b8f]">.</span></span>
        </Link>
        {showNavigation ? <nav aria-label="Main navigation" className="hidden items-center gap-8 text-[12px] font-medium text-[#66746b] md:flex">
          {links.map((link) => <Link key={link.href} aria-current={active === link.href ? 'page' : undefined} className={`transition hover:text-[#274c3b] ${active === link.href ? 'text-[#274c3b]' : ''}`} href={link.href}>{link.label}</Link>)}
        </nav> : null}
        {session.authenticated ? <AccountMenu name={session.name ?? 'Your account'} avatar={session.avatar} dashboard={session.dashboard} roleLabel={session.isAdmin ? 'Administrator' : 'Community member'}/> : session.available ? <div className="flex shrink-0 items-center gap-2">
          <Link className="rounded-xl px-3 py-2 text-[12px] font-semibold text-[#41534a] transition hover:bg-white/70" href="/login/">Log in</Link>
          <Link className="rounded-xl bg-[#274c3b] px-3.5 py-2.5 text-[12px] font-semibold text-white transition hover:bg-[#1e3d2f] sm:px-4" href="/register/">Get started <ArrowUpRight className="ml-1 inline" size={13}/></Link>
        </div> : <span role="status" className="text-xs text-[#8b6b45]">Account service unavailable</span>}
      </div>
      {showNavigation ? <nav aria-label="Mobile navigation" className="flex justify-between gap-3 border-t border-[#e8ece5] py-3 text-[11px] font-medium text-[#66746b] md:hidden">
        {links.map((link) => <Link key={link.href} aria-current={active === link.href ? 'page' : undefined} className={`transition hover:text-[#274c3b] ${active === link.href ? 'text-[#274c3b]' : ''}`} href={link.href}>{link.label}</Link>)}
      </nav> : null}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-[#e8ece5] px-6 py-6 text-xs text-[#5f6c63] md:px-12">
      <Link href="/" className="font-bold text-[#3d5645]">findly.</Link>
      <span>Made for the things that matter — and the people who return them.</span>
      <Link href="/community" className="font-semibold text-[#55705d]">Join your community <ArrowUpRight size={13} className="ml-1 inline"/></Link>
    </footer>
  );
}
