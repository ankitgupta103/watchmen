'use client';

import useOrganization from '@/hooks/use-organization';
import useUser from '@/hooks/use-user';
import {
  Calendar,
  CameraIcon,
  ChevronDown,
  HomeIcon,
  LogOut,
  NetworkIcon,
  User,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
  useSidebar,
} from '@/components/ui/sidebar';

import { setCookie } from '@/lib/cookies';
import { Organization } from '@/lib/types/organization';
import { cn } from '@/lib/utils';

import { Logo } from '../logo';

const items = [
  {
    title: 'Dashboard',
    url: '/dashboard',
    icon: HomeIcon,
  },
  {
    title: 'Live Feed',
    url: '/live-feed',
    icon: CameraIcon,
  },
  {
    title: 'Calendar',
    url: '/calendar',
    icon: Calendar,
  },
  {
    title: 'Network Simulation',
    url: '/network-simulation',
    icon: NetworkIcon,
  },
];

export default function AppSidebar() {
  const router = useRouter();
  const { open } = useSidebar();
  const pathname = usePathname();
  const { user, organizations } = useUser();
  const { organization: currentOrg } = useOrganization();

  const handleOrganizationChange = (org: Organization) => {
    setCookie('organization', JSON.stringify(org));
    router.push('/dashboard');
  };

  return (
    <Sidebar collapsible="icon" className="group relative">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              tooltip="Vyom OS Netrajaal"
              className="h-12"
            >
              <Logo showText={open} />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarSeparator className="group-data-[collapsed=true]:hidden" />

        <SidebarMenu className="group-data-[collapsed=true]:hidden">
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg">
                  <div className="bg-sidebar-primary aspect-square size-8 rounded-lg text-gray-800">
                    <Avatar className="h-8 w-8">
                      <AvatarImage
                        src={
                          currentOrg?.organization_logo || '/placeholder.svg'
                        } // Use a placeholder if organization_logo fails
                        alt={currentOrg?.organization_name}
                      />
                      <AvatarFallback>
                        {currentOrg?.organization_name?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  </div>
                  {/* Text within the button - this part is already hidden by hiding the parent SidebarMenu */}
                  <div className="flex flex-col gap-0.5 leading-none">
                    <span className="font-semibold">
                      {currentOrg?.organization_name}
                    </span>
                    <span className="text-muted-foreground text-xs">
                      Organization
                    </span>
                  </div>
                  <ChevronDown className="ml-auto size-4 opacity-50" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="start"
                className="w-[--radix-popper-anchor-width]"
              >
                <DropdownMenuLabel>Organizations</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {organizations?.map((org) => (
                  <DropdownMenuItem
                    key={org.organization_id}
                    onClick={() => {
                      handleOrganizationChange(org);
                    }}
                  >
                    <Avatar className="mr-2 h-6 w-6">
                      <AvatarImage
                        src={org?.organization_logo || '/placeholder.svg'}
                        alt={org?.organization_name}
                      />
                      <AvatarFallback>
                        {org?.organization_name?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <span>{org?.organization_name}</span>
                    {org.organization_id === currentOrg?.organization_id && (
                      <span className="ml-auto flex h-4 w-4 items-center justify-center">
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="size-4"
                        >
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </span>
                    )}
                  </DropdownMenuItem>
                ))}
                {/* Optional: Create Organization Item */}
                {/* <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <Building className="mr-2 size-4" />
                  <span>Create Organization</span>
                </DropdownMenuItem> */}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarSeparator className="group-data-[collapsed=true]:hidden" />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Main</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    className={cn({
                      'bg-sidebar-primary/10': pathname.includes(item.url),
                    })}
                  >
                    <a href={item.url}>
                      <item.icon className="size-5" /> <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarSeparator className="group-data-[collapsed=true]:hidden" />

        <SidebarMenu className="group-data-[collapsed=true]:hidden">
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg">
                  <div className="bg-sidebar-primary aspect-square size-8 rounded-lg text-gray-800">
                    <Avatar className="h-8 w-8">
                      <AvatarImage
                        src={`https://avatar.iran.liara.run/username?username=${user?.name}`} // Use a placeholder for now
                        alt={user?.name}
                      />
                      <AvatarFallback>{user?.name?.charAt(0)}</AvatarFallback>
                    </Avatar>
                  </div>
                  <div className="flex flex-col gap-0.5 leading-none">
                    <span className="font-semibold">{user?.name}</span>
                    <span className="text-muted-foreground text-xs">User</span>
                  </div>
                  <ChevronDown className="ml-auto size-4 opacity-50" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="start"
                className="w-[--radix-popper-anchor-width]"
              >
                <DropdownMenuItem>
                  <User className="mr-2 size-4" />
                  <a href="/user/profile">Profile</a>
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                <DropdownMenuItem>
                  <LogOut className="mr-2 size-4" />
                  <a href="/auth/logout">Logout</a>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
