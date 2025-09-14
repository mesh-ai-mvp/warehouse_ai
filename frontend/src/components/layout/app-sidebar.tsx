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
        <div className="flex items-center justify-between gap-2 px-3 py-3">
          <div className="flex items-center gap-2">
            <img
              src="/@new-logo.png"
              onError={(e) => { e.currentTarget.src = '/logo.png' }}
              alt="Suppl.AI"
              className="h-7 w-auto"
            />
            <div className="group-data-[collapsible=icon]:hidden">
              <h2 className="text-base font-semibold text-sidebar-foreground">Suppl.AI</h2>
            </div>
          </div>
          <SidebarTrigger className="h-8 w-8" />
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
