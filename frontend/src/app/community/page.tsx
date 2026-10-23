import Link from 'next/link';
import { ArrowRight, Heart, HandHeart, MapPin, ShieldCheck } from 'lucide-react';
import { SiteFooter, SiteHeader } from '@/components/site-header';

const values = [
  { icon: HandHeart, title: 'A little kindness', text: 'Taking a moment to report a found item can turn someone’s stressful day around.' },
  { icon: ShieldCheck, title: 'Care with details', text: 'Share enough for an owner to recognize their belongings while keeping sensitive details private.' },
  { icon: MapPin, title: 'Local connections', text: 'People who study, work, and spend time in the same places are often best placed to help.' },
];

export default function CommunityPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#f8f9f6]">
      <SiteHeader active="/community" />
      <section className="mx-auto grid max-w-[1440px] items-center gap-10 px-6 pb-16 pt-14 md:grid-cols-[1.05fr_.95fr] md:px-12 md:pb-24 md:pt-20">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-[#dce8dc] bg-white/80 px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[.14em] text-[#467356]">Good things find their way</div>
          <h1 className="mt-7 text-5xl font-semibold leading-[1.04] md:text-7xl">The best part is<br/><span className="serif text-[#598467]">all of us.</span></h1>
          <p className="mt-6 max-w-lg text-[15px] leading-7 text-[#718078]">Findly brings neighbors, classmates, and coworkers together around a simple idea: when we look out for one another, lost things find their way home.</p>
          <div className="mt-8 flex flex-wrap gap-3"><Link href="/browse" className="rounded-xl bg-[#274c3b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#1e3d2f]">See the community board <ArrowRight size={15} className="ml-2 inline"/></Link><Link href="/items/report/found/" className="rounded-xl border border-[#e2e8e1] bg-white px-5 py-3.5 text-sm font-semibold text-[#405148] transition hover:bg-[#f3f6f1]">I found something</Link></div>
        </div>
        <div className="relative mx-auto grid h-[330px] w-full max-w-[500px] place-items-center overflow-hidden rounded-[44%_44%_20px_20px] bg-[#dce8db] md:h-[390px]">
          <div className="grain absolute inset-0 opacity-35"/><div className="absolute -left-10 bottom-0 h-[73%] w-[65%] rounded-t-[50%] bg-[#b3c6b3]"/><div className="absolute -right-8 bottom-0 h-[62%] w-[61%] rounded-t-[50%] bg-[#829d85]"/><div className="absolute bottom-0 left-[34%] h-[42%] w-[34%] rounded-t-[48%] bg-[#e7c5a5]"/><div className="relative z-10 -mt-2 grid h-[78px] w-[78px] place-items-center rounded-[26px] border border-white/70 bg-[#f5f6eb] text-[#598467] shadow-xl shadow-[#39543c]/10"><Heart size={34} strokeWidth={1.5}/></div>
          <div className="absolute bottom-5 left-5 rounded-xl border border-white/80 bg-white/95 px-4 py-3 shadow-lg"><p className="text-[11px] font-semibold text-[#2d3d32]">Small act, big relief</p><p className="mt-1 text-[10px] text-[#879187]">A neighbor returned a set of keys</p></div>
        </div>
      </section>
      <section className="mx-auto max-w-[1440px] px-6 pb-20 md:px-12"><div className="max-w-xl"><p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#709078]">What brings us together</p><h2 className="mt-3 text-4xl font-semibold md:text-5xl">Community looks like <span className="serif text-[#598467]">this.</span></h2></div><div className="mt-9 grid gap-3 md:grid-cols-3">{values.map(({icon:Icon,title,text})=><article key={title} className="rounded-2xl border border-[#e8ece5] bg-white p-6"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#eff4eb] text-[#52765b]"><Icon size={18}/></span><h3 className="mt-6 text-lg font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[#7b8780]">{text}</p></article>)}</div></section>
      <section className="mx-6 mb-20 overflow-hidden rounded-2xl bg-[#274c3b] px-7 py-8 text-white md:mx-12 md:px-12 md:py-10"><div className="grain flex flex-wrap items-center justify-between gap-6"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-[#bdd0bc]">Be the reason someone smiles</p><h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">Have you found something?</h2><p className="mt-2 max-w-lg text-sm leading-6 text-[#c1d0c4]">A quick report gives its owner a better chance of finding it.</p></div><Link href="/items/report/found/" className="rounded-xl bg-white px-5 py-3.5 text-sm font-semibold text-[#274c3b] transition hover:bg-[#edf2e9]">Report a found item <ArrowRight size={15} className="ml-2 inline"/></Link></div></section>
      <SiteFooter />
    </main>
  );
}
