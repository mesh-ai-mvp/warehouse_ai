import { Outlet } from 'react-router-dom'
import { AppSidebar } from './app-sidebar'
import { Header } from './header'
import { SidebarProvider, SidebarInset, SidebarRail } from '@/components/ui/sidebar'

export function MainLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarRail />
      <SidebarInset>
        <Header />
        <div className="flex-1 p-6 bg-muted/10">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
