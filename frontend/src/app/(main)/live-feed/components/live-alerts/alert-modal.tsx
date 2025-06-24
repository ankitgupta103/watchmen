// import { Alert, AlertDescription } from '@/components/ui/alert'
// import { Badge } from '@/components/ui/badge'
// import { Button } from '@/components/ui/button'
// import { Card, CardContent, CardHeader } from '@/components/ui/card'
// import { CardTitle } from '@/components/ui/card'
// import { Input } from '@/components/ui/input'
// import { Separator } from '@/components/ui/separator'
// import { cn } from '@/lib/utils'
// import { Camera, CheckCircle, Clock, ImageIcon, Loader2, Play, Volume2, VolumeX, Wifi } from 'lucide-react'
// import Image from 'next/image'
// import React, { useCallback } from 'react'
// import { toast } from 'sonner'
// import { AudioManager } from '../audio-manager'
// import { EventMessage } from '@/lib/types/activity'

// interface EventAlert {
//   id: string;
//   timestamp: Date;
//   machineId: string;
//   machineName: string;
//   message: EventMessage;
//   croppedImageUrl?: string;
//   fullImageUrl?: string;
//   acknowledged: boolean;
//   imagesFetched: boolean;
//   fetchingImages: boolean;
// }

// interface AlertModal {
//   setIsModalOpen: (isModalOpen: boolean) => void;
//   unacknowledgedCount: number;
//   isAudioEnabled: boolean;
//   setIsAudioEnabled: (isAudioEnabled: boolean) => void;
//   modalRef: React.RefObject<HTMLDivElement>;
//   audioManagerRef: React.RefObject<AudioManager>;
//   volume: number;
//   alerts: EventAlert[];
//   setAlerts: (alerts: EventAlert[]) => void;
//   setUnacknowledgedCount: (unacknowledgedCount: number) => void;
//   processedEventKeysRef: React.RefObject<Set<string>>;
//   globalAlertProcessedEvents: Set<string>;
//   isConnected: boolean;
//   error: Error | null;
// }

// export default function AlertModal({
//   setIsModalOpen,
//   unacknowledgedCount,
//   isAudioEnabled,
//   setIsAudioEnabled,
//   modalRef,
//   audioManagerRef,
//   volume,
//   alerts,
//   setAlerts,
//   setUnacknowledgedCount,
//   processedEventKeysRef,
//   globalAlertProcessedEvents,
//   isConnected,
//   error,
//   severityThreshold,
//   machines,
// }: AlertModal) {

//     const testAudio = async () => {
//     console.log('🧪 [AlertSystem] Testing audio manually...');
//     try {
//       await audioManagerRef.current.playAlarm(volume);
//       console.log('✅ [AlertSystem] Test audio played successfully');
//       toast.success('Audio test successful!');
//     } catch (error) {
//       console.error('❌ [AlertSystem] Test audio failed:', error);
//       toast.error('Audio test failed: ' + error);
//     }
//   };

//     const acknowledgeAlert = useCallback((alertId: string) => {
//     setAlerts((prev) =>
//       prev.map((alert) =>
//         alert.id === alertId ? { ...alert, acknowledged: true } : alert,
//       ),
//     );
//     setUnacknowledgedCount((prev) => Math.max(0, prev - 1));
//   }, []);

//   const acknowledgeAll = useCallback(() => {
//     setAlerts((prev) =>
//       prev.map((alert) => ({ ...alert, acknowledged: true })),
//     );
//     setUnacknowledgedCount(0);
//   }, []);

//   const clearAll = useCallback(() => {
//     setAlerts([]);
//     setUnacknowledgedCount(0);
//     processedEventKeysRef.current.clear();
//     globalAlertProcessedEvents.clear();
//   }, []);

//     const getTimeElapsed = (timestamp: Date) => {
//     const now = new Date();
//     const diff = now.getTime() - timestamp.getTime();
//     const minutes = Math.floor(diff / 60000);
//     const seconds = Math.floor((diff % 60000) / 1000);
//     return minutes > 0 ? `${minutes}m ${seconds}s ago` : `${seconds}s ago`;
//   };

