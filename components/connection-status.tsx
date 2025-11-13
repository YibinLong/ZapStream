"use client"

import { useEffect, useState, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff, Server, Database, Zap, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { zapStreamAPI, isZapStreamAPIError } from "@/lib/api"

interface ServiceStatus {
  name: string
  status: "operational" | "degraded" | "down"
  latency?: number
  icon: typeof Server
}

export function ConnectionStatus() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "Backend API", status: "down", latency: undefined, icon: Server },
    { name: "Event Stream", status: "down", latency: undefined, icon: Zap },
    { name: "Database", status: "down", latency: undefined, icon: Database },
  ])

  const [isConnected, setIsConnected] = useState(false)
  const [currentTime, setCurrentTime] = useState<string>("")
  const [lastCheck, setLastCheck] = useState<string>("")
  const [error, setError] = useState<string | null>(null)

  // Health check function
  const checkHealth = useCallback(async () => {
    try {
      setError(null)
      const startTime = Date.now()

      // Check backend API health
      const healthResponse = await zapStreamAPI.healthCheck()
      const apiLatency = Date.now() - startTime

      // Test inbox endpoint
      const inboxStartTime = Date.now()
      await zapStreamAPI.getInboxEvents({ limit: 1 })
      const inboxLatency = Date.now() - inboxStartTime

      // Update services status
      const updatedServices: ServiceStatus[] = [
        {
          name: "Backend API",
          status: apiLatency < 1000 ? "operational" : apiLatency < 3000 ? "degraded" : "down",
          latency: apiLatency,
          icon: Server
        },
        {
          name: "Event Stream",
          status: inboxLatency < 500 ? "operational" : inboxLatency < 2000 ? "degraded" : "down",
          latency: inboxLatency,
          icon: Zap
        },
        {
          name: "Database",
          status: healthResponse.status === 'healthy' ? "operational" : "degraded",
          latency: undefined,
          icon: Database
        }
      ]

      setServices(updatedServices)
      setIsConnected(true)
      setLastCheck(new Date().toLocaleString())
    } catch (err) {
      if (isZapStreamAPIError(err)) {
        setError(err.message)
      } else {
        setError('Backend connection failed')
      }

      // Set all services as down on error
      setServices(prev => prev.map(service => ({ ...service, status: "down" as const, latency: undefined })))
      setIsConnected(false)
      setLastCheck(new Date().toLocaleString())
    }
  }, [])

  // Initialize current time and run first health check
  useEffect(() => {
    setCurrentTime(new Date().toLocaleTimeString())
    checkHealth()
  }, [checkHealth])

  // Real-time status updates
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString())
      checkHealth()
    }, 10000) // Check every 10 seconds

    return () => clearInterval(interval)
  }, [checkHealth])

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

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/30">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-destructive font-medium">Connection Error</p>
              <p className="text-xs text-destructive/80 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

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

      <div className={cn(
        "mt-6 p-4 rounded-lg border",
        isConnected
          ? "bg-success/5 border-success/20"
          : "bg-destructive/5 border-destructive/20"
      )}>
        <div className="flex items-start gap-3">
          <div className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full flex-shrink-0 mt-0.5",
            isConnected
              ? "bg-success/10"
              : "bg-destructive/10"
          )}>
            {isConnected ? (
              <Zap className="h-4 w-4 text-success" />
            ) : (
              <AlertCircle className="h-4 w-4 text-destructive" />
            )}
          </div>
          <div className="flex-1">
            <p className={cn(
              "text-sm font-medium mb-1",
              isConnected ? "text-success" : "text-destructive"
            )}>
              {isConnected ? "All systems operational" : "System degraded"}
            </p>
            <p className="text-xs text-muted-foreground">
              {"Last check: "}
              <span className="font-mono">{lastCheck || "Checking..."}</span>
            </p>
            <button
              onClick={checkHealth}
              className="text-xs text-accent hover:text-accent/80 mt-1 font-medium"
            >
              Check now →
            </button>
          </div>
        </div>
      </div>
    </Card>
  )
}
