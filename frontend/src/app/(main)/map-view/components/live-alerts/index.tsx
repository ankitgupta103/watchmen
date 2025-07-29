// 'use client';

// import React, { useCallback, useEffect, useRef, useState } from 'react';
// import { usePubSub } from '@/hooks/use-pub-sub';
// import useToken from '@/hooks/use-token';
// import {
//   Bell,
//   Camera,
//   CheckCircle,
//   Clock,
//   Image as ImageIcon,
//   Loader2,
//   Play,
//   Volume2,
//   VolumeX,
//   Wifi,
//   X,
// } from 'lucide-react';
// import Image from 'next/image';
// import { toast } from 'sonner';

// import { Alert, AlertDescription } from '@/components/ui/alert';
// import { Badge } from '@/components/ui/badge';
// import { Button } from '@/components/ui/button';
// import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
// import { Input } from '@/components/ui/input';
// import { Separator } from '@/components/ui/separator';

// import { API_BASE_URL } from '@/lib/constants';
// import { fetcherClient } from '@/lib/fetcher-client';
// import { Machine } from '@/lib/types/machine';
// import { cn } from '@/lib/utils';

// import { AudioManager } from '../audio-manager';
// import AlertModal from './alert-modal';

// // Types for alert system
// interface EventMessage {
//   eventstr?: string;
//   image_c_key: string;
//   image_f_key: string;
//   event_severity: string;
//   meta?: {
//     node_id: string;
//     hb_count: string;
//     last_hb_time: string;
//     photos_taken: string;
//     events_seen: string;
//   };
// }

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

// interface AlertSystemProps {
//   organizationId: string;
//   machines: Machine[];
//   onAlertReceived?: (alert: EventAlert) => void;
//   enableSound?: boolean;
//   useAlertTopics?: boolean; // Whether to use separate alert topics
//   severityThreshold?: number; // Only process events above this severity
// }

// const globalAlertProcessedEvents = new Set<string>();

// export default function CriticalAlertSystem({
//   organizationId,
//   machines,
//   onAlertReceived = (alert) => {
//     console.log('Alert received:', alert);
//   },
//   enableSound = true,
//   severityThreshold = 1,
// }: AlertSystemProps) {
//   const { token } = useToken();
//   const [alerts, setAlerts] = useState<EventAlert[]>([]);
//   const [isAudioEnabled, setIsAudioEnabled] = useState(enableSound);
//   const [isModalOpen, setIsModalOpen] = useState(false);
//   const [volume, setVolume] = useState(0.7);
//   const [unacknowledgedCount, setUnacknowledgedCount] = useState(0);

//   const audioManagerRef = useRef(new AudioManager());
//   const flashIntervalRef = useRef<NodeJS.Timeout | null>(null);
//   const modalRef = useRef<HTMLDivElement>(null);
//   const processedEventKeysRef = useRef(new Set<string>());

//   const topics = React.useMemo(() => {
//     if (machines.length === 0) {
//       console.log('[AlertSystem] No machines provided');
//       return [];
//     }

//     const generatedTopics = machines.map(
//       (machine) => `${organizationId}/_all_/+/${machine.id}/_all_/EVENT/#`,
//     );

//     console.log('[AlertSystem] Generated topics:', generatedTopics);
//     return generatedTopics;
//   }, [organizationId, machines]);

//   useEffect(() => {
//     const initAudio = async () => {
//       if (isAudioEnabled) {
//         console.log('[AlertSystem] Initializing audio...');
//         try {
//           await audioManagerRef.current.initialize();
//           console.log('[AlertSystem] Audio initialized successfully');
//         } catch (error) {
//           console.error('[AlertSystem] Audio initialization failed:', error);
//         }
//       }
//     };

//     const handleUserInteraction = () => {
//       initAudio();
//       document.removeEventListener('click', handleUserInteraction);
//       document.removeEventListener('keydown', handleUserInteraction);
//       document.removeEventListener('touchstart', handleUserInteraction);
//     };

