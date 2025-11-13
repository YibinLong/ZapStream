"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Copy, Play, CheckCircle2, Code2, Terminal, ArrowRight, Zap, Inbox, Trash2, Clock } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { zapStreamAPI, isZapStreamAPIError } from "@/lib/api"
import { cn } from "@/lib/utils"

// Request history interface
interface RequestDetails {
  method: string
  endpoint: string
  payload: string
  status: number
  statusText: string
  response: string
  timestamp: string
  headers: Record<string, string>
}

export function ApiPlayground() {
  const { toast } = useToast()
  const [endpoint, setEndpoint] = useState("/events")
  const [method, setMethod] = useState("POST")
  const [payload, setPayload] = useState(
    JSON.stringify(
      {
        source: "playground",
        type: "test.event",
        topic: "testing",
        payload: {
          message: "Testing from API Playground",
          timestamp: new Date().toISOString()
        }
      },
      null,
      2,
    ),
  )
  const [response, setResponse] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)
  const [lastRequest, setLastRequest] = useState<RequestDetails | null>(null)

  const handleSendRequest = async () => {
    setIsLoading(true)
    
    try {
      let result: any
      let statusCode = 200
      let statusText = "OK"
      
      // Route to appropriate API method based on endpoint and method
      if (endpoint === "/events" && method === "POST") {
        const eventData = JSON.parse(payload)
        result = await zapStreamAPI.submitEvent(eventData)
        statusCode = 201
        statusText = "Created"
      } else if (endpoint.startsWith("/inbox/") && endpoint.endsWith("/ack") && method === "POST") {
        const eventId = endpoint.split("/")[2]
        result = await zapStreamAPI.acknowledgeEvent(eventId)
      } else if (endpoint.startsWith("/inbox/") && method === "DELETE") {
        const eventId = endpoint.split("/")[2]
        result = await zapStreamAPI.deleteEvent(eventId)
      } else if (endpoint.startsWith("/inbox") && method === "GET") {
        const params: any = {}
        if (payload.trim()) {
          const queryParams = JSON.parse(payload)
          Object.assign(params, queryParams)
        }
        result = await zapStreamAPI.getInboxEvents(params)
      } else if (endpoint === "/health" && method === "GET") {
        result = await zapStreamAPI.healthCheck()
      } else {
        throw new Error(`Unsupported endpoint/method combination`)
      }

      const responseJson = JSON.stringify(result, null, 2)
      setResponse(responseJson)

      // Store request details
      setLastRequest({
        method,
        endpoint,
        payload: payload || "(empty)",
        status: statusCode,
        statusText,
        response: responseJson,
        timestamp: new Date().toISOString(),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer dev_key_123",
        }
      })

      toast({
        title: "✅ Request successful",
        description: `${method} ${endpoint} - ${statusCode} ${statusText}`,
      })
    } catch (err) {
      const errorMessage = isZapStreamAPIError(err) ? err.message : "Request failed"
      const errorJson = JSON.stringify({ error: errorMessage }, null, 2)
      setResponse(errorJson)

      // Store error request details
      setLastRequest({
        method,
        endpoint,
        payload: payload || "(empty)",
        status: isZapStreamAPIError(err) ? err.status : 500,
        statusText: "Error",
        response: errorJson,
        timestamp: new Date().toISOString(),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer dev_key_123",
        }
      })

      toast({
        title: "❌ Request failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copied!",
      description: "Command copied to clipboard",
    })
  }

  // Load command into playground
  const loadCommand = (cmd: { method: string; endpoint: string; payload?: string; description: string }) => {
    setMethod(cmd.method)
    setEndpoint(cmd.endpoint)
    setPayload(cmd.payload || "")
    toast({
      title: "Loaded!",
      description: cmd.description,
    })
  }

  // Command examples organized by action
  const commands = {
    create: {
      method: "POST",
      endpoint: "/events",
      payload: JSON.stringify({
        source: "billing",
        type: "invoice.paid",
        topic: "finance",
        payload: { invoiceId: "inv_123", amount: 4200 }
      }, null, 2),
      description: "Create a new event",
      curl: `curl -X POST http://localhost:8000/events \\
  -H "Authorization: Bearer dev_key_123" \\
  -H "Content-Type: application/json" \\
  -d '{
    "source": "billing",
    "type": "invoice.paid", 
    "topic": "finance",
    "payload": {"invoiceId": "inv_123", "amount": 4200}
  }'`
    },
    list: {
      method: "GET",
      endpoint: "/inbox",
      payload: JSON.stringify({ limit: 10, topic: "finance" }, null, 2),
      description: "List inbox events",
      curl: `curl "http://localhost:8000/inbox?limit=10&topic=finance" \\
  -H "Authorization: Bearer dev_key_123"`
    },
    acknowledge: {
      method: "POST",
      endpoint: "/inbox/{event_id}/ack",
      payload: "",
      description: "Acknowledge an event (replace {event_id})",
      curl: `curl -X POST "http://localhost:8000/inbox/{event_id}/ack" \\
  -H "Authorization: Bearer dev_key_123"`
    },
    delete: {
      method: "DELETE",
      endpoint: "/inbox/{event_id}",
      payload: "",
      description: "Delete an event (replace {event_id})",
      curl: `curl -X DELETE "http://localhost:8000/inbox/{event_id}" \\
  -H "Authorization: Bearer dev_key_123"`
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Request Builder */}
      <div className="space-y-6">
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <Terminal className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold text-balance">API Playground</h2>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-2">
              <div className="col-span-1">
                <Label htmlFor="method" className="text-sm font-medium mb-2">
                  Method
                </Label>
                <select
                  id="method"
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="POST">POST</option>
                  <option value="GET">GET</option>
                  <option value="DELETE">DELETE</option>
                </select>
              </div>
              <div className="col-span-3">
                <Label htmlFor="endpoint" className="text-sm font-medium mb-2">
                  Endpoint
                </Label>
                <Input
                  id="endpoint"
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  className="font-mono text-sm"
                  placeholder="/events or /inbox"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="payload" className="text-sm font-medium mb-2">
                Request Body {method === "GET" && "(JSON query params)"}
              </Label>
              <Textarea
                id="payload"
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                className="font-mono text-sm min-h-[200px]"
                placeholder={method === "GET" ? '{"limit": 10, "topic": "finance"}' : "Enter JSON payload..."}
              />
            </div>

            <Button
              onClick={handleSendRequest}
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary/90 gap-2"
              size="lg"
            >
              {isLoading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Sending...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Send Request
                </>
              )}
            </Button>
          </div>
        </Card>

        {/* Response */}
        {response && (
          <Card className="p-6 animate-slide-up">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold flex items-center gap-2 text-balance">
                <CheckCircle2 className="h-5 w-5 text-success" />
                Response
              </h3>
              <Badge className={cn(
                lastRequest?.status && lastRequest.status >= 200 && lastRequest.status < 300
                  ? "bg-success/10 text-success border-success/30"
                  : "bg-destructive/10 text-destructive border-destructive/30"
              )}>
                {lastRequest?.status} {lastRequest?.statusText}
              </Badge>
            </div>
            <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto">{response}</pre>
          </Card>
        )}

        {/* Request Inspector */}
        {lastRequest && (
          <Card className="p-6 animate-slide-up">
            <div className="flex items-center gap-2 mb-4">
              <Code2 className="h-5 w-5 text-accent" />
              <h3 className="text-lg font-bold text-balance">Last Request</h3>
              <Badge variant="outline" className="text-xs ml-auto">
                {new Date(lastRequest.timestamp).toLocaleTimeString()}
              </Badge>
            </div>
            
            <div className="space-y-3 text-sm">
              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Request
                </label>
                <div className="mt-1 p-3 bg-muted rounded-md font-mono text-xs">
                  <Badge variant="outline" className="mr-2">{lastRequest.method}</Badge>
                  {lastRequest.endpoint}
                </div>
              </div>

              {lastRequest.payload && lastRequest.payload !== "(empty)" && (
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Payload
                  </label>
                  <pre className="mt-1 p-3 bg-muted rounded-md font-mono text-xs overflow-x-auto">
                    {lastRequest.payload}
                  </pre>
                </div>
              )}

              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Headers
                </label>
                <div className="mt-1 p-3 bg-muted rounded-md font-mono text-xs space-y-1">
                  {Object.entries(lastRequest.headers).map(([key, value]) => (
                    <div key={key}>
                      <span className="text-accent">{key}:</span> {value}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Status
                </label>
                <div className="mt-1 p-3 bg-muted rounded-md">
                  <Badge className={cn(
                    lastRequest.status >= 200 && lastRequest.status < 300
                      ? "bg-success/10 text-success border-success/30"
                      : "bg-destructive/10 text-destructive border-destructive/30"
                  )}>
                    {lastRequest.status} {lastRequest.statusText}
                  </Badge>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Command Examples */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <Code2 className="h-5 w-5 text-accent" />
          <h2 className="text-2xl font-bold text-balance">Quick Commands</h2>
        </div>

        <Tabs defaultValue="create" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="create" className="text-xs">
              <Zap className="h-3 w-3 mr-1" />
              Create
            </TabsTrigger>
            <TabsTrigger value="list" className="text-xs">
              <Inbox className="h-3 w-3 mr-1" />
              List
            </TabsTrigger>
            <TabsTrigger value="acknowledge" className="text-xs">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Ack
            </TabsTrigger>
            <TabsTrigger value="delete" className="text-xs">
              <Trash2 className="h-3 w-3 mr-1" />
              Delete
            </TabsTrigger>
          </TabsList>

          <TabsContent value="create" className="mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">Create Event</h4>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-2 text-xs"
                  onClick={() => loadCommand(commands.create)}
                >
                  <ArrowRight className="h-3 w-3" />
                  Load in Playground
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Send a new event to the backend. Events are queued and delivered to subscribers.
              </p>
              <div className="relative">
                <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto whitespace-pre-wrap">
                  {commands.create.curl}
                </pre>
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute top-2 right-2"
                  onClick={() => copyToClipboard(commands.create.curl)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="list" className="mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">List Events</h4>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-2 text-xs"
                  onClick={() => loadCommand(commands.list)}
                >
                  <ArrowRight className="h-3 w-3" />
                  Load in Playground
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Retrieve inbox events with optional filtering by topic, type, or time range.
              </p>
              <div className="relative">
                <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto whitespace-pre-wrap">
                  {commands.list.curl}
                </pre>
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute top-2 right-2"
                  onClick={() => copyToClipboard(commands.list.curl)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="acknowledge" className="mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">Acknowledge Event</h4>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-2 text-xs"
                  onClick={() => loadCommand(commands.acknowledge)}
                >
                  <ArrowRight className="h-3 w-3" />
                  Load in Playground
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Mark an event as acknowledged. Replace {"{event_id}"} with the actual event ID from the inbox.
              </p>
              <div className="relative">
                <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto whitespace-pre-wrap">
                  {commands.acknowledge.curl}
                </pre>
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute top-2 right-2"
                  onClick={() => copyToClipboard(commands.acknowledge.curl)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="delete" className="mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">Delete Event</h4>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-2 text-xs"
                  onClick={() => loadCommand(commands.delete)}
                >
                  <ArrowRight className="h-3 w-3" />
                  Load in Playground
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Permanently delete an event. Replace {"{event_id}"} with the actual event ID from the inbox.
              </p>
              <div className="relative">
                <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto whitespace-pre-wrap">
                  {commands.delete.curl}
                </pre>
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute top-2 right-2"
                  onClick={() => copyToClipboard(commands.delete.curl)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Quick Tips */}
        <div className="mt-8 p-4 rounded-lg bg-primary/5 border border-primary/20">
          <div className="flex items-start gap-2">
            <Clock className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-sm mb-1">Pro Tip</h4>
              <p className="text-xs text-muted-foreground">
                Click &quot;Load in Playground&quot; to instantly test any command. Events created here will appear in 
                the Dashboard tab in real-time!
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
