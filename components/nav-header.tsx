"use client"

import { Activity, Zap } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export function NavHeader() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="w-full max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent">
            <Zap className="h-5 w-5 text-white" fill="white" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-lg font-bold leading-none text-balance">Zapier Triggers API</h1>
            <p className="text-xs text-muted-foreground">Real-time Event Platform</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-2 border-success/30 bg-success/10 text-success px-3 py-1">
            <Activity className="h-3 w-3 animate-pulse-glow" />
            <span className="text-xs font-medium whitespace-nowrap">API Online</span>
          </Badge>
        </div>
      </div>
    </header>
  )
}