//     // Try multiple event types for better browser compatibility
//     document.addEventListener('click', handleUserInteraction);
//     document.addEventListener('keydown', handleUserInteraction);
//     document.addEventListener('touchstart', handleUserInteraction);

//     // Also try to initialize immediately
//     initAudio();

//     return () => {
//       document.removeEventListener('click', handleUserInteraction);
//       document.removeEventListener('keydown', handleUserInteraction);
//       document.removeEventListener('touchstart', handleUserInteraction);
//     };
//   }, [isAudioEnabled]);

//   // Flash effect for critical alerts
//   const startFlashing = useCallback(() => {
//     if (flashIntervalRef.current) return;

//     console.log('🚨 [AlertSystem] Starting screen flash');
//     let isRed = false;
//     flashIntervalRef.current = setInterval(() => {
//       document.body.style.backgroundColor = isRed
//         ? ''
//         : 'rgba(239, 68, 68, 0.1)';
//       isRed = !isRed;
//     }, 500);

//     setTimeout(() => {
//       if (flashIntervalRef.current) {
//         clearInterval(flashIntervalRef.current);
//         flashIntervalRef.current = null;
//         document.body.style.backgroundColor = '';
//         console.log('⏹️ [AlertSystem] Screen flash stopped');
//       }
//     }, 5000);
//   }, []);

//   // Fetch images from Django backend
//   const fetchEventImages = async (imageKeys: {
//     image_c_key: string;
//     image_f_key: string;
//   }) => {
//     try {
//       if (!token) {
//         console.log('⚠️ [AlertSystem] No token for image fetching');
//         return null;
//       }

//       console.log('📸 [AlertSystem] Fetching images:', imageKeys);
//       const data = await fetcherClient<{
//         success: boolean;
//         cropped_image_url: string;
//         full_image_url: string;
//         error?: string;
//       }>(`${API_BASE_URL}/event-images/`, token, {
//         method: 'POST',
//         body: imageKeys,
//       });

//       if (data?.success) {
//         console.log('✅ [AlertSystem] Images fetched successfully');
//         return {
//           croppedImageUrl: data.cropped_image_url,
//           fullImageUrl: data.full_image_url,
//         };
//       } else {
//         throw new Error(data?.error || 'Failed to fetch images');
//       }
//     } catch (error) {
//       console.error('❌ [AlertSystem] Error fetching images:', error);
//       return null;
//     }
//   };

//   // Enhanced MQTT message handler with extensive debugging
//   const handleMqttMessage = useCallback(
//     // eslint-disable-next-line @typescript-eslint/no-explicit-any
//     async (topic: string, data: any) => {
//       const now = new Date();

//       console.log('📥 [AlertSystem] MQTT message received:', {
//         topic,
//         data: JSON.stringify(data).substring(0, 200),
//         timestamp: now.toISOString(),
//       });

//       try {
//         // Extract machine ID from topic
//         const topicParts = topic.split('/');
//         const machineId = topicParts[3];

//         console.log('🔍 [AlertSystem] Parsed topic:', {
//           topicParts,
//           machineId,
//         });

//         // Find machine info
//         const machine = machines.find((m) => m.id === parseInt(machineId));
//         const machineName = machine?.name || `Machine-${machineId}`;

//         console.log('🏭 [AlertSystem] Machine info:', {
//           machineId,
//           machineName,
//           found: !!machine,
//         });

//         // Parse event message
//         const eventMessage: EventMessage = data;
//         const severity = parseInt(eventMessage.event_severity || '0');

//         console.log('📊 [AlertSystem] Event details:', {
//           severity,
//           severityThreshold,
//           eventstr: eventMessage.eventstr,
//           hasImageKeys: !!(
//             eventMessage.image_c_key && eventMessage.image_f_key
//           ),
//           imageKeys: {
//             c_key: eventMessage.image_c_key,
//             f_key: eventMessage.image_f_key,
//           },
//         });

