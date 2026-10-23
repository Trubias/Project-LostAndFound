import Link from 'next/link';
import { ArrowLeft, ArrowRight, CircleHelp, ShieldCheck, type LucideIcon } from 'lucide-react';
import { AccountMenu } from '@/components/account-menu';

export type WorkspaceLink = { href: string; label: string; icon: LucideIcon };

export function WorkspaceFrame({ role, activePath, userName, avatar, nav, children }: {
  role: 'user' | 'admin';
  activePath: string;
  userName?: string;
  avatar?: string | null;
  nav: WorkspaceLink[];
  children: React.ReactNode;
}) {
  const isAdmin = role === 'admin';
  const name = userName || (isAdmin ? 'Administrator' : 'Your account');
  return <main className="min-h-screen bg-[#f5f7f3] text-[#203129] md:flex">
    <aside className="flex w-full shrink-0 flex-col border-b border-[#e6ebe4] bg-white px-4 py-4 md:min-h-screen md:w-[248px] md:border-b-0 md:border-r md:px-5 md:py-6">
      <Link href="/" className="mb-5 flex items-center gap-2.5 px-2 text-[17px] font-bold tracking-tight md:mb-10"><span className="grid h-8 w-8 place-items-center rounded-[10px] bg-[#274c3b] text-xs text-white">f.</span>findly<span className="-ml-2 text-[#8b9b8f]">.</span></Link>
      <p className="mb-2 hidden px-3 text-[10px] font-bold uppercase tracking-[.16em] text-[#98a39b] md:block">{isAdmin ? 'Administration' : 'Workspace'}</p>
      <nav aria-label={`${role} dashboard`} className="grid grid-cols-2 gap-1 sm:grid-cols-3 md:flex md:flex-col">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = activePath === href || (href !== '/admin-dashboard' && href !== '/dashboard' && activePath.startsWith(`${href}/`));
          return <Link key={href} href={href} aria-current={active ? 'page' : undefined} className={`flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-xs font-semibold transition md:text-[13px] ${active ? 'bg-[#edf3eb] text-[#274c3b]' : 'text-[#77847b] hover:bg-[#f7f9f6] hover:text-[#274c3b]'}`}><Icon size={16} strokeWidth={1.8}/>{label}</Link>;
        })}
      </nav>
      <div className="mt-auto hidden rounded-2xl bg-[#f6f8f4] p-4 md:block"><div className="grid h-9 w-9 place-items-center rounded-xl bg-white text-[#64806b]"><CircleHelp size={17}/></div><p className="mt-3 text-xs font-semibold">Need a hand?</p><p className="mt-1 text-[11px] leading-5 text-[#87938a]">Find something? Let the community help you get it back.</p><Link href="/browse" className="mt-3 inline-flex items-center gap-1 text-[11px] font-bold text-[#52765b]">Explore items <ArrowRight size={13}/></Link></div>
      <div className="mt-3 flex items-center border-t border-[#edf0eb] pt-3 md:mt-5 md:pt-4"><Link href="/" className="flex items-center gap-2 text-[11px] font-medium text-[#87938a] hover:text-[#274c3b]"><ArrowLeft size={14}/> Back to Findly</Link></div>
    </aside>
    <div className="min-w-0 flex-1">
      <header className="flex min-h-[70px] items-center justify-between border-b border-[#e7ebe5] bg-white/80 px-5 md:px-10"><div><p className="text-[10px] font-bold uppercase tracking-[.14em] text-[#95a198]">{isAdmin ? 'Findly admin' : 'Your Findly account'}</p><p className="mt-1 text-xs font-semibold text-[#536158]">{isAdmin ? 'Community management' : 'Personal workspace'}</p></div><div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-xs font-semibold text-[#34453b]">{name}</p><p className="mt-0.5 text-[10px] text-[#98a39b]">{isAdmin ? 'Administrator' : 'Community member'}</p></div><AccountMenu name={name} avatar={avatar} dashboard={isAdmin ? '/admin-dashboard' : '/dashboard'} roleLabel={isAdmin ? 'Administrator' : 'Community member'} size="small"/><ShieldCheck size={15} className={isAdmin ? 'text-[#67846c]' : 'hidden'}/></div></header>
      {children}
    </div>
  </main>;
}
