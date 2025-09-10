import { Outlet } from "react-router-dom"
import { AppSidebar } from "./app-sidebar"
import { Header } from "./header"
import { SidebarProvider } from "@/components/ui/sidebar"

export function MainLayout() {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 p-6 bg-muted/10">
            <Outlet />
          </main>
        </div>
      </div>
    </SidebarProvider>
  )
}