import { WorkspaceFrame } from '@/components/workspace-frame';
import { adminNavigation } from './navigation';
import { AdminRecordDrawerProvider } from './record-drawer';

export function AdminWorkspaceShell({ activePath, userName, avatar, children }: { activePath: string; userName?: string; avatar?: string | null; children: React.ReactNode }) {
  return <AdminRecordDrawerProvider><WorkspaceFrame role="admin" activePath={activePath} userName={userName} avatar={avatar} nav={adminNavigation}>{children}</WorkspaceFrame></AdminRecordDrawerProvider>;
}
