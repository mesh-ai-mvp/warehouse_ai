import { BarChart3, Package, ShoppingCart, FileText, Home, Settings, Warehouse } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarTrigger,
} from '@/components/ui/sidebar'

const menuItems = [
  {
    title: 'Dashboard',
    url: '/',
    icon: Home,
  },
  {
    title: 'Inventory',
    url: '/inventory',
    icon: Package,
  },
  {
    title: 'Purchase Orders',
    url: '/purchase-orders',
    icon: ShoppingCart,
  },
  {
    title: 'Create PO',
    url: '/create-po',
    icon: FileText,
  },
  {
    title: 'Analytics',
    url: '/analytics',
    icon: BarChart3,
  },
  {
    title: 'Reports',
    url: '/reports',
    icon: FileText,
  },
  {
    title: 'Warehouse UI',
    url: '/warehouse-ui',
    icon: Warehouse,
  },
  {
    title: 'Settings',
    url: '/settings',
    icon: Settings,
  },
]

export function AppSidebar() {
  const location = useLocation()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="h-16 w-full flex items-center justify-between px-3">
          <div className="brand-font text-2xl font-semibold tracking-wide text-sidebar-foreground group-data-[collapsible=icon]:hidden">
            Suppl.AI
          </div>
          <SidebarTrigger className="h-6 w-6 bg-white/80 hover:bg-white rounded shadow-sm dark:bg-black/30 dark:hover:bg-black/40" />
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map(item => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={location.pathname === item.url}>
                    <Link to={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}