//         // Check severity threshold
//         if (severity < severityThreshold) {
//           console.log(
//             `⚠️ [AlertSystem] Severity ${severity} < threshold ${severityThreshold}, filtering out`,
//           );
//           return;
//         }

//         // Create event key for deduplication
//         const eventKey = `alert_${eventMessage.image_f_key}_${eventMessage.image_c_key}_${machineId}_${severity}`;
//         console.log('🔑 [AlertSystem] Event key:', eventKey);

//         // Check for duplicates
//         if (
//           processedEventKeysRef.current.has(eventKey) ||
//           globalAlertProcessedEvents.has(eventKey)
//         ) {
//           console.log(`🔄 [AlertSystem] Duplicate detected: ${eventKey}`);
//           return;
//         }

//         // Mark as processed
//         processedEventKeysRef.current.add(eventKey);
//         globalAlertProcessedEvents.add(eventKey);

//         // Cleanup old entries
//         if (globalAlertProcessedEvents.size > 500) {
//           const entries = Array.from(globalAlertProcessedEvents);
//           const toRemove = entries.slice(0, entries.length - 400);
//           toRemove.forEach((key) => globalAlertProcessedEvents.delete(key));
//           console.log('🧹 [AlertSystem] Cleaned up old processed events');
//         }

//         console.log('✅ [AlertSystem] Creating new alert for event:', eventKey);

//         // Create alert
//         const alert: EventAlert = {
//           id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
//           timestamp: new Date(),
//           machineId,
//           machineName,
//           message: eventMessage,
//           acknowledged: false,
//           imagesFetched: false,
//           fetchingImages: false,
//         };

//         // Add to state
//         setAlerts((prev) => [alert, ...prev.slice(0, 49)]);
//         setUnacknowledgedCount((prev) => prev + 1);

//         // Play audio
//         if (isAudioEnabled && severity >= severityThreshold) {
//           console.log('🔊 [AlertSystem] Playing alarm for severity', severity);
//           try {
//             await audioManagerRef.current.playAlarm(volume);
//             console.log('✅ [AlertSystem] Alarm played successfully');
//           } catch (error) {
//             console.error('❌ [AlertSystem] Failed to play alarm:', error);
//           }
//         } else {
//           console.log(
//             '🔇 [AlertSystem] Audio disabled or severity too low, skipping sound',
//           );
//         }

//         // Flash for critical alerts
//         if (severity >= 3) {
//           startFlashing();
//         }

//         // Show toast
//         toast.custom(
//           (t) => (
//             <div className="flex w-full max-w-md items-center justify-between rounded-lg border border-red-400 bg-red-50 p-3 shadow-lg">
//               <div className="flex items-center gap-3">
//                 <Camera className="h-5 w-5 text-red-500" />
//                 <div>
//                   <p className="text-sm font-semibold text-gray-900">
//                     🚨 ALERT
//                   </p>
//                   <p className="text-sm text-gray-700">
//                     {machineName}: Severity {severity}
//                   </p>
//                 </div>
//               </div>
//               <Button
//                 variant="ghost"
//                 size="sm"
//                 onClick={() => toast.dismiss(t)}
//                 className="ml-2"
//               >
//                 <X className="h-4 w-4" />
//               </Button>
//             </div>
//           ),
//           {
//             duration: 5000,
//             id: alert.id,
//             position: 'bottom-right',
//           },
//         );

//         // Callback
//         if (onAlertReceived) {
//           onAlertReceived(alert);
//         }

//         console.log('🎉 [AlertSystem] Alert processing complete');
//       } catch (error) {
//         console.error('❌ [AlertSystem] Error processing MQTT message:', error);
//       }
//     },
//     [
//       machines,
//       isAudioEnabled,
//       volume,
//       startFlashing,
//       onAlertReceived,
//       severityThreshold,
//     ],
//   );

