/**
 * ZapStream Backend API Client
 *
 * Handles all communication with the ZapStream backend API including:
 * - Event ingestion and retrieval
 * - Real-time event streaming via Server-Sent Events
 * - Event acknowledgment and deletion
 * - Error handling and retries
 */

export interface ZapStreamEvent {
  id: string;
  created_at: string;
  source?: string;
  type?: string;
  topic?: string;
  payload: Record<string, any>;
  status?: 'pending' | 'acknowledged' | 'deleted';
  delivered?: boolean;
}

export interface InboxResponse {
  events: ZapStreamEvent[];
  next_cursor?: string;
}

export interface EventSubmissionResponse {
  id: string;
  receivedAt: string;
  status: string;
}

export interface AcknowledgeResponse {
  id: string;
  status: string;
}

export interface DeleteResponse {
  id: string;
  status: string;
}

export interface EventSubmission {
  source?: string;
  type?: string;
  topic?: string;
  payload: Record<string, any>;
}

export interface InboxParams {
  limit?: number;
  since?: string;
  topic?: string;
  type?: string;
  cursor?: string;
}

class ZapStreamAPIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public requestId?: string
  ) {
    super(message);
    this.name = 'ZapStreamAPIError';
  }
}

class ZapStreamAPIClient {
  private baseURL: string;
  private apiKey: string;

  constructor() {
    this.baseURL =
      process.env.NEXT_PUBLIC_ZAPSTREAM_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    this.apiKey = process.env.NEXT_PUBLIC_ZAPSTREAM_API_KEY || 'dev_key_123';
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.apiKey}`,
      'X-API-Key': this.apiKey,
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorMessage = 'API request failed';
        let errorCode: string | undefined;
        let requestId: string | undefined;

        try {
          const errorData = await response.json();
          errorMessage = errorData?.error?.message || errorMessage;
          errorCode = errorData?.error?.code;
          requestId = errorData?.error?.requestId;
        } catch {
          // If we can't parse the error response, use status text
          errorMessage = response.statusText || errorMessage;
        }

        throw new ZapStreamAPIError(
          errorMessage,
          response.status,
          errorCode,
          requestId
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ZapStreamAPIError) {
        throw error;
      }

      // Handle network errors, timeouts, etc.
      throw new ZapStreamAPIError(
        error instanceof Error ? error.message : 'Network error',
        0,
        'NETWORK_ERROR'
      );
    }
  }

  // Event Management
  async submitEvent(event: EventSubmission, idempotencyKey?: string): Promise<EventSubmissionResponse> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['X-Idempotency-Key'] = idempotencyKey;
    }

    return this.request<EventSubmissionResponse>('/events', {
      method: 'POST',
      body: JSON.stringify(event),
      headers,
    });
  }

  async getInboxEvents(params: InboxParams = {}): Promise<InboxResponse> {
    const searchParams = new URLSearchParams();

    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.since) searchParams.append('since', params.since);
    if (params.topic) searchParams.append('topic', params.topic);
    if (params.type) searchParams.append('type', params.type);
    if (params.cursor) searchParams.append('cursor', params.cursor);

    const query = searchParams.toString();
    const endpoint = `/inbox${query ? `?${query}` : ''}`;

    return this.request<InboxResponse>(endpoint);
  }

  async acknowledgeEvent(eventId: string): Promise<AcknowledgeResponse> {
    return this.request<AcknowledgeResponse>(`/inbox/${eventId}/ack`, {
      method: 'POST',
    });
  }

  async deleteEvent(eventId: string): Promise<DeleteResponse> {
    return this.request<DeleteResponse>(`/inbox/${eventId}`, {
      method: 'DELETE',
    });
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>('/health');
  }

  // Server-Sent Events for real-time updates
  createEventStream(
    onEvent: (event: ZapStreamEvent) => void,
    onError?: (error: Error) => void,
    onConnectionChange?: (connected: boolean) => void
  ): EventSource | null {
    // Server-Sent Events are not supported in all environments
    if (typeof EventSource === 'undefined') {
      return null;
    }

    const streamURL = `${this.baseURL}/inbox/stream`;

    // For EventSource, we need to pass the API key via query parameter
    // since EventSource doesn't support custom headers
    const url = new URL(streamURL);
    url.searchParams.append('api_key', this.apiKey);
    url.searchParams.append('tenant_id', 'tenant_dev'); // Add tenant_id for SSE

    const eventSource = new EventSource(url.toString());

    eventSource.onopen = () => {
      onConnectionChange?.(true);
    };

    eventSource.onmessage = (event) => {
      try {
        if (event.data === ': heartbeat') {
          // Heartbeat message, ignore
          return;
        }

        const eventData = JSON.parse(event.data);

        if (eventData.type === 'error') {
          onError?.(new Error(eventData.message));
          return;
        }

        onEvent(eventData);
      } catch (error) {
        console.error('Error parsing SSE event:', error);
        onError?.(new Error('Failed to parse event data'));
      }
    };

    eventSource.onerror = () => {
      onConnectionChange?.(false);
      onError?.(new Error('Event stream connection lost'));
    };

    return eventSource;
  }
}

// Create a singleton instance
export const zapStreamAPI = new ZapStreamAPIClient();

// Export types and error class
export { ZapStreamAPIError };

// Utility functions for frontend use
export const createZapStreamEvent = (
  payload: Record<string, any>,
  options: Partial<EventSubmission> = {}
): EventSubmission => ({
  payload,
  ...options,
});

export const isZapStreamAPIError = (error: unknown): error is ZapStreamAPIError => {
  return error instanceof ZapStreamAPIError;
};
