import { redirect } from 'next/navigation';
import { ApiTestDashboard } from '@/features/admin/api-tests';
import { AdminWorkspaceShell } from '@/features/admin/workspace-shell';
import { getDjangoSession } from '@/lib/django-session';

export default async function ApiTestsPage() {
  const session = await getDjangoSession();
  if (!session.authenticated) redirect('/login');
  if (!session.isAdmin) redirect('/dashboard');
  return <AdminWorkspaceShell activePath="/admin-dashboard/api-tests" userName={session.name} avatar={session.avatar}>
    <section className="w-full px-6 pb-20 pt-8 md:px-10 md:pt-10">
      <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.16em] text-[#709078]">Findly administration</p>
      <h1 className="mt-3 text-4xl font-semibold md:text-5xl">API test console</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-[#718078]">Discover Django API routes, probe HTTP methods, and review request/response history in an isolated test environment.</p>
      <ApiTestDashboard />
    </section>
  </AdminWorkspaceShell>;
}
