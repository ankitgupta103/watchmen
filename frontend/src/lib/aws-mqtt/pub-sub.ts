import { EventEmitter } from 'events';
import { AWS_IOT_CONFIG } from '@/constants/aws-iot-config';
import { PubSub } from '@aws-amplify/pubsub';
import { Amplify, ResourcesConfig } from 'aws-amplify';

interface MinimalAmplifyObservable {
  subscribe(observer: MinimalAmplifyObserver): MinimalAmplifySubscription;
}

interface MinimalAmplifyObserver {
  next: (value: unknown) => void;
  error: (error: unknown) => void;
  complete: () => void;
}

interface MinimalAmplifySubscription {
  unsubscribe: () => void;
}

interface SubscriptionInfo {
  observableController: MinimalAmplifyObservable;
  activeSubscription: MinimalAmplifySubscription;
  callbacks: Set<PubSubSubscriptionCallback>;
  messageCount: number;
  lastMessageTime: number;
  lastProcessedMessages: Map<string, number>; // Track recent message hashes
}

export type PubSubSubscriptionCallback = (
  topic: string,
  messageData: unknown,
) => void;

export interface PubSubMessageEnvelope {
  value?: {
    data?: unknown;
    [key: string]: unknown;
  };
  data?: unknown;
  [key: string]: unknown;
}

const CONFIG = {
  MAX_RECONNECT_ATTEMPTS: 5,
  RECONNECT_INTERVAL: 2000, // ms
  MESSAGE_BUFFER_SIZE: 50, // Reduced from 100 to prevent excessive buffering
  CONNECTION_TIMEOUT: 30000, // ms
  HEALTH_CHECK_INTERVAL: 30000, // ms
  DUPLICATE_DETECTION_WINDOW: 5000, // 5 seconds window for duplicate detection
  MESSAGE_HASH_CLEANUP_INTERVAL: 60000, // 1 minute
};

class PubSubService extends EventEmitter {
  private static instance: PubSubService | null = null;
  private client: PubSub | null = null;
  public isConnected: boolean = false;
  public isInitializing: boolean = false;
  private subscriptions: Map<string, SubscriptionInfo> = new Map();
  private reconnectAttempts: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private connectionTimeout: NodeJS.Timeout | null = null;
  private messageHashCleanupTimer: NodeJS.Timeout | null = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private messageBuffer: Map<string, any[]> = new Map();
  private globalProcessedMessages = new Map<string, number>(); // Global deduplication

  private constructor() {
    super();
    this.setMaxListeners(100);
    this.startMessageHashCleanup();
  }

  public static getInstance(): PubSubService {
    if (!PubSubService.instance) {
      PubSubService.instance = new PubSubService();
    }
    return PubSubService.instance;
  }

