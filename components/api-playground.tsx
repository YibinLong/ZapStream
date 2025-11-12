"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Copy, Play, CheckCircle2, Book, Code2, Terminal } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export function ApiPlayground() {
  const { toast } = useToast()
  const [apiKey, setApiKey] = useState("zap_live_sk_1234567890abcdef")
  const [endpoint, setEndpoint] = useState("/events")
  const [method, setMethod] = useState("POST")
  const [payload, setPayload] = useState(
    JSON.stringify(
      {
        source: "test_frontend",
        type: "connection.test",
        topic: "integration",
        payload: {
          message: "Testing frontend-backend connection"
        }
      },
      null,
      2,
    ),
  )
  const [response, setResponse] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSendRequest = async () => {
    setIsLoading(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 800))

    const mockResponse = {
      success: true,
      event_id: `evt_${Math.random().toString(36).substring(7)}`,
      timestamp: new Date().toISOString(),
      status: "received",
      message: "Event successfully queued for processing",
    }

    setResponse(JSON.stringify(mockResponse, null, 2))
    setIsLoading(false)

    toast({
      title: "Request sent successfully",
      description: "Event has been queued for processing",
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copied to clipboard",
      description: "Code snippet copied successfully",
    })
  }

  const curlExample = `curl -X POST https://api.zapier.com/v1/events \\
  -H "Authorization: Bearer ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '${payload.replace(/\n/g, " ")}'`

  const pythonExample = `import requests

url = "https://api.zapier.com/v1/events"
headers = {
    "Authorization": "Bearer ${apiKey}",
    "Content-Type": "application/json"
}
payload = ${payload}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`

  const nodejsExample = `const response = await fetch('https://api.zapier.com/v1/events', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ${apiKey}',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(${payload.replace(/\n/g, " ")})
});

const data = await response.json();
console.log(data);`

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
            <div>
              <Label htmlFor="api-key" className="text-sm font-medium mb-2 flex items-center gap-2">
                API Key
                <Badge variant="outline" className="text-xs">
                  Required
                </Badge>
              </Label>
              <Input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="font-mono text-sm"
              />
            </div>

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
                />
              </div>
            </div>

            <div>
              <Label htmlFor="payload" className="text-sm font-medium mb-2">
                Request Body
              </Label>
              <Textarea
                id="payload"
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                className="font-mono text-sm min-h-[300px]"
                placeholder="Enter JSON payload..."
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
              <Badge className="bg-success/10 text-success border-success/30">200 OK</Badge>
            </div>
            <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto">{response}</pre>
          </Card>
        )}
      </div>

      {/* Code Examples */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <Code2 className="h-5 w-5 text-accent" />
          <h2 className="text-2xl font-bold text-balance">Code Examples</h2>
        </div>

        <Tabs defaultValue="curl" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="curl">cURL</TabsTrigger>
            <TabsTrigger value="python">Python</TabsTrigger>
            <TabsTrigger value="nodejs">Node.js</TabsTrigger>
          </TabsList>

          <TabsContent value="curl" className="mt-4">
            <div className="relative">
              <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto">{curlExample}</pre>
              <Button
                size="icon"
                variant="ghost"
                className="absolute top-2 right-2"
                onClick={() => copyToClipboard(curlExample)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="python" className="mt-4">
            <div className="relative">
              <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto">{pythonExample}</pre>
              <Button
                size="icon"
                variant="ghost"
                className="absolute top-2 right-2"
                onClick={() => copyToClipboard(pythonExample)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="nodejs" className="mt-4">
            <div className="relative">
              <pre className="text-xs font-mono p-4 bg-muted rounded-lg overflow-x-auto">{nodejsExample}</pre>
              <Button
                size="icon"
                variant="ghost"
                className="absolute top-2 right-2"
                onClick={() => copyToClipboard(nodejsExample)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </TabsContent>
        </Tabs>

        {/* Quick Docs */}
        <div className="mt-8 space-y-4">
          <div className="flex items-center gap-2">
            <Book className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-bold text-balance">Quick Start</h3>
          </div>

          <div className="space-y-3 text-sm">
            <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
              <h4 className="font-semibold mb-2">1. Get your API key</h4>
              <p className="text-muted-foreground text-xs">
                {"Generate an API key from your dashboard to authenticate requests"}
              </p>
            </div>

            <div className="p-4 rounded-lg bg-accent/5 border border-accent/20">
              <h4 className="font-semibold mb-2">2. Send an event</h4>
              <p className="text-muted-foreground text-xs">POST to /events with your event data in JSON format</p>
            </div>

            <div className="p-4 rounded-lg bg-success/5 border border-success/20">
              <h4 className="font-semibold mb-2">3. Monitor delivery</h4>
              <p className="text-muted-foreground text-xs">Track event status in real-time through the dashboard</p>
            </div>
          </div>

          <Button variant="outline" className="w-full mt-4 bg-transparent">
            View Full Documentation
          </Button>
        </div>
      </Card>
    </div>
  )
}
