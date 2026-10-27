import BackendPage, { type BackendPageProps } from '@/components/backend-page';

export default function AdminModulePage(props: BackendPageProps) {
  return <BackendPage {...props} pathPrefix="/admin-dashboard"/>;
}