  // Create a simple hash for message deduplication
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private createMessageHash(topic: string, data: any): string {
    try {
      const dataString = typeof data === 'string' ? data : JSON.stringify(data);
      // Create a simple hash combining topic and data
      let hash = 0;
      const str = `${topic}:${dataString}`;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash = hash & hash; // Convert to 32-bit integer
      }
      return hash.toString();
    } catch {
      // Fallback to timestamp if hashing fails
      return `${topic}:${Date.now()}:${Math.random()}`;
    }
  }

  private startMessageHashCleanup() {
    this.messageHashCleanupTimer = setInterval(() => {
      const now = Date.now();

      // Clean up old message hashes (older than detection window)
      for (const [hash, timestamp] of this.globalProcessedMessages.entries()) {
        if (now - timestamp > CONFIG.DUPLICATE_DETECTION_WINDOW) {
          this.globalProcessedMessages.delete(hash);
        }
      }

      // Clean up subscription-level message hashes
      this.subscriptions.forEach((info) => {
        for (const [hash, timestamp] of info.lastProcessedMessages.entries()) {
          if (now - timestamp > CONFIG.DUPLICATE_DETECTION_WINDOW) {
            info.lastProcessedMessages.delete(hash);
          }
        }
      });
    }, CONFIG.MESSAGE_HASH_CLEANUP_INTERVAL);
  }

  public async initialize(): Promise<PubSub> {
    if (this.isConnected && this.client) {
      return this.client;
    }

    if (this.isInitializing) {
      return this.waitForConnection();
    }

    this.isInitializing = true;
    this.clearConnectionTimeout();

    // Set connection timeout
    this.connectionTimeout = setTimeout(() => {
      if (!this.isConnected) {
        const error = new Error('Connection timeout');
        this.handleConnectionError(error);
      }
    }, CONFIG.CONNECTION_TIMEOUT);

    try {
      // Configure Amplify
      Amplify.configure(AWS_IOT_CONFIG.amplifyConfig as ResourcesConfig);

      this.client = new PubSub({
        region: AWS_IOT_CONFIG.region,
        endpoint: AWS_IOT_CONFIG.endpoint,
      });

      this.isConnected = true;
      this.isInitializing = false;
      this.reconnectAttempts = 0;
      this.clearConnectionTimeout();

      // Start health check
      this.startHealthCheck();

      this.emit('connect');

      if (!this.client) {
        throw new Error('Client is null after successful initialization.');
      }

      return this.client;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      this.handleConnectionError(error);
      throw error;
    }
  }

  private waitForConnection(): Promise<PubSub> {
    return new Promise<PubSub>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout while waiting'));
        this.removeListener('connect', onConnect);
        this.removeListener('error', onError);
      }, CONFIG.CONNECTION_TIMEOUT);

      const onConnect = () => {
        clearTimeout(timeout);
        if (this.client) {
          resolve(this.client);
        } else {
          reject(new Error('Client not available after connect event'));
        }
        this.removeListener('error', onError);
      };

      const onError = (err: unknown) => {
        clearTimeout(timeout);
        reject(err instanceof Error ? err : new Error(String(err)));
        this.removeListener('connect', onConnect);
      };

      this.once('connect', onConnect);
      this.once('error', onError);
    });
  }

  private handleConnectionError(error: unknown) {
    this.isConnected = false;
    this.isInitializing = false;
    this.clearConnectionTimeout();

    const typedError =
      error instanceof Error ? error : new Error(String(error));
    console.error('[PubSubService] Connection error:', typedError);
    this.emit('error', typedError);

    // Attempt reconnection
    this.scheduleReconnect();
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= CONFIG.MAX_RECONNECT_ATTEMPTS) {
      console.error('[PubSubService] Max reconnection attempts reached');
      this.emit('max_reconnect_attempts_reached');
      return;
    }

    if (this.reconnectTimer) {
      return; // Already scheduled
    }

    this.reconnectAttempts++;
    const delay =
      CONFIG.RECONNECT_INTERVAL * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `[PubSubService] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`,
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.initialize().catch((err) => {
        console.error('[PubSubService] Reconnection failed:', err);
      });
    }, delay);
  }

  private clearConnectionTimeout() {
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
  }

  private startHealthCheck() {
    this.stopHealthCheck();

    this.healthCheckTimer = setInterval(() => {
      if (this.isConnected && this.client) {
        // Check if we're still receiving messages
        const now = Date.now();
        let activeSubscriptions = 0;
        let staleSubscriptions = 0;

        this.subscriptions.forEach((info) => {
          if (info.callbacks.size > 0) {
            activeSubscriptions++;
            if (
              info.messageCount > 0 &&
              now - info.lastMessageTime > CONFIG.HEALTH_CHECK_INTERVAL * 2
            ) {
              staleSubscriptions++;
            }
          }
        });

        if (
          activeSubscriptions > 0 &&
          staleSubscriptions === activeSubscriptions
        ) {
          console.warn(
            '[PubSubService] All subscriptions appear stale, checking connection...',
          );
          this.emit('health_check_warning', {
            activeSubscriptions,
            staleSubscriptions,
          });
        }
      }
    }, CONFIG.HEALTH_CHECK_INTERVAL);
  }

  private stopHealthCheck() {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  }

  public async subscribe(
    topic: string,
    callback: PubSubSubscriptionCallback,
  ): Promise<void> {
    if (!this.client || !this.isConnected) {
      try {
        await this.initialize();
      } catch (error: unknown) {
        console.error(
          '[PubSubService] Failed to initialize before subscribing:',
          error,
        );
        throw error;
      }
    }

    // Check if already subscribed to this topic
    const existingSubscription = this.subscriptions.get(topic);
    if (existingSubscription) {
      // Add callback to existing subscription
      existingSubscription.callbacks.add(callback);
      console.log(
        `[PubSubService] Added callback to existing subscription for topic: ${topic}`,
      );

      // Don't send buffered messages automatically to prevent duplicates
      // Let the hook handle initial state if needed
      return;
    }

    try {
      const client = this.client!;
      const observableController = client.subscribe({
        topics: [topic],
      }) as MinimalAmplifyObservable;

      const callbacks = new Set<PubSubSubscriptionCallback>([callback]);
      const subscriptionInfo: SubscriptionInfo = {
        observableController,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        activeSubscription: null as any,
        callbacks,
        messageCount: 0,
        lastMessageTime: Date.now(),
        lastProcessedMessages: new Map<string, number>(),
      };

      const activeSubscription = observableController.subscribe({
        next: (data: unknown) => {
          try {
            const messageData = this.extractMessageData(
              data as PubSubMessageEnvelope,
            );

            if (messageData !== undefined) {
              // Create message hash for deduplication
              const messageHash = this.createMessageHash(topic, messageData);
              const now = Date.now();

              // Check for duplicates at global level
              if (this.globalProcessedMessages.has(messageHash)) {
                console.log(
                  `[PubSubService] Global duplicate detected for topic ${topic}: ${messageHash}`,
                );
                return;
              }

              // Check for duplicates at subscription level
              if (subscriptionInfo.lastProcessedMessages.has(messageHash)) {
                console.log(
                  `[PubSubService] Subscription duplicate detected for topic ${topic}: ${messageHash}`,
                );
                return;
              }

              // Record the message hash
              this.globalProcessedMessages.set(messageHash, now);
              subscriptionInfo.lastProcessedMessages.set(messageHash, now);

              subscriptionInfo.messageCount++;
              subscriptionInfo.lastMessageTime = now;

              // Buffer messages (with reduced buffer size)
              this.bufferMessage(topic, messageData);

              // Call all callbacks
              callbacks.forEach((cb) => {
                try {
                  cb(topic, messageData);
                } catch (callbackError) {
                  console.error(
                    `[PubSubService] Callback error for topic ${topic}:`,
                    callbackError,
                  );
                }
              });
            }
          } catch (error) {
            console.error(
              `[PubSubService] Error processing message for topic ${topic}:`,
              error,
            );
          }
        },
        error: (error: unknown) => {
          console.error(
            `[PubSubService] Subscription error for topic ${topic}:`,
            error,
          );
          const typedError =
            error instanceof Error ? error : new Error(String(error));
          this.emit('subscription_error', { topic, error: typedError });
          this.subscriptions.delete(topic);
          this.messageBuffer.delete(topic);
        },
        complete: () => {
          console.log(
            `[PubSubService] Subscription completed for topic: ${topic}`,
          );
          this.subscriptions.delete(topic);
          this.messageBuffer.delete(topic);
        },
      });

      subscriptionInfo.activeSubscription = activeSubscription;
      this.subscriptions.set(topic, subscriptionInfo);

      console.log(`[PubSubService] Successfully subscribed to topic: ${topic}`);
    } catch (error: unknown) {
      console.error(
        `[PubSubService] Failed to subscribe to topic ${topic}:`,
        error,
      );
      const typedError =
        error instanceof Error ? error : new Error(String(error));
      this.emit('error', typedError);
      throw typedError;
    }
  }

  public unsubscribe(
    topic: string,
    callback?: PubSubSubscriptionCallback,
  ): void {
    const subInfo = this.subscriptions.get(topic);
    if (!subInfo) {
      console.log(`[PubSubService] No subscription found for topic: ${topic}`);
      return;
    }

    try {
      if (callback) {
        subInfo.callbacks.delete(callback);

        if (subInfo.callbacks.size > 0) {
          console.log(
            `[PubSubService] Removed callback from topic ${topic}, ${subInfo.callbacks.size} callbacks remaining`,
          );
          return;
        }
      }

      // Unsubscribe completely
      if (
        subInfo.activeSubscription &&
        typeof subInfo.activeSubscription.unsubscribe === 'function'
      ) {
        subInfo.activeSubscription.unsubscribe();
      }

      this.subscriptions.delete(topic);
      this.messageBuffer.delete(topic);

      console.log(`[PubSubService] Unsubscribed from topic: ${topic}`);
    } catch (error: unknown) {
      console.error(
        `[PubSubService] Failed to unsubscribe from topic ${topic}:`,
        error,
      );
      const typedError =
        error instanceof Error ? error : new Error(String(error));
      this.emit('error', typedError);

      // Still attempt to clean up
      this.subscriptions.delete(topic);
      this.messageBuffer.delete(topic);
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public async publish(topic: string, data: any): Promise<void> {
    if (!this.client || !this.isConnected) {
      console.warn(
        '[PubSubService] Not connected. Attempting to initialize before publish...',
      );
      try {
        await this.initialize();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (initError: any) {
        console.error(
          '[PubSubService] Initialization failed during publish attempt:',
          initError,
        );
        throw new Error(
          `PubSub service is not connected: ${initError.message}`,
        );
      }
    }

    try {
      await this.client!.publish({
        topics: [topic],
        message: data,
      });

      console.log(`[PubSubService] Published message to topic: ${topic}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      console.error(
        `[PubSubService] Failed to publish to topic ${topic}:`,
        error,
      );
      const typedError =
        error instanceof Error ? error : new Error(String(error));
      this.emit('error', typedError);
      throw typedError;
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private extractMessageData(data: PubSubMessageEnvelope): any {
    // Extract message data from various envelope formats
    if (data?.value !== undefined) {
      if (data.value.data !== undefined) {
        return data.value.data;
      }
      return data.value;
    } else if (data?.data !== undefined) {
      return data.data;
    }
    return data;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private bufferMessage(topic: string, message: any) {
    let buffer = this.messageBuffer.get(topic);
    if (!buffer) {
      buffer = [];
      this.messageBuffer.set(topic, buffer);
    }

    buffer.push(message);

    // Keep only recent messages (reduced buffer size)
    if (buffer.length > CONFIG.MESSAGE_BUFFER_SIZE) {
      buffer.shift();
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public getBufferedMessages(topic: string): any[] {
    return this.messageBuffer.get(topic) || [];
  }

  public getSubscriptionStats() {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const stats: Record<string, any> = {};
    this.subscriptions.forEach((info, topic) => {
      stats[topic] = {
        callbackCount: info.callbacks.size,
        messageCount: info.messageCount,
        lastMessageTime: new Date(info.lastMessageTime).toISOString(),
        processedMessageCount: info.lastProcessedMessages.size,
      };
    });
    return {
      topics: stats,
      globalProcessedMessages: this.globalProcessedMessages.size,
    };
  }

  public cleanup(): void {
    console.log('[PubSubService] Cleaning up...');

    // Clear all timers
    this.clearConnectionTimeout();
    this.stopHealthCheck();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.messageHashCleanupTimer) {
      clearInterval(this.messageHashCleanupTimer);
      this.messageHashCleanupTimer = null;
    }

    // Unsubscribe all topics
    const topicsToUnsubscribe = Array.from(this.subscriptions.keys());
    for (const topic of topicsToUnsubscribe) {
      this.unsubscribe(topic);
    }

    // Clear buffers and processed messages
    this.messageBuffer.clear();
    this.globalProcessedMessages.clear();

    // Reset state
    this.isConnected = false;
    this.isInitializing = false;
    this.reconnectAttempts = 0;

    this.emit('disconnect');
    this.removeAllListeners();

    PubSubService.instance = null;
  }
}

export default PubSubService;