//   return (
//             <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4">
//           <Card
//             className="h-full w-full max-w-4xl overflow-hidden"
//             ref={modalRef}
//           >
//             <CardHeader className="pb-3">
//               <div className="flex items-center justify-between">
//                 <CardTitle className="flex items-center gap-2">
//                   <Camera className="h-5 w-5 text-red-500" />
//                   Critical Alert System
//                   {unacknowledgedCount > 0 && (
//                     <Badge variant="destructive">
//                       {unacknowledgedCount} New
//                     </Badge>
//                   )}
//                 </CardTitle>
//                 <div className="flex items-center gap-2">
//                   <Button
//                     variant="ghost"
//                     size="sm"
//                     onClick={() => setIsAudioEnabled(!isAudioEnabled)}
//                     title="Toggle Audio"
//                   >
//                     {isAudioEnabled ? (
//                       <Volume2 className="h-4 w-4" />
//                     ) : (
//                       <VolumeX className="h-4 w-4" />
//                     )}
//                   </Button>
//                   <Button
//                     variant="ghost"
//                     size="sm"
//                     onClick={testAudio}
//                     title="Test Audio"
//                   >
//                     <Play className="h-4 w-4" />
//                   </Button>
//                   <Button
//                     variant="ghost"
//                     size="sm"
//                     onClick={() => setIsModalOpen(false)}
//                   >
//                     <X className="h-4 w-4" />
//                   </Button>
//                 </div>
//               </div>

//               {/* Controls */}
//               <div className="mt-2 flex gap-2">
//                 {unacknowledgedCount > 0 && (
//                   <Button size="sm" onClick={acknowledgeAll} className="flex-1">
//                     <CheckCircle className="mr-1 h-4 w-4" />
//                     Acknowledge All
//                   </Button>
//                 )}
//                 <Button
//                   size="sm"
//                   variant="outline"
//                   onClick={clearAll}
//                   className="flex-1"
//                 >
//                   Clear All
//                 </Button>
//               </div>

//               {/* Volume Control */}
//               {isAudioEnabled && (
//                 <div className="mt-2 flex items-center gap-2">
//                   <VolumeX className="h-4 w-4" />
//                   <Input
//                     type="range"
//                     min="0"
//                     max="1"
//                     step="0.1"
//                     value={volume}
//                     onChange={(e) => setVolume(parseFloat(e.target.value))}
//                     className="flex-1"
//                   />
//                   <Volume2 className="h-4 w-4" />
//                   <span className="w-8 text-xs">
//                     {Math.round(volume * 100)}%
//                   </span>
//                 </div>
//               )}
//             </CardHeader>

//             <CardContent className="p-0">
//               {/* Status */}
//               <div className="px-4 pb-3">
//                 <Alert
//                   className={cn(
//                     isConnected
//                       ? 'border-green-200 bg-green-50'
//                       : 'border-red-200 bg-red-50',
//                   )}
//                 >
//                   <Wifi
//                     className={cn(
//                       'h-4 w-4',
//                       isConnected ? 'text-green-600' : 'text-red-600',
//                     )}
//                   />
//                   <AlertDescription
//                     className={cn(
//                       isConnected ? 'text-green-800' : 'text-red-800',
//                     )}
//                   >
//                     {isConnected
//                       ? `Connected - Monitoring ${machines.length} machines (Severity ≥ ${severityThreshold})`
//                       : error
//                         ? `Connection Error: ${error.message}`
//                         : 'Connecting...'}
//                   </AlertDescription>
//                 </Alert>
//               </div>

//               <Separator />

