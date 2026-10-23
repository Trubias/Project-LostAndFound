import { HeartHandshake } from 'lucide-react';
import { AuthForm } from '@/components/auth-form';
import { SiteFooter, SiteHeader } from '@/components/site-header';
import { getDjangoSession } from '@/lib/django-session';
import { redirect } from 'next/navigation';

export default async function RegisterPage({searchParams}:{searchParams:Promise<{error?:string}>}) {
  const [{error},session]=await Promise.all([searchParams,getDjangoSession()]);
  if(session.authenticated) redirect(session.dashboard ?? '/dashboard');
  return <main className="min-h-screen bg-[#f8f9f6]"><SiteHeader/><section className="mx-auto max-w-[1440px] px-6 py-12 md:px-12 md:py-16"><div className="mx-auto max-w-[470px] rounded-[28px] border border-[#e8ece5] bg-white p-7 shadow-[0_18px_70px_rgba(32,52,39,.07)] md:p-10"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-[#eff4eb] text-[#52765b]"><HeartHandshake size={22}/></div><p className="mt-6 text-center text-[10px] font-bold uppercase tracking-[.16em] text-[#709078]">A little kindness goes a long way</p><h1 className="mt-2 text-center text-3xl font-semibold">Join your community.</h1><p className="mt-2 text-center text-sm text-[#829087]">Create an account to report items and make a connection.</p><AuthForm mode="register" error={error==='1'}/></div></section><SiteFooter/></main>;
}
