import Link from 'next/link';
import { ArrowRight, CheckCircle2, FileText, HeartHandshake, Search } from 'lucide-react';
import { SiteFooter, SiteHeader } from '@/components/site-header';

const steps = [
  { number: '01', icon: Search, title: 'Start with a search', text: 'Look through recent lost and found reports. Search by item name, category, or the place it was last seen.' },
  { number: '02', icon: FileText, title: 'Share a few details', text: 'If it is not listed, report the item. A clear description and the last known location help your community recognize it.' },
  { number: '03', icon: HeartHandshake, title: 'Reconnect safely', text: 'When something looks familiar, submit a claim with details that help confirm it is yours. Coordinate a handoff with the reporter.' },
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#f8f9f6]">
      <SiteHeader active="/how-it-works" />
      <section className="mx-auto max-w-[1440px] px-6 pb-12 pt-16 md:px-12 md:pt-24">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#dce8dc] bg-white/80 px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[.14em] text-[#467356]">Easy to use, built around people</div>
          <h1 className="mt-7 text-5xl font-semibold leading-[1.03] md:text-7xl">A few small steps.<br/><span className="serif text-[#598467]">A happy reunion.</span></h1>
          <p className="mt-6 max-w-lg text-[15px] leading-7 text-[#718078]">Whether you’ve lost something or picked it up, Findly helps your community make the connection.</p>
        </div>
        <div className="mt-12 grid gap-3 md:grid-cols-3 md:gap-4">
          {steps.map(({ number, icon: Icon, title, text }) => (
            <article key={number} className="rounded-2xl border border-[#e8ece5] bg-white p-6 md:p-7">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold text-[#9eaa9e]">{number}</span><span className="grid h-11 w-11 place-items-center rounded-xl bg-[#eff4eb] text-[#52765b]"><Icon size={19}/></span></div>
              <h2 className="mt-8 text-xl font-semibold">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-[#7b8780]">{text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="mx-6 mb-20 rounded-2xl bg-[#edf2e9] p-7 md:mx-12 md:flex md:items-center md:justify-between md:p-10">
        <div className="flex max-w-xl gap-4"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-[#52765b]"><CheckCircle2 size={19}/></span><div><h2 className="text-lg font-semibold">A helpful detail can make all the difference.</h2><p className="mt-2 text-sm leading-6 text-[#718078]">For claims, mention a detail only the owner would know. Keep private contact information out of public item descriptions.</p></div></div>
        <Link href="/browse" className="mt-6 inline-flex items-center rounded-xl bg-[#274c3b] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#1e3d2f] md:mt-0">Explore items <ArrowRight size={15} className="ml-2"/></Link>
      </section>
      <SiteFooter />
    </main>
  );
}
