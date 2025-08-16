'use client';

import React, { useCallback, useEffect, useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import { Loader2 } from 'lucide-react';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';

import DevicesTable from './components/devices-table';
import PageHeader from './components/page-header';

export default function DevicesPage() {
  const { token } = useToken();
  const { organizationUid } = useOrganization();

  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMachines = useCallback(async () => {
    if (!organizationUid || !token) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetcherClient<{ data: Machine[] }>(
        `${API_BASE_URL}/machines?organization_uid=${organizationUid}`,
        token,
      );

      if (response?.data) {
        setMachines(response.data);
      } else {
        setMachines([]);
      }
    } catch (error) {
      console.error('Failed to load machines:', error);
      setError('Failed to load machines. Please try again.');
      setMachines([]);
    } finally {
      setLoading(false);
    }
  }, [organizationUid, token]);

  useEffect(() => {
    loadMachines();
  }, [loadMachines]);

  const refreshMachines = async () => {
    await loadMachines();
  };

  if (!organizationUid || !token) {
    return (
      <section className="flex h-full w-full flex-col gap-4 p-4">
        <PageHeader />
        <div className="bg-background h-full w-full overflow-y-auto rounded-lg border p-6">
          <div className="flex h-32 items-center justify-center">
            <div className="text-muted-foreground">Loading...</div>
          </div>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="flex h-full w-full flex-col gap-4 p-4">
        <PageHeader />
        <div className="bg-background h-full w-full overflow-y-auto rounded-lg border p-6">
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="mr-2 h-6 w-6 animate-spin" />
            <div className="text-muted-foreground">Loading machines...</div>
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="flex h-full w-full flex-col gap-4 p-4">
        <PageHeader />
        <div className="bg-background h-full w-full overflow-y-auto rounded-lg border p-6">
          <div className="flex h-32 flex-col items-center justify-center space-y-2">
            <div className="text-destructive">{error}</div>
            <button
              type="button"
              onClick={refreshMachines}
              className="text-primary text-sm hover:underline"
            >
              Try again
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-y-auto rounded-lg border p-6">
        {machines.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <div className="text-muted-foreground">No machines found.</div>
          </div>
        ) : (
          <DevicesTable
            machines={machines}
            onRefreshMachines={refreshMachines}
          />
        )}
      </div>
    </section>
  );
}
