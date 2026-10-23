import { WorkspaceFrame } from '@/components/workspace-frame';
import { userNavigation } from './navigation';

export function UserWorkspaceShell({ activePath, userName, avatar, children }: { activePath: string; userName?: string; avatar?: string | null; children: React.ReactNode }) {
  return <WorkspaceFrame role="user" activePath={activePath} userName={userName} avatar={avatar} nav={userNavigation}>{children}</WorkspaceFrame>;
}
