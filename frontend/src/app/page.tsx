import Link from 'next/link';
import {
  ArrowRight,
  ArrowUpRight,
  Box,
  Check,
  Heart,
  LockKeyhole,
  MapPin,
  PackageCheck,
  Search,
} from 'lucide-react';
import { SiteFooter, SiteHeader } from '@/components/site-header';

const steps = [
  {
    number: '01',
    icon: Search,
    title: 'Search the board',
    text: 'Browse recent reports by item, category, and place. You can look around before signing in.',
  },
  {
    number: '02',
    icon: Box,
    title: 'Share the useful details',
    text: 'Report what went missing or what you found. A color, marking, or nearby landmark can help.',
  },
  {
    number: '03',
    icon: Heart,
    title: 'Reconnect safely',
    text: 'Use a claim to describe proof of ownership. Keep identifying details for the private claim conversation.',
  },
];

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#f8f9f6]">
      <SiteHeader showNavigation />

      <section className="relative mx-auto grid max-w-[1440px] items-center gap-8 px-6 pb-14 pt-11 md:grid-cols-[1.04fr_.96fr] md:px-12 md:pb-20 md:pt-14">
        <div className="relative z-10 max-w-[610px]">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#dce8dc] bg-white/80 px-3.5 py-2 text-[11px] font-semibold uppercase tracking-[.13em] text-[#467356]">
            A little kindness goes a long way
          </div>
          <h1 className="text-[clamp(3.8rem,7.9vw,7.5rem)] font-semibold leading-[.94]">
            Lost<br />things.<br /><span className="serif text-[#598467]">Found<br />people.</span>
          </h1>
          <p className="mt-7 max-w-[435px] text-[16px] leading-[1.8] text-[#718078]">
            A missing jacket, a found set of keys, a familiar face. We help the little things make their way back home.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link href="/browse" className="rounded-xl bg-[#274c3b] px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-[#274c3b]/15 transition hover:-translate-y-0.5 hover:bg-[#1e3d2f]">
              Find something <ArrowRight size={16} className="ml-2 inline" />
            </Link>
            <Link href="/items/report/found/" className="rounded-xl border border-[#e2e8e1] bg-white px-5 py-3.5 text-sm font-semibold text-[#405148] transition hover:bg-[#f3f6f1]">
              I found something
            </Link>
          </div>
          <div className="mt-11 flex items-center gap-3">
            <div className="flex -space-x-2" aria-hidden="true">
              {['#e9bd9b', '#b7c5a3', '#d9a895', '#d3c59d'].map((color, index) => (
                <div key={color} style={{ background: color }} className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#f8f9f6] text-[10px] font-bold text-white">
                  {['J', 'A', 'M', 'S'][index]}
                </div>
              ))}
            </div>
            <p className="text-xs text-[#8b968e]"><span className="font-bold text-[#43564a]">A community that cares</span><br />Little acts. Real connections.</p>
          </div>
        </div>

        <div className="relative mx-auto h-[470px] w-full max-w-[630px] md:h-[555px]" aria-label="A neighbor returning a found bag">
          <div className="absolute right-1 top-2 h-[87%] w-[86%] overflow-hidden rounded-[48%_48%_20px_20px] bg-[#dce8db]">
            <div className="grain absolute inset-0 opacity-40" />
            <div className="absolute -right-12 top-10 h-64 w-64 rounded-full bg-[#cadac9]" />
            <div className="absolute -left-8 bottom-0 h-[72%] w-[67%] rounded-t-[46%] bg-[#b3c6b3]" />
            <div className="absolute bottom-0 right-0 h-[58%] w-[52%] rounded-t-[48%] bg-[#829d85]" />
            <div className="absolute bottom-0 left-[29%] h-[36%] w-[38%] rounded-t-[45%] bg-[#e7c5a5]" />
            <div className="absolute bottom-0 left-[28%] h-[12%] w-[40%] rounded-t-[50%] bg-[#d4a884]" />
            <div className="absolute bottom-[21%] left-[39%] h-[34%] w-[21%] rotate-[-8deg] rounded-[45%_45%_16px_16px] bg-[#dbe6cb] shadow-xl" />
            <div className="absolute bottom-[12%] left-[43%] h-28 w-16 rotate-[-8deg] rounded-xl border border-[#c5d2b4] bg-[#f0f1e5]" />
          </div>
          <div className="absolute bottom-4 left-0 rounded-2xl border border-white/80 bg-white/95 p-4 shadow-[0_16px_50px_rgba(32,52,39,.12)] backdrop-blur-sm md:left-1">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#eef3e9] text-[#5b785e]"><Check size={18} /></div>
              <div><p className="text-xs font-semibold text-[#2d3d32]">A little reunion</p><p className="mt-0.5 text-[10px] text-[#879187]">A tote found near the library</p></div>
              <span className="ml-3 rounded-full bg-[#edf5e9] px-2 py-1 text-[9px] font-bold text-[#628261]">TOGETHER</span>
            </div>
          </div>
          <div className="absolute right-0 top-[22%] rotate-3 rounded-2xl border border-white/90 bg-white/95 px-4 py-3 shadow-[0_14px_44px_rgba(32,52,39,.12)]">
            <div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg bg-[#eff4eb] text-[#698365]"><Heart size={14} /></span><div><p className="text-[11px] font-bold">A helpful detail</p><p className="text-[9px] text-[#8c968e]">The blue umbrella</p></div></div>
          </div>
          <span className="absolute left-[7%] top-[17%] h-2 w-2 rounded-full bg-[#a1bc91]" />
          <span className="absolute right-[9%] bottom-[20%] h-3 w-3 rounded-full border-2 border-[#95b58a]" />
          <span className="absolute left-[22%] top-[51%] h-1.5 w-1.5 rounded-full bg-[#c8a488]" />
        </div>
      </section>

      <section aria-labelledby="start-here" className="mx-6 mb-24 rounded-[28px] border border-[#e5ebe2] bg-[#eef2eb] p-5 md:mx-12 md:p-9 lg:p-11">
        <div className="mx-auto max-w-7xl">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#709078]">A good place to begin</p>
              <h2 id="start-here" className="mt-2 text-3xl font-semibold md:text-4xl">What brings you here?</h2>
            </div>
            <p className="max-w-sm text-sm leading-6 text-[#718078]">Browse reports freely. Sign in when you are ready to report an item or make a claim.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Link href="/browse?type=FOUND" className="group flex min-h-52 flex-col justify-between rounded-2xl border border-white bg-white p-6 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-[#274c3b]/[.07] md:p-8">
              <div className="flex items-start justify-between"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#eef3e9] text-[#52765b]"><Search size={21} /></span><ArrowUpRight size={19} className="text-[#8b968e] transition group-hover:text-[#426e51]" /></div>
              <div><h3 className="text-xl font-semibold">I lost something</h3><p className="mt-2 max-w-md text-sm leading-6 text-[#7b8780]">Look through found items and check the details people have shared.</p><span className="mt-4 inline-flex items-center text-sm font-semibold text-[#426e51]">Browse found items <ArrowRight size={15} className="ml-2" /></span></div>
            </Link>
            <Link href="/items/report/found/" className="group flex min-h-52 flex-col justify-between rounded-2xl bg-[#274c3b] p-6 text-white transition hover:-translate-y-1 hover:bg-[#1e3d2f] hover:shadow-xl hover:shadow-[#274c3b]/15 md:p-8">
              <div className="flex items-start justify-between"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-white/10 text-[#dcefcd]"><PackageCheck size={21} /></span><ArrowUpRight size={19} className="text-[#b8cbb9] transition group-hover:text-white" /></div>
              <div><h3 className="text-xl font-semibold">I found something</h3><p className="mt-2 max-w-md text-sm leading-6 text-[#d0ded1]">Share where it was found so its owner has a better chance of spotting it.</p><span className="mt-4 inline-flex items-center text-sm font-semibold text-[#dcefcd]">Report a found item <ArrowRight size={15} className="ml-2" /></span></div>
            </Link>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white/65 px-5 py-4">
            <p className="text-sm text-[#718078]">Didn’t find what you’re looking for?</p>
            <Link href="/items/report/lost/" className="inline-flex items-center text-sm font-semibold text-[#426e51] hover:underline">Report a lost item <ArrowRight size={15} className="ml-2" /></Link>
          </div>
          <p className="mt-5 flex items-center gap-2 text-xs text-[#748078]"><LockKeyhole size={14} className="text-[#628261]" /> Keep unique proof details for your claim, not the public report.</p>
        </div>
      </section>

      <section className="mx-auto max-w-[1440px] px-6 pb-24 md:px-12">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div><p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#709078]">From report to reunion</p><h2 className="mt-3 text-4xl font-semibold md:text-5xl">A little care goes <span className="serif text-[#598467]">a long way.</span></h2></div>
          <Link href="/how-it-works" className="text-sm font-semibold text-[#55705d]">See how it works <ArrowRight size={15} className="ml-2 inline" /></Link>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {steps.map(({ number, icon: Icon, title, text }) => (
            <article key={number} className="rounded-2xl border border-[#e8ece5] bg-white p-6 transition hover:-translate-y-1 hover:shadow-lg hover:shadow-[#274c3b]/[.05] md:p-7">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold tracking-[.14em] text-[#8c9a8d]">STEP {number}</span><span className="grid h-11 w-11 place-items-center rounded-xl bg-[#eff4eb] text-[#52765b]"><Icon size={19} /></span></div>
              <h3 className="mt-7 text-xl font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[#7b8780]">{text}</p>
            </article>
          ))}
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
