'use client';

import React, { useMemo, useState } from 'react';
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Filter,
  MapPin,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import 'leaflet/dist/leaflet.css';

import dynamic from 'next/dynamic';

import { DayActivity } from '@/lib/types/activity';
import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

const MapFilter = dynamic(() => import('./map-filter'), {
  ssr: false,
});

interface HeatMapCalendarProps {
  machines: Machine[];
}

interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function HeatMapCalendar({ machines }: HeatMapCalendarProps) {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(
    new Date(),
  );
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [showMapFilter, setShowMapFilter] = useState(false);
  const [areaFilter, setAreaFilter] = useState<MapBounds | null>(null);

  // Filter machines based on selected area
  const filteredMachines = useMemo(() => {
    if (!areaFilter) return machines;

    const filtered = machines.filter(
      (machine) =>
        machine.location.lat >= areaFilter.south &&
        machine.location.lat <= areaFilter.north &&
        machine.location.lng >= areaFilter.west &&
        machine.location.lng <= areaFilter.east,
    );

    console.log('Area filter applied:', {
      totalMachines: machines.length,
      filteredMachines: filtered.length,
      bounds: areaFilter,
    });

    return filtered;
  }, [machines, areaFilter]);

  // Process machine data to create heat map data
  const heatMapData = useMemo(() => {
    const activityMap = new Map<string, DayActivity>();

    filteredMachines.forEach((machine) => {
      // Process suspicious events
      machine.data.suspiciousEvents?.forEach((event) => {
        const date = new Date(event.timestamp);
        const dateKey = date.toDateString();

        if (!activityMap.has(dateKey)) {
          activityMap.set(dateKey, {
            date,
            suspiciousCount: 0,
            healthIssues: 0,
            offlineCount: 0,
            unknownCount: 0,
            intensity: 'none',
            events: [],
          });
        }

        const dayActivity = activityMap.get(dateKey)!;
        dayActivity.suspiciousCount++;
        dayActivity.events.push({
          machineId: machine.id,
          machineName: machine.name,
          type: 'suspicious',
          details: event,
        });
      });

      // Process health events
      machine.data.healthEvents?.forEach((event) => {
        const date = new Date(event.timestamp);
        const dateKey = date.toDateString();

        if (!activityMap.has(dateKey)) {
          activityMap.set(dateKey, {
            date,
            suspiciousCount: 0,
            healthIssues: 0,
            offlineCount: 0,
            unknownCount: 0,
            intensity: 'none',
            events: [],
          });
        }

        const dayActivity = activityMap.get(dateKey)!;
        dayActivity.healthIssues++;
        if (event.type === 'offline') dayActivity.offlineCount++;

        dayActivity.events.push({
          machineId: machine.id,
          machineName: machine.name,
          type: 'health',
          details: event,
        });
      });
    });

    // Calculate intensity for each day
    activityMap.forEach((activity) => {
      const totalEvents = activity.suspiciousCount + activity.healthIssues;
      const hasOffline = activity.offlineCount > 0;
      const hasCriticalHealth = activity.events.some(
        (e) => e.type === 'health' && e.details.severity === 'critical',
      );

      if (hasCriticalHealth || activity.suspiciousCount > 5) {
        activity.intensity = 'critical';
      } else if (totalEvents > 3 || hasOffline) {
        activity.intensity = 'high';
      } else if (totalEvents > 1) {
        activity.intensity = 'medium';
      } else if (totalEvents > 0) {
        activity.intensity = 'low';
      }
    });

    return activityMap;
  }, [filteredMachines]);

  // Get calendar days for current month
  const getCalendarDays = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();

    const firstDay = new Date(year, month, 1);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());

    const days = [];
    const current = new Date(startDate);

    for (let i = 0; i < 42; i++) {
      // 6 weeks × 7 days
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }

    return days;
  };

  const calendarDays = getCalendarDays();
  const selectedDateActivity = selectedDate
    ? heatMapData.get(selectedDate.toDateString())
    : null;

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentMonth((prev) => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + (direction === 'next' ? 1 : -1));
      return newDate;
    });
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === currentMonth.getMonth();
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isSelected = (date: Date) => {
    return selectedDate?.toDateString() === date.toDateString();
  };

  const handleAreaSelect = (bounds: MapBounds | null) => {
    setAreaFilter(bounds);
  };

  return (
    <>
      <div className="relative flex gap-4 overflow-y-auto">
        {/* Calendar */}
        <div className="mb-4 flex-1">
          <Card className="h-fit">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <CardTitle className="text-2xl font-bold">
                    {MONTHS[currentMonth.getMonth()]}{' '}
                    {currentMonth.getFullYear()}
                  </CardTitle>
                  <Button
                    variant={areaFilter ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setShowMapFilter(true)}
                    className="flex items-center gap-2"
                  >
                    <Filter className="h-4 w-4" />
                    {areaFilter
                      ? `Filtered (${filteredMachines.length} machines)`
                      : 'Map Filter'}
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigateMonth('prev')}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigateMonth('next')}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Filter Status Banner */}
              {areaFilter && (
                <div className="mb-4 flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 p-3">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-blue-800">
                      Showing events from {filteredMachines.length} of{' '}
                      {machines.length} machines in selected area
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setAreaFilter(null)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    Clear filter
                  </Button>
                </div>
              )}

              {/* Weekday Headers */}
              <div className="mb-4 grid grid-cols-7 gap-2">
                {WEEKDAYS.map((day) => (
                  <div
                    key={day}
                    className="py-2 text-center text-sm font-medium text-gray-500"
                  >
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar Grid */}
              <div className="grid grid-cols-7 gap-2">
                {calendarDays.map((date, index) => {
                  const activity = heatMapData.get(date.toDateString());

                  return (
                    <Button
                      key={index}
                      onClick={() => setSelectedDate(date)}
                      className={cn(
                        'group text-primary relative flex h-24 w-full flex-col items-start justify-start rounded-lg border-2 border-gray-200 bg-white p-1 text-left transition-all duration-200 hover:bg-gray-50',
                        isSelected(date) &&
                          'ring-2 ring-blue-500 ring-offset-2',
                        !isCurrentMonth(date) && 'opacity-40',
                        isToday(date) && 'ring-1 ring-blue-400',
                      )}
                    >
                      <span
                        className={cn(
                          'font-semibold',
                          !isCurrentMonth(date) && 'text-gray-400',
                          isToday(date) && 'text-blue-600',
                        )}
                      >
                        {date.getDate()}
                      </span>

                      {/* Activity Badges */}
                      {activity && (
                        <div className="mt-1 flex w-full flex-col items-start gap-1">
                          {activity.suspiciousCount > 0 && (
                            <Badge
                              variant="destructive"
                              className="h-auto w-full px-1 py-0.5 text-[10px]"
                            >
                              Suspicious: {activity.suspiciousCount}
                            </Badge>
                          )}
                          {activity.healthIssues > 0 && (
                            <Badge
                              variant="secondary"
                              className="h-auto w-full px-1 py-0.5 text-[10px]"
                            >
                              Health: {activity.healthIssues}
                            </Badge>
                          )}
                        </div>
                      )}

                      {/* Filter indicator */}
                      {areaFilter && !activity && isCurrentMonth(date) && (
                        <div className="absolute right-1 bottom-1">
                          <div
                            className="h-1.5 w-1.5 rounded-full bg-blue-400"
                            title="Area filter active"
                          />
                        </div>
                      )}
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Details Panel */}
        <div className="sticky top-0 mb-4 h-fit w-96 space-y-4">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Activity className="h-6 w-6" />
                {selectedDate
                  ? selectedDate.toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })
                  : 'Select a Date'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedDateActivity ? (
                <div className="space-y-6">
                  {/* Filter Status in Details */}
                  {areaFilter && (
                    <div className="flex items-center gap-1 rounded border border-blue-200 bg-blue-50 p-2 text-xs text-blue-800">
                      <Filter className="h-3 w-3" />
                      <span>
                        Filtered view - showing events from selected area only
                      </span>
                    </div>
                  )}

                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
                      <div className="text-3xl font-bold text-red-600">
                        {selectedDateActivity.suspiciousCount}
                      </div>
                      <div className="text-sm font-medium text-red-500">
                        Suspicious Events
                      </div>
                    </div>
                    <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-center">
                      <div className="text-3xl font-bold text-orange-600">
                        {selectedDateActivity.healthIssues}
                      </div>
                      <div className="text-sm font-medium text-orange-500">
                        Health Issues
                      </div>
                    </div>
                  </div>

                  {/* Event Details */}
                  <div className="max-h-80 space-y-3 overflow-y-auto">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold">Event Timeline</h4>
                      {areaFilter && (
                        <span className="text-xs text-gray-500">
                          {selectedDateActivity.events.length} events
                        </span>
                      )}
                    </div>
                    {selectedDateActivity.events
                      .sort(
                        (a, b) =>
                          new Date(b.details.timestamp).getTime() -
                          new Date(a.details.timestamp).getTime(),
                      )
                      .map((event, index) => (
                        <div
                          key={index}
                          className="rounded-lg border p-3 transition-colors hover:bg-gray-50"
                        >
                          <div className="mb-2 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <MapPin className="h-4 w-4 text-gray-500" />
                              <span className="text-sm font-medium">
                                {event.machineName}
                              </span>
                            </div>
                            <Badge
                              variant={
                                event.type === 'suspicious'
                                  ? 'destructive'
                                  : 'secondary'
                              }
                              className="text-xs"
                            >
                              {event.type}
                            </Badge>
                          </div>

                          {event.type === 'suspicious' && (
                            <div className="space-y-1 text-xs text-gray-600">
                              <div>
                                Type:{' '}
                                <span className="font-medium">
                                  {event.details.type.replace(/_/g, ' ')}
                                </span>
                              </div>
                              <div>
                                Confidence:{' '}
                                <span className="font-medium">
                                  {(event.details.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div>
                                Time:{' '}
                                <span className="font-medium">
                                  {new Date(
                                    event.details.timestamp,
                                  ).toLocaleTimeString()}
                                </span>
                              </div>
                              {event.details.marked && (
                                <Badge variant="outline" className="mt-2">
                                  {event.details.marked}
                                </Badge>
                              )}
                            </div>
                          )}

                          {event.type === 'health' && (
                            <div className="space-y-1 text-xs text-gray-600">
                              <div>
                                Issue:{' '}
                                <span className="font-medium">
                                  {event.details.type.replace(/_/g, ' ')}
                                </span>
                              </div>
                              <div>
                                Time:{' '}
                                <span className="font-medium">
                                  {new Date(
                                    event.details.timestamp,
                                  ).toLocaleTimeString()}
                                </span>
                              </div>
                              <Badge
                                variant={
                                  event.details.severity === 'critical'
                                    ? 'destructive'
                                    : 'secondary'
                                }
                                className="mt-2"
                              >
                                {event.details.severity}
                              </Badge>
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
                  <p className="text-lg font-medium">No activity recorded</p>
                  <p className="text-sm">
                    {areaFilter
                      ? 'No events found in the selected area for this date'
                      : 'Select a date to view events'}
                  </p>
                  {areaFilter && machines.length > filteredMachines.length && (
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => setAreaFilter(null)}
                      className="mt-2 text-blue-600"
                    >
                      Clear area filter to see all events
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Map Filter Modal */}
      {showMapFilter && (
        <MapFilter
          machines={machines}
          onAreaSelect={handleAreaSelect}
          onClose={() => setShowMapFilter(false)}
          selectedBounds={areaFilter}
        />
      )}
    </>
  );
}
