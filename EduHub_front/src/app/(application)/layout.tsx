import { Coquille } from '@/components/layout/coquille';

export default function ApplicationLayout({ children }: { children: React.ReactNode }) {
  return <Coquille>{children}</Coquille>;
}