//               {/* Alerts List */}
//               <div className="max-h-[60vh] overflow-y-auto">
//                 {alerts.length === 0 ? (
//                   <div className="p-8 text-center text-gray-500">
//                     <Camera className="mx-auto mb-2 h-12 w-12 opacity-30" />
//                     <p>No alerts detected</p>
//                     <p className="text-sm">
//                       Monitoring severity ≥ {severityThreshold}...
//                     </p>
//                   </div>
//                 ) : (
//                   <div className="grid gap-4 p-4">
//                     {alerts.map((alert) => (
//                       <div
//                         key={alert.id}
//                         className={cn(
//                           'rounded-lg border p-4 transition-all',
//                           alert.acknowledged
//                             ? 'border-gray-200 bg-gray-50'
//                             : parseInt(alert.message.event_severity) >= 3
//                               ? 'border-red-200 bg-red-50 shadow-md'
//                               : 'border-orange-200 bg-orange-50',
//                         )}
//                       >
//                         <div className="mb-3 flex items-start justify-between">
//                           <div className="flex items-center gap-2">
//                             <Camera className="h-5 w-5 text-red-500" />
//                             <div>
//                               <Badge variant="destructive" className="text-xs">
//                                 🚨 ALERT
//                               </Badge>
//                               {!alert.acknowledged && (
//                                 <Badge
//                                   variant="outline"
//                                   className="ml-1 text-xs"
//                                 >
//                                   NEW
//                                 </Badge>
//                               )}
//                             </div>
//                           </div>
//                           <div className="flex items-center gap-1">
//                             <Clock className="h-3 w-3 text-gray-400" />
//                             <span className="text-xs text-gray-500">
//                               {getTimeElapsed(alert.timestamp)}
//                             </span>
//                           </div>
//                         </div>

//                         <div className="mb-3">
//                           <div className="mb-1 font-medium text-gray-900">
//                             {alert.machineName}
//                           </div>
//                           <div className="text-sm text-gray-600">
//                             Event: {alert.message.eventstr || 'No description'}
//                           </div>
//                           <div className="text-sm text-gray-600">
//                             Severity: {alert.message.event_severity}(
//                             {alert.message.event_severity === '1'
//                               ? 'Low'
//                               : alert.message.event_severity === '2'
//                                 ? 'High'
//                                 : 'Critical'}
//                             )
//                           </div>
//                         </div>

//                         {/* Image Display */}
//                         <div className="mb-3">
//                           {alert.fetchingImages ? (
//                             <div className="flex items-center gap-2 text-sm text-gray-500">
//                               <Loader2 className="h-4 w-4 animate-spin" />
//                               Fetching images...
//                             </div>
//                           ) : alert.imagesFetched ? (
//                             <div className="flex items-center gap-2">
//                               {alert.croppedImageUrl && (
//                                 <div>
//                                   <p className="mb-1 text-xs text-gray-500">
//                                     Cropped
//                                   </p>
//                                   <Image
//                                     width={100}
//                                     height={100}
//                                     src={alert.croppedImageUrl}
//                                     alt="Cropped event image"
//                                     className="h-80 w-fit rounded border object-contain"
//                                   />
//                                 </div>
//                               )}
//                               {alert.fullImageUrl && (
//                                 <div>
//                                   <p className="mb-1 text-xs text-gray-500">
//                                     Full
//                                   </p>
//                                   <Image
//                                     width={100}
//                                     height={100}
//                                     src={alert.fullImageUrl}
//                                     alt="Full event image"
//                                     className="h-80 w-fit rounded border object-contain"
//                                   />
//                                 </div>
//                               )}
//                             </div>
//                           ) : (
//                             <div className="flex items-center gap-2 text-sm text-gray-500">
//                               <ImageIcon className="h-4 w-4" />
//                               Images not available yet...
//                             </div>
//                           )}
//                         </div>

//                         <div className="flex items-center justify-between">
//                           <div className="text-xs text-gray-500">
//                             Machine ID: {alert.machineId}
//                           </div>
//                           {!alert.acknowledged && (
//                             <Button
//                               size="sm"
//                               variant="outline"
//                               onClick={() => acknowledgeAlert(alert.id)}
//                               className="text-xs"
//                             >
//                               <CheckCircle className="mr-1 h-3 w-3" />
//                               Acknowledge
//                             </Button>
//                           )}
//                         </div>
//                       </div>
//                     ))}
//                   </div>
//                 )}
//               </div>
//             </CardContent>
//           </Card>
//         </div>
//   )
// }
