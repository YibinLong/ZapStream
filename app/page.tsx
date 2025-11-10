import { NavHeader } from "@/components/nav-header"
import { StatCard } from "@/components/stat-card"
import { EventLog } from "@/components/event-log"
import { ApiPlayground } from "@/components/api-playground"
import { ConnectionStatus } from "@/components/connection-status"
import { Footer } from "@/components/footer"
import { Activity, Zap, Clock, TrendingUp } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <NavHeader />

      <main className="container px-6 py-8">
        {/* Hero Section */}
        <div className="mb-12 text-center animate-slide-up">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-balance bg-clip-text text-transparent bg-gradient-to-r from-primary via-accent to-primary">
            Real-time Event Management
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-balance">
            {"Monitor, manage, and deliver events at scale with enterprise-grade reliability"}
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Events Today"
            value="12,458"
            description="Total events processed"
            icon={Zap}
            trend={{ value: "12.5%", positive: true }}
            iconColor="text-primary"
          />
          <StatCard
            title="Active Triggers"
            value="247"
            description="Currently listening"
            icon={Activity}
            trend={{ value: "8.2%", positive: true }}
            iconColor="text-accent"
          />
          <StatCard
            title="Avg Response Time"
            value="45ms"
            description="Sub-100ms target"
            icon={Clock}
            trend={{ value: "5.1%", positive: true }}
            iconColor="text-success"
          />
          <StatCard
            title="Success Rate"
            value="99.9%"
            description="Delivery guarantee"
            icon={TrendingUp}
            iconColor="text-success"
          />
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="dashboard" className="w-full">
          <TabsList className="grid w-full max-w-md mx-auto grid-cols-2 mb-8">
            <TabsTrigger value="dashboard" className="gap-2">
              <Activity className="h-4 w-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="playground" className="gap-2">
              <Zap className="h-4 w-4" />
              Playground
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3">
                <EventLog />
              </div>
              <div className="lg:col-span-1">
                <ConnectionStatus />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="playground">
            <ApiPlayground />
          </TabsContent>
        </Tabs>
      </main>

      <Footer />
    </div>
  )
}
