"use client"

import { useState, useEffect, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CheckCircle2, Clock, XCircle, ChevronRight, Filter, RefreshCw, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { zapStreamAPI, ZapStreamEvent, isZapStreamAPIError } from "@/lib/api"

// Event interface matching the backend API
interface Event extends ZapStreamEvent {
  timestamp: string // Alias for created_at to match existing UI
}

// Status configuration updated to match backend statuses
const statusConfig = {
  acknowledged: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/10",
    border: "border-success/30",
    label: "Acknowledged",
  },
  pending: {
    icon: Clock,
    color: "text-warning",
    bg: "bg-warning/10",
    border: "border-warning/30",
    label: "Pending",
  },
  deleted: {
    icon: XCircle,
    color: "text-destructive",
    bg: "bg-destructive/10",
    border: "border-destructive/30",
    label: "Deleted",
  },
}

export function EventLog() {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Convert backend event to frontend format
  const convertEvent = (backendEvent: ZapStreamEvent): Event => ({
    ...backendEvent,
    timestamp: backendEvent.created_at,
    status: backendEvent.status || 'pending',
  })

  // Fetch events from API
  const fetchEvents = useCallback(async () => {
    try {
      setError(null)
      const response = await zapStreamAPI.getInboxEvents({ limit: 50 })
      const convertedEvents = response.events.map(convertEvent)
      // Sort by created_at DESC (newest first)
      convertedEvents.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      setEvents(convertedEvents)
    } catch (err) {
      if (isZapStreamAPIError(err)) {
        setError(err.message)
      } else {
        setError('Failed to fetch events')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Set up Server-Sent Events for real-time updates
  useEffect(() => {
    fetchEvents()

    const eventSource = zapStreamAPI.createEventStream(
      (newEvent) => {
        const convertedEvent = convertEvent(newEvent)
        setEvents(prev => [convertedEvent, ...prev].slice(0, 100)) // Keep last 100 events
      },
      (err) => {
        console.error('Event stream error:', err)
        setIsConnected(false)
      },
      (connected) => {
        setIsConnected(connected)
      }
    )

    return () => {
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [fetchEvents])

  // Refetch events when component becomes visible (e.g., switching tabs)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Tab became visible, refetch events
        fetchEvents()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [fetchEvents])

  // Handle event actions
  const handleAcknowledge = async (eventId: string) => {
    try {
      await zapStreamAPI.acknowledgeEvent(eventId)
      setEvents(prev =>
        prev.map(event =>
          event.id === eventId
            ? { ...event, status: 'acknowledged', delivered: true }
            : event
        )
      )
    } catch (err) {
      if (isZapStreamAPIError(err)) {
        setError(err.message)
      } else {
        setError('Failed to acknowledge event')
      }
    }
  }

  const handleDelete = async (eventId: string) => {
    try {
      await zapStreamAPI.deleteEvent(eventId)
      setEvents(prev => prev.filter(event => event.id !== eventId))
      if (selectedEvent?.id === eventId) {
        setSelectedEvent(null)
      }
    } catch (err) {
      if (isZapStreamAPIError(err)) {
        setError(err.message)
      } else {
        setError('Failed to delete event')
      }
    }
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

    // Handle future timestamps (shouldn't happen but just in case)
    if (diff < 0) return 'just now'
    
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return date.toLocaleDateString()
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-balance">Event Stream</h2>
            {isConnected ? (
              <div className="flex items-center gap-1 text-xs text-success">
                <div className="h-2 w-2 bg-success rounded-full animate-pulse"></div>
                Live
              </div>
            ) : (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <div className="h-2 w-2 bg-muted rounded-full"></div>
                Offline
              </div>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {isLoading ? "Loading events..." : `Real-time event monitoring (${events.length} events)`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {error && (
            <div className="flex items-center gap-1 text-xs text-destructive">
              <AlertCircle className="h-3 w-3" />
              {error}
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            className="gap-2 bg-transparent"
            onClick={fetchEvents}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      <ScrollArea className="h-[600px] pr-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="flex items-center gap-2 text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Loading events...
            </div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <AlertCircle className="h-8 w-8 text-destructive mb-2" />
            <p className="text-sm text-destructive mb-2">Failed to load events</p>
            <Button variant="outline" size="sm" onClick={fetchEvents}>
              Try Again
            </Button>
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <div className="h-8 w-8 bg-muted rounded-full flex items-center justify-center mb-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">No events found</p>
            <p className="text-xs text-muted-foreground mt-1">New events will appear here automatically</p>
          </div>
        ) : (
          <div className="space-y-3">
          {events.map((event, index) => {
            const config = statusConfig[event.status || 'pending']
            const Icon = config.icon
            const isSelected = selectedEvent?.id === event.id

            return (
              <div
                key={event.id}
                style={{ animationDelay: `${index * 50}ms` }}
                className={cn(
                  "w-full text-left p-4 rounded-lg border transition-all duration-200 hover:shadow-md group animate-slide-up",
                  isSelected
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border bg-card hover:border-primary/40",
                )}
              >
                <button
                  onClick={() => setSelectedEvent(isSelected ? null : event)}
                  className="w-full text-left"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", config.bg)}>
                        <Icon className={cn("h-4 w-4", config.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-sm font-semibold">{event.source || 'Unknown Source'}</p>
                          <Badge variant="outline" className={cn("text-xs", config.border, config.bg)}>
                            {config.label}
                          </Badge>
                        </div>
                        {event.type && <p className="text-xs text-muted-foreground mb-1">{event.type}</p>}
                        <p className="text-xs text-muted-foreground font-mono truncate">
                          {JSON.stringify(event.payload).substring(0, 80)}...
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTime(event.timestamp)}
                      </span>
                      <ChevronRight
                        className={cn("h-4 w-4 text-muted-foreground transition-transform", isSelected && "rotate-90")}
                      />
                    </div>
                  </div>
                </button>

                {isSelected && (
                  <div className="mt-4 pt-4 border-t border-border animate-slide-up">
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Event ID
                        </label>
                        <p className="text-xs font-mono mt-1">{event.id}</p>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Timestamp
                        </label>
                        <p className="text-sm mt-1">{new Date(event.timestamp).toLocaleString()}</p>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Full Payload
                        </label>
                        <pre className="text-xs font-mono mt-2 p-3 bg-muted rounded-md overflow-x-auto">
                          {JSON.stringify(event.payload, null, 2)}
                        </pre>
                      </div>
                      {event.status === 'pending' && (
                        <div className="flex gap-2">
                          <button
                            className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-8 rounded-md px-3"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleAcknowledge(event.id)
                            }}
                          >
                            <CheckCircle2 className="h-3 w-3" />
                            Acknowledge
                          </button>
                          <button
                            className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-8 rounded-md px-3 text-destructive hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDelete(event.id)
                            }}
                          >
                            <XCircle className="h-3 w-3" />
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
      </ScrollArea>
    </Card>
  )
}