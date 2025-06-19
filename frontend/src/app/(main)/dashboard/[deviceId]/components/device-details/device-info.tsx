'use client';

import React from 'react';
import { Calendar, MapPin, Server, Wifi, WifiOff } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { Machine } from '@/lib/types/machine';
import { formatBufferSize } from '@/lib/utils';

const DeviceInfo = ({
  device,
  machineStats,
  buffer,
}: {
  device: Machine;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  machineStats: any;
  buffer: number;
}) => (
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center gap-2">
        <Server className="h-6 w-6" />
        Device Information
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <div>
            <h1 className="mb-2 text-3xl font-bold">
              {device.name.replace(/-/g, ' ')}
            </h1>
            <div className="mb-4 flex flex-wrap gap-2">
              <Badge
                variant={machineStats !== null ? 'default' : 'destructive'}
                className="flex items-center gap-1 capitalize"
              >
                {machineStats !== null ? (
                  <Wifi className="h-3 w-3" />
                ) : (
                  <WifiOff className="h-3 w-3" />
                )}
                {machineStats !== null ? 'Online' : 'Offline'}
              </Badge>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-semibold text-gray-600">Machine UID:</span>
              <p className="font-mono">{device.machine_uid}</p>
            </div>
            <div>
              <span className="font-semibold text-gray-600">Model UID:</span>
              <p className="font-mono">{device.model_uid}</p>
            </div>
            <div>
              <span className="font-semibold text-gray-600">Owner:</span>
              <p>{device.current_owner_name}</p>
            </div>
            <div>
              <span className="font-semibold text-gray-600">Buffer:</span>
              <p>{formatBufferSize(buffer)}</p>
            </div>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="mb-2 flex items-center gap-2 font-semibold text-gray-600">
              <Calendar className="h-4 w-4" />
              Important Dates
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Manufacturing:</span>
                <span>{new Date(device.mfg_date).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Activation:</span>
                <span>
                  {new Date(device.activation_date).toLocaleDateString()}
                </span>
              </div>
              {device.end_of_service_date && (
                <div className="flex justify-between">
                  <span>End of Service:</span>
                  <span>
                    {new Date(device.end_of_service_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div>
            <h3 className="mb-2 flex items-center gap-2 font-semibold text-gray-600">
              <MapPin className="h-4 w-4" />
              Location
            </h3>
            <div className="space-y-1 text-sm">
              <div>
                <span className="font-medium">Real-time:</span>{' '}
                {machineStats?.message?.location?.lat ??
                  device?.last_location?.lat ??
                  'N/A'}
                ,{' '}
                {machineStats?.message?.location?.long ??
                  device?.last_location?.long ??
                  'N/A'}
              </div>
              <div>
                <span className="font-medium">Last known:</span>{' '}
                {device?.last_location?.lat ?? 'N/A'},{' '}
                {device?.last_location?.long ?? 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

export default DeviceInfo;
