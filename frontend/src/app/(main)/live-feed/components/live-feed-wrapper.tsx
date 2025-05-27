'use client';

import 'leaflet/dist/leaflet.css';

import React, { useMemo, useState } from 'react';
import { Calendar, RefreshCw, Shield } from 'lucide-react';
import dynamic from 'next/dynamic';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

import MachineDetailModal from './machine-detail-model';

interface LiveFeedWrapperProps {
  machines: Machine[];
  selectedDate?: Date;
}

const ReactLeafletMap = dynamic(() => import('./react-leaflet-map'), {
  ssr: false,
});

export default function LiveFeedWrapper({
  machines,
  selectedDate,
}: LiveFeedWrapperProps) {
  const [selectedMachine, setSelectedMachine] = useState<Machine | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [activityFilter, setActivityFilter] = useState<string>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Filter machines based on selected filters
  const filteredMachines = useMemo(() => {
    return machines.filter((machine) => {
      if (statusFilter !== 'all' && machine.data.status !== statusFilter) {
        return false;
      }

      if (activityFilter !== 'all') {
        const recentEvents =
          machine.data.suspiciousEvents?.filter((event) => {
            const eventDate = new Date(event.timestamp);
            const daysDiff =
              (Date.now() - eventDate.getTime()) / (1000 * 60 * 60 * 24);
            return daysDiff <= 7; // Last 7 days
          }) || [];

        if (activityFilter === 'high' && recentEvents.length < 3) return false;
        if (
          activityFilter === 'medium' &&
          (recentEvents.length === 0 || recentEvents.length > 5)
        )
          return false;
        if (activityFilter === 'low' && recentEvents.length > 2) return false;
      }

      return true;
    });
  }, [machines, statusFilter, activityFilter]);

  // Get unreviewed events count
  const getUnreviewedCount = (machine: Machine) => {
    return (
      machine.data.suspiciousEvents?.filter(
        (event) => event.marked === 'unreviewed' || !event.marked,
      ).length || 0
    );
  };

  // Mock refresh function
  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1500);
  };

  const onlineCount = machines.filter((m) => m.data.status === 'online').length;
  const offlineCount = machines.filter(
    (m) => m.data.status === 'offline',
  ).length;
  const maintenanceCount = machines.filter(
    (m) => m.data.status === 'maintenance',
  ).length;
  const totalAlerts = machines.reduce(
    (sum, m) => sum + getUnreviewedCount(m),
    0,
  );

  return (
    <div className="flex h-full w-full flex-col">
      {/* Enhanced Map Controls */}
      <div className="flex items-center justify-between border-b bg-white p-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <span className="font-semibold">Network Overview</span>
          </div>

          {/* Quick Stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span>{onlineCount} Online</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-red-500"></div>
              <span>{offlineCount} Offline</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
              <span>{maintenanceCount} Maintenance</span>
            </div>
            {totalAlerts > 0 && (
              <Badge variant="destructive" className="text-xs">
                {totalAlerts} Alert{totalAlerts > 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Date Filter */}
          {selectedDate && (
            <div className="flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-sm">
              <Calendar className="h-4 w-4 text-blue-600" />
              <span>{selectedDate.toLocaleDateString()}</span>
            </div>
          )}

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent className="z-[1000]">
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="online">Online</SelectItem>
              <SelectItem value="offline">Offline</SelectItem>
              <SelectItem value="maintenance">Maintenance</SelectItem>
            </SelectContent>
          </Select>

          {/* Activity Filter */}
          <Select value={activityFilter} onValueChange={setActivityFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="All Activity" />
            </SelectTrigger>
            <SelectContent className="z-[1000]">
              <SelectItem value="all">All Activity</SelectItem>
              <SelectItem value="high">High Activity</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low Activity</SelectItem>
            </SelectContent>
          </Select>

          {/* Refresh Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Map Container */}
      <div className="relative flex-1 overflow-hidden">
        <ReactLeafletMap
          machines={filteredMachines}
          onMarkerClick={setSelectedMachine}
          selectedDate={selectedDate}
        />

        {/* Filtered Results Indicator */}
        {filteredMachines.length !== machines.length && (
          <div className="absolute top-4 right-4 rounded-lg border bg-white px-3 py-2 shadow-lg">
            <div className="text-sm font-medium">
              Showing {filteredMachines.length} of {machines.length} machines
            </div>
            {(statusFilter !== 'all' || activityFilter !== 'all') && (
              <button
                onClick={() => {
                  setStatusFilter('all');
                  setActivityFilter('all');
                }}
                className="mt-1 text-xs text-blue-600 hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Enhanced Machine Detail Modal */}
      <MachineDetailModal
        selectedMachine={selectedMachine}
        setSelectedMachine={setSelectedMachine}
      />
    </div>
  );
}
