/**
 * WebSocket Hook for Real-time Warehouse Updates
 *
 * Provides real-time connection to warehouse events
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export type EventType =
  | 'temperature_update'
  | 'inventory_movement'
  | 'alert_triggered'
  | 'shelf_update'
  | 'medication_expiry'
  | 'capacity_warning';

export interface WebSocketMessage {
  type: EventType | 'connection_established' | 'error' | 'pong';
  data?: any;
  timestamp?: string;
  message?: string;
}

export interface UseWarehouseWebSocketOptions {
  clientId: string;
  subscriptions?: string[];
  autoReconnect?: boolean;
  reconnectInterval?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export interface WebSocketState {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export function useWarehouseWebSocket({
  clientId,
  subscriptions = ['all'],
  autoReconnect = true,
  reconnectInterval = 5000,
  onMessage,
  onConnect,
  onDisconnect,
  onError
}: UseWarehouseWebSocketOptions) {
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    lastMessage: null,
    connectionStatus: 'disconnected'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState(prev => ({ ...prev, connectionStatus: 'connecting' }));

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const subscriptionParams = subscriptions.join(',');
    const wsUrl = `${protocol}//${host}/ws/warehouse?client_id=${clientId}&subscriptions=${subscriptionParams}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({
          ...prev,
          isConnected: true,
          connectionStatus: 'connected'
        }));

        // Start ping interval to keep connection alive
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'ping',
              timestamp: new Date().toISOString()
            }));
          }
        }, 30000); // Ping every 30 seconds

        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          setState(prev => ({
            ...prev,
            lastMessage: message
          }));

          // Don't trigger callback for pong messages
          if (message.type !== 'pong') {
            onMessage?.(message);
          }

          // Handle specific message types
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({
          ...prev,
          connectionStatus: 'error'
        }));
        onError?.(new Error('WebSocket connection error'));
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setState(prev => ({
          ...prev,
          isConnected: false,
          connectionStatus: 'disconnected'
        }));

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        onDisconnect?.();

        // Auto-reconnect if enabled
        if (autoReconnect && !reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, reconnectInterval);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setState(prev => ({
        ...prev,
        connectionStatus: 'error'
      }));
      onError?.(error as Error);
    }
  }, [clientId, subscriptions, autoReconnect, reconnectInterval, onConnect, onDisconnect, onError, onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  const subscribe = useCallback((channels: string[]) => {
    sendMessage({
      type: 'subscribe',
      channels
    });
  }, [sendMessage]);

  const unsubscribe = useCallback((channels: string[]) => {
    sendMessage({
      type: 'unsubscribe',
      channels
    });
  }, [sendMessage]);

  const handleMessage = (message: WebSocketMessage) => {
    // Handle specific message types with custom logic
    switch (message.type) {
      case 'temperature_update':
        console.log('Temperature update received:', message.data);
        break;

      case 'inventory_movement':
        console.log('Inventory movement:', message.data);
        break;

      case 'alert_triggered':
        console.warn('Alert triggered:', message.data);
        break;

      case 'shelf_update':
        console.log('Shelf update:', message.data);
        break;

      case 'medication_expiry':
        console.warn('Medication expiry warning:', message.data);
        break;

      case 'capacity_warning':
        console.warn('Capacity warning:', message.data);
        break;

      default:
        break;
    }
  };

  // Connect on mount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, []); // Empty dependency array for mount only

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe
  };
}

// Example usage in a component:
/*
function WarehouseMonitor() {
  const { isConnected, lastMessage, connectionStatus } = useWarehouseWebSocket({
    clientId: 'warehouse-monitor-1',
    subscriptions: ['temperature', 'alerts'],
    onMessage: (message) => {
      // Handle incoming messages
      if (message.type === 'alert_triggered') {
        showNotification(message.data.message);
      }
    },
    onConnect: () => {
      console.log('Connected to warehouse WebSocket');
    },
    onDisconnect: () => {
      console.log('Disconnected from warehouse WebSocket');
    }
  });

  return (
    <div>
      <div>Connection Status: {connectionStatus}</div>
      {lastMessage && (
        <div>Last Update: {lastMessage.type} at {lastMessage.timestamp}</div>
      )}
    </div>
  );
}
*/