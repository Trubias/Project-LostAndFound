'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

export function AccountMenu({ name, avatar, dashboard = '/dashboard', roleLabel = 'Community member', size = 'regular' }: {
  name: string; avatar?: string | null; dashboard?: string; roleLabel?: string; size?: 'regular' | 'small';
}) {
  const [open, setOpen] = useState(false);
  const [csrf, setCsrf] = useState('');
  const menu = useRef<HTMLDivElement>(null);
  const initials = name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase();

  useEffect(() => {
    let mounted = true;
    fetch('/api/csrf/', { cache: 'no-store' }).then((response) => response.ok ? response.json() as Promise<{ csrfToken: string }> : Promise.reject())
      .then(({ csrfToken }) => { if (mounted) setCsrf(csrfToken); }).catch(() => undefined);
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    function closeOnOutside(event: MouseEvent) { if (!menu.current?.contains(event.target as Node)) setOpen(false); }
    function closeOnEscape(event: KeyboardEvent) { if (event.key === 'Escape') setOpen(false); }
    document.addEventListener('mousedown', closeOnOutside);
    document.addEventListener('keydown', closeOnEscape);
    return () => { document.removeEventListener('mousedown', closeOnOutside); document.removeEventListener('keydown', closeOnEscape); };
  }, []);

  const avatarSize = size === 'small' ? 'h-9 w-9' : 'h-10 w-10';
  return <div className="relative" ref={menu}>
    <button type="button" aria-label="Open account menu" aria-expanded={open} aria-haspopup="menu" onClick={() => setOpen((value) => !value)} className={`grid ${avatarSize} shrink-0 place-items-center overflow-hidden rounded-full border-2 border-white bg-[#dce8d8] text-xs font-bold text-[#365b43] shadow-sm ring-1 ring-[#dce5d8] transition hover:ring-[#91aa91]`}>
      {avatar ? <img src={avatar} alt="" className="h-full w-full object-cover"/> : initials || 'U'}
    </button>
    {open ? <div role="menu" aria-label="Account options" className="absolute right-0 top-[calc(100%+10px)] z-50 w-64 overflow-hidden rounded-2xl border border-[#e5ebe3] bg-white p-2 shadow-[0_22px_60px_-25px_rgba(25,55,37,.3)]">
      <div className="border-b border-[#edf0eb] px-3 py-3"><p className="truncate text-sm font-semibold text-[#304237]">{name}</p><p className="mt-1 text-[11px] text-[#87938a]">{roleLabel}</p></div>
      <div className="py-1"><Link role="menuitem" href={dashboard} onClick={() => setOpen(false)} className="block rounded-xl px-3 py-2.5 text-xs font-medium text-[#596b5e] transition hover:bg-[#f5f8f3]">Dashboard</Link><Link role="menuitem" href="/profile" onClick={() => setOpen(false)} className="block rounded-xl px-3 py-2.5 text-xs font-medium text-[#596b5e] transition hover:bg-[#f5f8f3]">Settings</Link></div>
      <form method="post" action="/api/django/logout/" className="border-t border-[#edf0eb] pt-1"><input type="hidden" name="csrfmiddlewaretoken" value={csrf}/><button role="menuitem" type="submit" disabled={!csrf} className="w-full rounded-xl px-3 py-2.5 text-left text-xs font-semibold text-[#8c5d52] transition hover:bg-[#fbf4f1] disabled:cursor-wait disabled:opacity-60">{csrf ? 'Log out' : 'Preparing secure sign out…'}</button></form>
    </div> : null}
  </div>;
}
