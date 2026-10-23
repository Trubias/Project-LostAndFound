import { Bell, Boxes, FileText, FolderKanban, KeyRound, LayoutDashboard, UserRound } from 'lucide-react';
import type { WorkspaceLink } from '@/components/workspace-frame';

export const userNavigation: WorkspaceLink[] = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/items/my-reports', label: 'My reports', icon: FolderKanban },
  { href: '/claims/my', label: 'My claims', icon: FileText },
  { href: '/matches', label: 'Possible matches', icon: Boxes },
  { href: '/notifications', label: 'Notifications', icon: Bell },
  { href: '/profile', label: 'My profile', icon: UserRound },
  { href: '/password-change', label: 'Change password', icon: KeyRound },
];
