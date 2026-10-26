import { Activity, Bell, Boxes, CalendarCheck, ChartNoAxesCombined, FileText, Flag, FlaskConical, FolderKanban, LayoutDashboard, MapPinned, Search, Users } from 'lucide-react';
import type { WorkspaceLink } from '@/components/workspace-frame';

export const adminNavigation: WorkspaceLink[] = [
  { href: '/admin-dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/admin-dashboard/users', label: 'Users', icon: Users },
  { href: '/admin-dashboard/items', label: 'Items', icon: Boxes },
  { href: '/admin-dashboard/claims', label: 'Claims', icon: FileText },
  { href: '/admin-dashboard/handoffs', label: 'Handoffs', icon: CalendarCheck },
  { href: '/admin-dashboard/activity', label: 'Activity log', icon: Activity },
  { href: '/admin-dashboard/flags', label: 'Community reports', icon: Flag },
  { href: '/admin-dashboard/categories', label: 'Categories', icon: FolderKanban },
  { href: '/admin-dashboard/locations', label: 'Locations & fields', icon: MapPinned },
  { href: '/admin-dashboard/matches', label: 'Matches', icon: Search },
  { href: '/admin-dashboard/notifications', label: 'Notifications', icon: Bell },
  { href: '/admin-dashboard/api-tests', label: 'API tests', icon: FlaskConical },
  { href: '/reports', label: 'Reports', icon: ChartNoAxesCombined },
];
