import React, { useState } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Camera,
  CheckCircle,
  Clock,
  Eye,
  MapPin,
  Power,
  RefreshCw,
  Settings,
  Shield,
  Video,
  XCircle,
} from 'lucide-react';
import Image from 'next/image';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { Machine } from '@/lib/types/machine';
import { cn, toTitleCase } from '@/lib/utils';

interface MachineDetailModalProps {
  selectedMachine: Machine | null;
  setSelectedMachine: React.Dispatch<React.SetStateAction<Machine | null>>;
}

export default function MachineDetailModal({
  selectedMachine,
  setSelectedMachine,
}: MachineDetailModalProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const [isExecutingCommand, setIsExecutingCommand] = useState(false);

  if (!selectedMachine) return null;

  // Calculate machine activity level
  const getMachineActivityLevel = (machine: Machine) => {
    const recentEvents =
      machine.data.suspiciousEvents?.filter((event) => {
        const eventDate = new Date(event.timestamp);
        const daysDiff =
          (Date.now() - eventDate.getTime()) / (1000 * 60 * 60 * 24);
        return daysDiff <= 7;
      }) || [];

    const healthIssues =
      machine.data.healthEvents?.filter(
        (event) => event.severity === 'high' || event.severity === 'critical',
      ) || [];

    if (recentEvents.length > 5 || healthIssues.length > 0) return 'critical';
    if (recentEvents.length > 2) return 'high';
    if (recentEvents.length > 0) return 'medium';
    return 'low';
  };

  // Get unreviewed events count
  const getUnreviewedCount = (machine: Machine) => {
    return (
      machine.data.suspiciousEvents?.filter(
        (event) => event.marked === 'unreviewed' || !event.marked,
      ).length || 0
    );
  };

  // Mock command execution
  const executeCommand = async (command: string) => {
    setIsExecutingCommand(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsExecutingCommand(false);
    // In real implementation, this would call your API
    console.log(
      `Executing command: ${command} on machine ${selectedMachine.id}`,
    );
  };

  // Mock event marking
  const markEvent = (eventIndex: number, status: 'noted' | 'ignored') => {
    // In real implementation, this would update the event in your backend
    console.log(`Marking event ${eventIndex} as ${status}`);
  };

  const activityLevel = getMachineActivityLevel(selectedMachine);
  const unreviewed = getUnreviewedCount(selectedMachine);

  // Calculate time since last seen
  const getLastSeenText = (lastSeen: string) => {
    const lastSeenDate = new Date(lastSeen);
    const now = new Date();
    const diffMs = now.getTime() - lastSeenDate.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffHours > 24) {
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
    } else {
      return 'Just now';
    }
  };

  return (
    <Dialog
      open={!!selectedMachine}
      onOpenChange={() => setSelectedMachine(null)}
    >
      <DialogContent className="flex h-full max-h-[90vh] w-full flex-col overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 text-xl">
            <div
              className={cn(
                'h-4 w-4 rounded-full',
                selectedMachine.data.status === 'online'
                  ? 'bg-green-500'
                  : selectedMachine.data.status === 'offline'
                    ? 'bg-red-500'
                    : 'bg-yellow-500',
              )}
            ></div>
            {toTitleCase(selectedMachine.name)}
            <Badge variant="outline" className="ml-auto">
              {toTitleCase(selectedMachine.type.replace('_', ' '))}
            </Badge>
            {unreviewed > 0 && (
              <Badge variant="destructive">
                {unreviewed} Alert{unreviewed > 1 ? 's' : ''}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="suspicious" className="relative">
              Suspicious Events
              {unreviewed > 0 && (
                <div className="flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs text-white">
                  {unreviewed > 9 ? '9+' : unreviewed}
                </div>
              )}
            </TabsTrigger>
            <TabsTrigger value="health">Health & Status</TabsTrigger>
            <TabsTrigger value="controls">Device Controls</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Quick Status Cards */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
              <Card>
                <CardContent className="p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <Activity className="h-4 w-4 text-blue-500" />
                    <span className="text-sm font-medium">Status</span>
                  </div>
                  <Badge
                    variant={
                      selectedMachine.data.status === 'online'
                        ? 'default'
                        : selectedMachine.data.status === 'offline'
                          ? 'destructive'
                          : 'secondary'
                    }
                    className="capitalize"
                  >
                    {selectedMachine.data.status}
                  </Badge>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-500" />
                    <span className="text-sm font-medium">Last Seen</span>
                  </div>
                  <div className="text-sm">
                    {getLastSeenText(selectedMachine.data.lastSeen)}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                    <span className="text-sm font-medium">Activity</span>
                  </div>
                  <Badge
                    variant={
                      activityLevel === 'critical'
                        ? 'destructive'
                        : activityLevel === 'high'
                          ? 'destructive'
                          : activityLevel === 'medium'
                            ? 'secondary'
                            : 'outline'
                    }
                    className="capitalize"
                  >
                    {activityLevel}
                  </Badge>
                </CardContent>
              </Card>
            </div>

            {/* Location and Technical Details */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <MapPin className="h-5 w-5" />
                    Location & Deployment
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <span className="text-sm font-medium text-gray-500">
                      Coordinates:
                    </span>
                    <div className="text-sm">
                      {selectedMachine.location.lat.toFixed(6)},{' '}
                      {selectedMachine.location.lng.toFixed(6)}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">
                      Deployment Type:
                    </span>
                    <div className="text-sm capitalize">
                      {selectedMachine.type.replace('_', ' ')}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Shield className="h-5 w-5" />
                    Activity Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <span className="text-sm font-medium text-gray-500">
                      Total Suspicious Events:
                    </span>
                    <div className="text-sm">
                      {selectedMachine.data.suspiciousEvents?.length || 0}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">
                      Recent Events (7 days):
                    </span>
                    <div className="text-sm">
                      {selectedMachine.data.suspiciousEvents?.filter((e) => {
                        const days =
                          (Date.now() - new Date(e.timestamp).getTime()) /
                          (1000 * 60 * 60 * 24);
                        return days <= 7;
                      }).length || 0}{' '}
                      suspicious events
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">
                      Health Issues:
                    </span>
                    <div className="text-sm">
                      {selectedMachine.data.healthEvents?.filter(
                        (e) => e.severity !== 'low',
                      ).length || 0}{' '}
                      active issues
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">
                      Unreviewed Alerts:
                    </span>
                    <div className="text-sm font-medium text-red-600">
                      {unreviewed} pending review
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="col-span-full">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Camera className="h-5 w-5" />
                    Images Captured
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(() => {
                    const images = (selectedMachine.data.suspiciousEvents || []).filter(e => !!e.url);
                    if (images.length > 0) {
                      return images.map(event => (
                        <div key={event.timestamp}>
                          <Image
                            src={event.url!}
                            alt={`Image captured at ${event.timestamp}`}
                            width={100}
                            height={100}
                            className="h-full w-full"
                          />
                        </div>
                      ));
                    } else {
                      return (
                        <div className="text-center text-gray-500">
                          No images captured
                        </div>
                      );
                    }
                  })()}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Suspicious Events Tab */}
          <TabsContent value="suspicious" className="space-y-4">
            {selectedMachine.data.suspiciousEvents?.length ? (
              <div className="space-y-3">
                {selectedMachine.data.suspiciousEvents
                  .sort(
                    (a, b) =>
                      new Date(b.timestamp).getTime() -
                      new Date(a.timestamp).getTime(),
                  )
                  .map((event, index) => (
                    <Card
                      key={index}
                      className={cn(
                        'border-l-4 transition-all hover:shadow-md',
                        event.marked === 'noted'
                          ? 'border-l-blue-500 bg-blue-50/30'
                          : event.marked === 'ignored'
                            ? 'border-l-gray-500 bg-gray-50/30'
                            : 'border-l-red-500 bg-red-50/30',
                      )}
                    >
                      <CardContent className="p-4 space-y-3">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <Badge
                              variant={
                                event.confidence > 0.8
                                  ? 'destructive'
                                  : 'secondary'
                              }
                            >
                              {event.type.replace('_', ' ')}
                            </Badge>
                            <div className="text-sm">
                              <span className="font-medium">
                                {(event.confidence * 100).toFixed(0)}%
                              </span>
                              <span className="ml-1 text-gray-500">
                                confidence
                              </span>
                            </div>
                            {event.marked === 'unreviewed' || !event.marked ? (
                              <Badge
                                variant="outline"
                                className="border-yellow-300 bg-yellow-50 text-yellow-700"
                              >
                                Needs Review
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="capitalize">
                                {event.marked}
                              </Badge>
                            )}
                          </div>
                          <span className="text-xs text-gray-500">
                            {new Date(event.timestamp).toLocaleString()}
                          </span>
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex gap-2">
                            {(!event.marked ||
                              event.marked === 'unreviewed') && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => markEvent(index, 'noted')}
                                  className="border-blue-300 text-blue-600 hover:bg-blue-50"
                                >
                                  <CheckCircle className="mr-1 h-3 w-3" />
                                  Mark as Noted
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => markEvent(index, 'ignored')}
                                  className="text-gray-600 hover:bg-gray-50"
                                >
                                  <XCircle className="mr-1 h-3 w-3" />
                                  Ignore
                                </Button>
                              </>
                            )}
                          </div>
                          <div className="text-xs text-gray-500">
                            Risk Level:{' '}
                            {event.confidence > 0.9
                              ? 'Very High'
                              : event.confidence > 0.8
                                ? 'High'
                                : event.confidence > 0.6
                                  ? 'Medium'
                                  : 'Low'}
                          </div>
                        </div>
                        {event.url && (
                          <Image
                            src={event.url}
                            alt={`Image captured at ${event.timestamp}`}
                            width={100}
                            height={100}
                            className="h-full w-full"
                          />
                        )}
                      </CardContent>
                    </Card>
                  ))}
              </div>
            ) : (
              <div className="py-12 text-center">
                <Shield className="mx-auto mb-4 h-16 w-16 text-gray-300" />
                <h3 className="mb-2 text-lg font-medium text-gray-600">
                  All Clear
                </h3>
                <p className="text-gray-500">
                  No suspicious events recorded for this device
                </p>
              </div>
            )}
          </TabsContent>

          {/* Health & Status Tab */}
          <TabsContent value="health" className="space-y-4">
            {selectedMachine.data.healthEvents?.length ? (
              <div className="space-y-3">
                {selectedMachine.data.healthEvents
                  .sort(
                    (a, b) =>
                      new Date(b.timestamp).getTime() -
                      new Date(a.timestamp).getTime(),
                  )
                  .map((event, index) => (
                    <Card key={index}>
                      <CardContent className="p-4">
                        <div className="mb-3 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <AlertTriangle
                              className={cn(
                                'h-5 w-5',
                                event.severity === 'critical'
                                  ? 'text-red-500'
                                  : event.severity === 'high'
                                    ? 'text-orange-500'
                                    : event.severity === 'medium'
                                      ? 'text-yellow-500'
                                      : 'text-blue-500',
                              )}
                            />
                            <div>
                              <span className="font-medium">
                                {toTitleCase(event.type.replace('_', ' '))}
                              </span>
                              <div className="text-sm text-gray-500">
                                {event.type === 'offline'
                                  ? 'Device went offline and is not responding'
                                  : event.type === 'hardware_failure'
                                    ? 'Hardware component malfunction detected'
                                    : event.type === 'low_battery'
                                      ? 'Battery level is below optimal threshold'
                                      : event.type === 'gps_failure'
                                        ? 'GPS positioning system failure'
                                        : event.type === 'camera_failure'
                                          ? 'Camera or imaging system failure'
                                          : 'System health issue detected'}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge
                              variant={
                                event.severity === 'critical'
                                  ? 'destructive'
                                  : event.severity === 'high'
                                    ? 'destructive'
                                    : 'secondary'
                              }
                              className="mb-1"
                            >
                              {toTitleCase(event.severity)}
                            </Badge>
                            <div className="text-xs text-gray-500">
                              {new Date(event.timestamp).toLocaleString()}
                            </div>
                          </div>
                        </div>

                        {event.severity === 'critical' && (
                          <Alert className="border-red-200 bg-red-50">
                            <AlertCircle className="h-4 w-4 text-red-600" />
                            <AlertDescription className="text-red-800">
                              This issue requires immediate attention and may
                              affect device functionality.
                            </AlertDescription>
                          </Alert>
                        )}
                      </CardContent>
                    </Card>
                  ))}
              </div>
            ) : (
              <div className="py-12 text-center">
                <Activity className="mx-auto mb-4 h-16 w-16 text-green-300" />
                <h3 className="mb-2 text-lg font-medium text-gray-600">
                  All Systems Operational
                </h3>
                <p className="text-gray-500">
                  No health issues detected for this device
                </p>
              </div>
            )}
          </TabsContent>

          {/* Device Controls Tab */}
          <TabsContent value="controls" className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Basic Controls */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Basic Controls</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    disabled={isExecutingCommand}
                    onClick={() => executeCommand('reboot')}
                  >
                    <RefreshCw
                      className={cn(
                        'mr-2 h-4 w-4',
                        isExecutingCommand && 'animate-spin',
                      )}
                    />
                    Reboot Device
                  </Button>
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    disabled={isExecutingCommand}
                    onClick={() => executeCommand('live_feed')}
                  >
                    <Video className="mr-2 h-4 w-4" />
                    Request Live Feed
                  </Button>
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    disabled={isExecutingCommand}
                    onClick={() => executeCommand('status_check')}
                  >
                    <Activity className="mr-2 h-4 w-4" />
                    Force Status Check
                  </Button>
                </CardContent>
              </Card>

              {/* Advanced Controls */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Advanced Controls</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    disabled={isExecutingCommand}
                    onClick={() => executeCommand('power_management')}
                  >
                    <Power className="mr-2 h-4 w-4" />
                    Power Management
                  </Button>
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    disabled={isExecutingCommand}
                    onClick={() => executeCommand('device_settings')}
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    Device Settings
                  </Button>
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    disabled={isExecutingCommand}
                    onClick={() => executeCommand('maintenance_mode')}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Maintenance Mode
                  </Button>
                </CardContent>
              </Card>
            </div>

            <Separator />

            {/* Emergency Controls */}
            <Card className="border-red-200 bg-red-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg text-red-800">
                  <AlertTriangle className="h-5 w-5" />
                  Emergency Controls
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <Alert className="border-red-300 bg-red-100">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <AlertDescription className="text-red-800">
                      Emergency controls will immediately affect device
                      operation. Use with caution.
                    </AlertDescription>
                  </Alert>
                  <div className="flex gap-3">
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={isExecutingCommand}
                      onClick={() => executeCommand('emergency_shutdown')}
                    >
                      Emergency Shutdown
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={isExecutingCommand}
                      onClick={() => executeCommand('safe_mode')}
                      className="border-orange-300 text-orange-700 hover:bg-orange-50"
                    >
                      Enter Safe Mode
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {isExecutingCommand && (
              <Alert className="border-blue-200 bg-blue-50">
                <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
                <AlertDescription className="text-blue-800">
                  Executing command... Please wait.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
