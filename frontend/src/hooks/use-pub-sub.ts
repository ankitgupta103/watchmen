import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import PubSubService from '@/lib/aws-mqtt/pub-sub';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface MessageEntry<T = any> {
  timestamp: string;
  data: T;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TopicStateData<T = any> {
  currentMessage: MessageEntry<T> | null;
  messageCount: number;
  lastUpdate: string | null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AllTopicsDataState = Record<string, TopicStateData<any>>;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type TopicInput = string | { topic: string; [key: string]: any };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type UsePubSubCallback = (topic: string, parsedData: any) => void;

interface UsePubSubOptions {
  autoReconnect?: boolean;
  parseJson?: boolean;
  enableBufferedMessages?: boolean; // New option to control buffered message replay
}

interface UsePubSubReturn {
  isConnected: boolean;
  error: Error | null;
  topicData: AllTopicsDataState;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  publish: (topic: string, data: any) => Promise<void>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getCurrentMessage: (topic: string) => MessageEntry<any> | undefined;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  subscriptionStats: Record<string, any>;
}

// Default options
const DEFAULT_OPTIONS: UsePubSubOptions = {
  autoReconnect: true,
  parseJson: true,
  enableBufferedMessages: false, // Disabled by default to prevent duplicates
};

export const usePubSub = (
  topics: TopicInput[] = [],
  callback?: UsePubSubCallback,
  options: UsePubSubOptions = {},
): UsePubSubReturn => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const mergedOptions = { ...DEFAULT_OPTIONS, ...options };

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [topicData, setTopicData] = useState<AllTopicsDataState>({});

  // Refs to prevent stale closures and track subscriptions
  const optionsRef = useRef(mergedOptions);
  const callbackRef = useRef(callback);
  const subscribedTopicsRef = useRef<Set<string>>(new Set());
  const processedMessagesRef = useRef<Set<string>>(new Set());

  // Update refs when values change
  useEffect(() => {
    optionsRef.current = mergedOptions;
  }, [mergedOptions]);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Get singleton instance of PubSubService
  const pubSubService = useMemo(() => PubSubService.getInstance(), []);

  // Create a simple hash for message deduplication at hook level
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const createMessageHash = useCallback((topic: string, data: any): string => {
    try {
      const dataString = typeof data === 'string' ? data : JSON.stringify(data);
      return `${topic}:${dataString}:${Date.now()}`;
    } catch {
      return `${topic}:${Date.now()}:${Math.random()}`;
    }
  }, []);

  /**
   * Handle incoming messages from PubSubService
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMessage = useCallback((topic: string, messageData: any) => {
    let parsedData = messageData;

    if (optionsRef.current.parseJson && typeof messageData === 'string') {
      try {
        parsedData = JSON.parse(messageData);
      } catch (e) {
        console.error('[usePubSub] JSON parse error:', e);
        parsedData = messageData;
      }
    }

    // Additional deduplication at hook level
    const messageHash = createMessageHash(topic, parsedData);
    if (processedMessagesRef.current.has(messageHash)) {
      console.log(`[usePubSub] Hook-level duplicate detected: ${messageHash}`);
      return;
    }
    processedMessagesRef.current.add(messageHash);

    // Clean up old processed messages (keep last 100)
    if (processedMessagesRef.current.size > 100) {
      const entries = Array.from(processedMessagesRef.current);
      const toRemove = entries.slice(0, entries.length - 80);
      toRemove.forEach(hash => processedMessagesRef.current.delete(hash));
    }

    // Create message entry with timestamp
    const newMessageEntry: MessageEntry = {
      timestamp: new Date().toISOString(),
      data: parsedData,
    };

    // Update topic data state efficiently
    setTopicData((prev) => {
      const currentTopicData = prev[topic];
      const newMessageCount = (currentTopicData?.messageCount || 0) + 1;

      return {
        ...prev,
        [topic]: {
          currentMessage: newMessageEntry,
          messageCount: newMessageCount,
          lastUpdate: newMessageEntry.timestamp,
        },
      };
    });

    if (callbackRef.current) {
      try {
        callbackRef.current(topic, parsedData);
      } catch (callbackError) {
        console.error(
          `[usePubSub] Error in callback for topic ${topic}:`,
          callbackError,
        );
        setError(
          callbackError instanceof Error
            ? callbackError
            : new Error(String(callbackError)),
        );
      }
    }
  }, [createMessageHash]);

  // Connection event handlers
  useEffect(() => {
    let isMounted = true;

    const handleConnect = () => {
      if (isMounted) {
        console.log('[usePubSub] Connected');
        setIsConnected(true);
        setError(null);
      }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleError = (err: any) => {
      if (isMounted) {
        console.error('[usePubSub] Error:', err);
        setError(err instanceof Error ? err : new Error(String(err)));
      }
    };

    const handleDisconnect = () => {
      if (isMounted) {
        console.log('[usePubSub] Disconnected');
        setIsConnected(false);
        // Clear subscribed topics tracking on disconnect
        subscribedTopicsRef.current.clear();
      }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleHealthWarning = (data: any) => {
      if (isMounted) {
        console.warn('[usePubSub] Health check warning:', data);
      }
    };

    // Subscribe to events
    pubSubService.on('connect', handleConnect);
    pubSubService.on('error', handleError);
    pubSubService.on('disconnect', handleDisconnect);
    pubSubService.on('health_check_warning', handleHealthWarning);

    // Initialize connection
    if (pubSubService.isConnected) {
      handleConnect();
    } else if (!pubSubService.isInitializing) {
      pubSubService.initialize().catch(handleError);
    }

    return () => {
      isMounted = false;
      pubSubService.off('connect', handleConnect);
      pubSubService.off('error', handleError);
      pubSubService.off('disconnect', handleDisconnect);
      pubSubService.off('health_check_warning', handleHealthWarning);
    };
  }, [pubSubService]);

  // Stable topics array to prevent unnecessary re-subscriptions
  const stableTopics = useMemo(() => {
    return topics
      .map((t) => (typeof t === 'object' && t !== null ? t.topic : t))
      .filter((t): t is string => typeof t === 'string' && t.length > 0)
      .sort(); // Sort to ensure consistent ordering
  }, [topics]);

  // Topic subscriptions with improved duplicate prevention
  useEffect(() => {
    if (!isConnected || stableTopics.length === 0) {
      return;
    }

    const currentSubscriptions = new Set<string>();
    
    const setupSubscriptions = async () => {
      for (const topicName of stableTopics) {
        // Skip if already subscribed
        if (subscribedTopicsRef.current.has(topicName)) {
          console.log(`[usePubSub] Already subscribed to ${topicName}, skipping`);
          currentSubscriptions.add(topicName);
          continue;
        }

        try {
          await pubSubService.subscribe(topicName, handleMessage);
          subscribedTopicsRef.current.add(topicName);
          currentSubscriptions.add(topicName);
          
          console.log(`[usePubSub] Successfully subscribed to ${topicName}`);

          // Only process buffered messages if explicitly enabled
          if (optionsRef.current.enableBufferedMessages) {
            const bufferedMessages = pubSubService.getBufferedMessages(topicName);
            if (bufferedMessages.length > 0) {
              console.log(
                `[usePubSub] Processing ${bufferedMessages.length} buffered messages for ${topicName}`,
              );
              // Add a small delay to prevent overwhelming the callback
              setTimeout(() => {
                bufferedMessages.forEach((msg) => handleMessage(topicName, msg));
              }, 100);
            }
          }
        } catch (subError) {
          console.error(
            `[usePubSub] Failed to subscribe to topic ${topicName}:`,
            subError,
          );
          setError(
            subError instanceof Error ? subError : new Error(String(subError)),
          );
        }
      }

      // Unsubscribe from topics that are no longer needed
      const topicsToUnsubscribe = Array.from(subscribedTopicsRef.current).filter(
        topic => !stableTopics.includes(topic)
      );

      for (const topicName of topicsToUnsubscribe) {
        pubSubService.unsubscribe(topicName, handleMessage);
        subscribedTopicsRef.current.delete(topicName);
        console.log(`[usePubSub] Unsubscribed from ${topicName}`);
      }
    };

    setupSubscriptions();

    return () => {
      // Cleanup function - unsubscribe from current subscriptions
      for (const topicName of currentSubscriptions) {
        pubSubService.unsubscribe(topicName, handleMessage);
        subscribedTopicsRef.current.delete(topicName);
      }
    };
  }, [stableTopics, isConnected, handleMessage, pubSubService]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Clear all subscriptions for this hook instance
      for (const topicName of subscribedTopicsRef.current) {
        pubSubService.unsubscribe(topicName, handleMessage);
      }
      subscribedTopicsRef.current.clear();
      processedMessagesRef.current.clear();
    };
  }, [pubSubService, handleMessage]);

  const publish = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (topic: string, data: any): Promise<void> => {
      if (!isConnected) {
        const err = new Error('Cannot publish: Not connected');
        console.error('[usePubSub]', err.message);
        setError(err);
        throw err;
      }

      try {
        await pubSubService.publish(topic, data);
      } catch (pubError) {
        console.error(
          `[usePubSub] Failed to publish to topic ${topic}:`,
          pubError,
        );
        const err =
          pubError instanceof Error ? pubError : new Error(String(pubError));
        setError(err);
        throw err;
      }
    },
    [isConnected, pubSubService],
  );

  const getCurrentMessage = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (topic: string): MessageEntry<any> | undefined => {
      return topicData[topic]?.currentMessage || undefined;
    },
    [topicData],
  );

  // Get subscription stats
  const subscriptionStats = useMemo(() => {
    try {
      const stats = pubSubService.getSubscriptionStats();
      return {
        ...stats,
        hookSubscriptions: Array.from(subscribedTopicsRef.current),
        hookProcessedMessages: processedMessagesRef.current.size,
      };
    } catch {
      return {
        hookSubscriptions: Array.from(subscribedTopicsRef.current),
        hookProcessedMessages: processedMessagesRef.current.size,
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pubSubService, isConnected]);

  return {
    isConnected,
    error,
    topicData,
    publish,
    getCurrentMessage,
    subscriptionStats,
  };
};