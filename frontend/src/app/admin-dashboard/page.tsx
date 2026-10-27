import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { AdminOverview, type ReportTrends } from '@/features/admin/overview';
import { AdminWorkspaceShell } from '@/features/admin/workspace-shell';
import { getDjangoSession } from '@/lib/django-session';

type DashboardData = {
  title: string;
  summary: string;
  trends?: ReportTrends;
};

export default async function AdminDashboardPage() {
  const session = await getDjangoSession();
  if (!session.authenticated) redirect('/login');
  if (!session.isAdmin) redirect('/dashboard');

  const backend = process.env.DJANGO_URL ?? 'http://127.0.0.1:8000';
  let dashboard: DashboardData | null = null;
  try {
    const cookieHeader = (await cookies()).toString();
    const query = new URLSearchParams({ path: '/admin-dashboard' });
    const response = await fetch(`${backend}/api/frontend-page/?${query}`, {
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
      cache: 'no-store',
    });
    if (response.ok) dashboard = await response.json() as DashboardData;
  } catch {
    dashboard = null;
  }

  return <AdminWorkspaceShell activePath="/admin-dashboard" userName={session.name} avatar={session.avatar}>
    <section className="w-full px-6 pb-20 pt-8 md:px-10 md:pt-10">
      <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.16em] text-[#709078]">Workspace</p>
      <h1 className="mt-3 text-4xl font-semibold md:text-5xl">{dashboard?.title ?? 'Admin overview'}</h1>
      {dashboard ? <>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[#718078]">{dashboard.summary}</p>
        <AdminOverview trends={dashboard.trends ?? { '7d': [], '30d': [], '6m': [], '1y': [] }}/>
      </> : <p role="alert" className="mt-4 text-sm text-[#9b5145]">The admin dashboard could not be loaded. Please try again.</p>}
    </section>
  </AdminWorkspaceShell>;
}