//   // Use PubSub hook
//   const { isConnected, error } = usePubSub(topics, handleMqttMessage, {
//     autoReconnect: true,
//     parseJson: true,
//     enableBufferedMessages: false,
//   });

//   // Update connection status in debug stats
//   useEffect(() => {

//     if (isConnected) {
//       console.log('✅ [AlertSystem] MQTT connected to topics:', topics);
//     } else if (error) {
//       console.error('❌ [AlertSystem] MQTT error:', error);
//     } else {
//       console.log('🔄 [AlertSystem] MQTT connecting...');
//     }
//   }, [isConnected, error, topics]);

//   // Polling for images
//   useEffect(() => {
//     const pollForImages = async () => {
//       const alertsNeedingImages = alerts.filter(
//         (alert) => !alert.imagesFetched && !alert.fetchingImages,
//       );

//       if (alertsNeedingImages.length === 0) return;

//       setAlerts((prev) =>
//         prev.map((alert) =>
//           alertsNeedingImages.some((a) => a.id === alert.id)
//             ? { ...alert, fetchingImages: true }
//             : alert,
//         ),
//       );

//       for (const alert of alertsNeedingImages) {
//         try {
//           const imageUrls = await fetchEventImages({
//             image_c_key: alert.message.image_c_key,
//             image_f_key: alert.message.image_f_key,
//           });

//           setAlerts((prev) =>
//             prev.map((a) =>
//               a.id === alert.id
//                 ? {
//                     ...a,
//                     croppedImageUrl: imageUrls?.croppedImageUrl,
//                     fullImageUrl: imageUrls?.fullImageUrl,
//                     imagesFetched: true,
//                     fetchingImages: false,
//                   }
//                 : a,
//             ),
//           );
//         } catch (error) {
//           console.error(`Failed to fetch images for alert ${alert.id}:`, error);
//           setAlerts((prev) =>
//             prev.map((a) =>
//               a.id === alert.id ? { ...a, fetchingImages: false } : a,
//             ),
//           );
//         }
//       }
//     };

//     const interval = setInterval(pollForImages, 5000);
//     return () => clearInterval(interval);
//   }, [alerts, token]);

//   // Click outside handler
//   useEffect(() => {
//     const handleClickOutside = (event: MouseEvent) => {
//       if (
//         modalRef.current &&
//         !modalRef.current.contains(event.target as Node)
//       ) {
//         setIsModalOpen(false);
//       }
//     };

//     if (isModalOpen) {
//       document.addEventListener('mousedown', handleClickOutside);
//     } else {
//       document.removeEventListener('mousedown', handleClickOutside);
//     }

//     return () => {
//       document.removeEventListener('mousedown', handleClickOutside);
//     };
//   }, [isModalOpen]);

//   return (
//     <>
//       <div className="fixed top-4 right-4 z-50">
//           <Button
//             onClick={() => setIsModalOpen(!isModalOpen)}
//             className={cn(
//               'relative',
//               unacknowledgedCount > 0
//                 ? 'animate-pulse bg-red-500 hover:bg-red-600'
//                 : '',
//             )}
//             size="lg"
//           >
//             <Bell className="mr-2 h-5 w-5" />
//             Alerts
//             {unacknowledgedCount > 0 && (
//               <Badge className="absolute -top-2 -right-2 h-5 min-w-[20px] bg-yellow-500 px-1 text-black">
//                 {unacknowledgedCount > 99 ? '99+' : unacknowledgedCount}
//               </Badge>
//             )}
//           </Button>
//       </div>

//       {/* Alert Modal */}
//       {isModalOpen && (
//         <AlertModal
//           isModalOpen={isModalOpen}
//           setIsModalOpen={setIsModalOpen}
//           unacknowledgedCount={unacknowledgedCount}
//           isAudioEnabled={isAudioEnabled}
//           setIsAudioEnabled={setIsAudioEnabled}
//           modalRef={modalRef}
//         />
//       )}
//     </>
//   );
// }
