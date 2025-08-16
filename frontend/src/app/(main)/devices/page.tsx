'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Loader2 } from 'lucide-react';

import { API_BASE_URL } from '@/lib/constants';
import { Machine } from '@/lib/types/machine';
import { fetcherClient } from '@/lib/fetcher-client';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';

import PageHeader from './components/page-header';
import DevicesTable from './components/devices-table';

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
        token
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
          <div className="flex items-center justify-center h-32">
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
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
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
          <div className="flex flex-col items-center justify-center h-32 space-y-2">
            <div className="text-destructive">{error}</div>
            <button 
              type="button"
              onClick={refreshMachines}
              className="text-sm text-primary hover:underline"
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
          <div className="flex items-center justify-center h-32">
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
