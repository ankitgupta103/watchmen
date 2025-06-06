import AppSidebar from '@/components/common/app-sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <div className="h-screen w-full overflow-y-auto">{children}</div>
    </SidebarProvider>
  );
}
