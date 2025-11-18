"use client"

import { useEffect, useState, useCallback } from "react"
import { StatCard } from "@/components/stat-card"
import { Zap, Activity, Clock, TrendingUp } from "lucide-react"
import { zapStreamAPI, ZapStreamEvent, isZapStreamAPIError } from "@/lib/api"

interface LiveStatsData {
  eventsToday: number
  totalEvents: number
  pendingEvents: number
  acknowledgedEvents: number
  uniqueSources: number
  lastUpdated?: string
}

const initialStats: LiveStatsData = {
  eventsToday: 0,
  totalEvents: 0,
  pendingEvents: 0,
  acknowledgedEvents: 0,
  uniqueSources: 0,
}

export function LiveStats() {
  const [stats, setStats] = useState<LiveStatsData>(initialStats)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      setError(null)
      const response = await zapStreamAPI.getInboxEvents({ limit: 50 })
      const events = response.events as ZapStreamEvent[]
      const today = new Date().toISOString().split("T")[0]

      const eventsToday = events.filter((event) => event.created_at.startsWith(today)).length
      const pendingEvents = events.filter((event) => event.status === "pending").length
      const acknowledgedEvents = events.filter((event) => event.status === "acknowledged").length
      const uniqueSources = new Set(events.map((event) => event.source || "unknown")).size

      setStats({
        eventsToday,
        totalEvents: events.length,
        pendingEvents,
        acknowledgedEvents,
        uniqueSources,
        lastUpdated: new Date().toISOString(),
      })
    } catch (err) {
      setError(isZapStreamAPIError(err) ? err.message : "Failed to load stats")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [fetchStats])

  const formatValue = (value: number) => (loading ? "—" : value.toLocaleString())
  const ackRate = stats.totalEvents ? Math.round((stats.acknowledgedEvents / stats.totalEvents) * 100) : 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <StatCard
        title="Events Today"
        value={formatValue(stats.eventsToday)}
        description={error ? error : "Events received since midnight"}
        icon={Zap}
        iconColor="text-primary"
      />
      <StatCard
        title="Pending Events"
        value={formatValue(stats.pendingEvents)}
        description="Awaiting acknowledgment"
        icon={Clock}
        iconColor="text-warning"
      />
      <StatCard
        title="Acknowledged Rate"
        value={loading ? "—" : `${ackRate}%`}
        description={`${stats.acknowledgedEvents.toLocaleString()} acknowledged`}
        icon={TrendingUp}
        iconColor="text-success"
      />
      <StatCard
        title="Active Sources"
        value={formatValue(stats.uniqueSources)}
        description="Unique event sources observed"
        icon={Activity}
        iconColor="text-accent"
      />
    </div>
  )
}
