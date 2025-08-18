import React from 'react';
import { SidebarTrigger } from '@/components/ui/sidebar';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';

import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';

import EventsFeed from './components/events-feed';
import { Machine } from '@/lib/types/machine';


interface MachinesResponse {
  status: string;
  data: Machine[];
}

// Page Header Component
function PageHeader() {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-1">
          <SidebarTrigger className="hover:bg-accent-foreground/10 h-8 w-8 rounded-md hover:cursor-pointer" />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="/">Home</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink href="/dashboard">Dashboard</BreadcrumbLink>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </div>
    </div>
  );
}

// Main Dashboard Page
export default async function DashboardPage() {
  // Fetch organization data
  const { organization_uid, organization_id } = await getOrg();

  // Fetch machines data on server-side
  const machinesResponse = await fetcher<MachinesResponse>(
    `${API_BASE_URL}/machines?organization_uid=${organization_uid}`
  );

  const machines = machinesResponse?.data ?? [];

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-y-auto rounded-lg border">
        <EventsFeed 
          machines={machines} 
          organizationId={organization_id}
          organizationUid={organization_uid}
        />
      </div>
    </section>
  );
}