"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CheckCircle2, Clock, XCircle, ChevronRight, Filter } from "lucide-react"
import { cn } from "@/lib/utils"

interface Event {
  id: string
  timestamp: string
  status: "delivered" | "pending" | "failed"
  payload: Record<string, unknown>
  source?: string
}

const mockEvents: Event[] = [
  {
    id: "evt_9k2m4n5p",
    timestamp: new Date(Date.now() - 2000).toISOString(),
    status: "delivered",
    payload: { user_id: "usr_123", action: "login", ip: "192.168.1.1" },
    source: "auth-service",
  },
  {
    id: "evt_8j1l3m4n",
    timestamp: new Date(Date.now() - 45000).toISOString(),
    status: "delivered",
    payload: { order_id: "ord_456", total: 299.99, items: 3 },
    source: "checkout-api",
  },
  {
    id: "evt_7h0k2l3m",
    timestamp: new Date(Date.now() - 120000).toISOString(),
    status: "pending",
    payload: { webhook_url: "https://example.com/webhook", retry_count: 2 },
    source: "webhook-processor",
  },
  {
    id: "evt_6g9j1k2l",
    timestamp: new Date(Date.now() - 180000).toISOString(),
    status: "failed",
    payload: { error: "Connection timeout", endpoint: "/api/notify" },
    source: "notification-service",
  },
  {
    id: "evt_5f8i0j1k",
    timestamp: new Date(Date.now() - 240000).toISOString(),
    status: "delivered",
    payload: { email: "user@example.com", template: "welcome", sent: true },
    source: "email-service",
  },
]

const statusConfig = {
  delivered: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/10",
    border: "border-success/30",
    label: "Delivered",
  },
  pending: {
    icon: Clock,
    color: "text-warning",
    bg: "bg-warning/10",
    border: "border-warning/30",
    label: "Pending",
  },
  failed: {
    icon: XCircle,
    color: "text-destructive",
    bg: "bg-destructive/10",
    border: "border-destructive/30",
    label: "Failed",
  },
}

export function EventLog() {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [events] = useState<Event[]>(mockEvents)

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return date.toLocaleDateString()
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-balance">Event Stream</h2>
          <p className="text-sm text-muted-foreground mt-1">Real-time event monitoring</p>
        </div>
        <Button variant="outline" size="sm" className="gap-2 bg-transparent">
          <Filter className="h-4 w-4" />
          Filter
        </Button>
      </div>

      <ScrollArea className="h-[600px] pr-4">
        <div className="space-y-3">
          {events.map((event, index) => {
            const config = statusConfig[event.status]
            const Icon = config.icon
            const isSelected = selectedEvent?.id === event.id

            return (
              <button
                key={event.id}
                onClick={() => setSelectedEvent(event)}
                style={{ animationDelay: `${index * 50}ms` }}
                className={cn(
                  "w-full text-left p-4 rounded-lg border transition-all duration-200 hover:shadow-md group animate-slide-up",
                  isSelected
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border bg-card hover:border-primary/40",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", config.bg)}>
                      <Icon className={cn("h-4 w-4", config.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-mono text-sm font-medium">{event.id}</p>
                        <Badge variant="outline" className={cn("text-xs", config.border, config.bg)}>
                          {config.label}
                        </Badge>
                      </div>
                      {event.source && <p className="text-xs text-muted-foreground mb-2">{event.source}</p>}
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

                {isSelected && (
                  <div className="mt-4 pt-4 border-t border-border animate-slide-up">
                    <div className="space-y-3">
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
                    </div>
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </ScrollArea>
    </Card>
  )
}
