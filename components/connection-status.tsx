"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff, Server, Database, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

interface ServiceStatus {
  name: string
  status: "operational" | "degraded" | "down"
  latency?: number
  icon: typeof Server
}

export function ConnectionStatus() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "API Gateway", status: "operational", latency: 45, icon: Server },
    { name: "Event Queue", status: "operational", latency: 12, icon: Zap },
    { name: "Database", status: "operational", latency: 8, icon: Database },
  ])

  const [isConnected, setIsConnected] = useState(true)
  const [currentTime, setCurrentTime] = useState<string>("")

  // Initialize current time on client side only
  useEffect(() => {
    setCurrentTime(new Date().toLocaleTimeString())
  }, [])

  // Simulate real-time status updates
  useEffect(() => {
    const interval = setInterval(() => {
      setServices((prev) =>
        prev.map((service) => ({
          ...service,
          latency: service.latency ? Math.floor(service.latency + (Math.random() - 0.5) * 10) : undefined,
        })),
      )
      setCurrentTime(new Date().toLocaleTimeString())
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const statusConfig = {
    operational: {
      color: "text-success",
      bg: "bg-success/10",
      border: "border-success/30",
      label: "Operational",
    },
    degraded: {
      color: "text-warning",
      bg: "bg-warning/10",
      border: "border-warning/30",
      label: "Degraded",
    },
    down: {
      color: "text-destructive",
      bg: "bg-destructive/10",
      border: "border-destructive/30",
      label: "Down",
    },
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-balance">System Status</h3>
        <Badge
          className={cn(
            "gap-2",
            isConnected
              ? "bg-success/10 text-success border-success/30"
              : "bg-destructive/10 text-destructive border-destructive/30",
          )}
        >
          {isConnected ? (
            <>
              <Wifi className="h-3 w-3 animate-pulse-glow" />
              Connected
            </>
          ) : (
            <>
              <WifiOff className="h-3 w-3" />
              Disconnected
            </>
          )}
        </Badge>
      </div>

      <div className="space-y-4">
        {services.map((service) => {
          const config = statusConfig[service.status]
          const Icon = service.icon

          return (
            <div
              key={service.name}
              className="flex items-center justify-between p-4 rounded-lg border border-border hover:border-primary/40 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", config.bg)}>
                  <Icon className={cn("h-5 w-5", config.color)} />
                </div>
                <div>
                  <p className="font-medium text-sm">{service.name}</p>
                  {service.latency && <p className="text-xs text-muted-foreground">{service.latency}ms latency</p>}
                </div>
              </div>
              <Badge variant="outline" className={cn("text-xs", config.border, config.bg)}>
                {config.label}
              </Badge>
            </div>
          )
        })}
      </div>

      <div className="mt-6 p-4 rounded-lg bg-muted/50 border border-border">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 flex-shrink-0 mt-0.5">
            <Zap className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium mb-1">All systems operational</p>
            <p className="text-xs text-muted-foreground">
              {"Last updated: "}
              <span className="font-mono">{currentTime || "Loading..."}</span>
            </p>
          </div>
        </div>
      </div>
    </Card>
  )
}
