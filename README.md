# ZapStream - Real-time Event Management Platform

A unified, real-time event ingestion and delivery API with a modern developer dashboard. ZapStream provides standardized, reliable triggers delivery for Zapier-like workflows.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Git

### One-Command Setup (New Developers)
```bash
git clone <repository-url>
cd ZapStream
make quickstart
```

This will:
- Set up the Python virtual environment
- Install all dependencies (frontend + backend)
- Initialize the SQLite database
- Run tests to verify everything works
- Start both development servers

### Manual Setup

1. **Environment Setup**
```bash
make env-setup    # Create .env from template
```

2. **Backend Setup**
```bash
make setup-backend    # Install Python dependencies
make db-init          # Initialize SQLite database
```

3. **Frontend Setup**
```bash
npm install           # Install Node.js dependencies
```

4. **Start Development**
```bash
make dev              # Start both frontend (port 3000) + backend (port 8000)
```

## 🏗️ Architecture

### Frontend (Next.js 16)
- **Framework**: Next.js 16 with App Router
- **UI**: React 19 with TypeScript
- **Styling**: Tailwind CSS v4.1.9 with shadcn/ui
- **State Management**: React hooks + Server-Sent Events
- **Real-time Updates**: EventSource API for live event streaming

### Backend (FastAPI)
- **Framework**: FastAPI with Python 3.9+
- **Database**: SQLite (development) / DynamoDB (production)
- **Authentication**: Bearer token / API key based
- **Real-time**: Server-Sent Events (SSE)
- **Testing**: pytest with comprehensive test suite

## 📋 Features

### Backend API
- ✅ **Event Ingestion** - POST /events with JSON payload validation
- ✅ **Event Listing** - GET /inbox with filtering and pagination
- ✅ **Event Management** - Acknowledge and delete events
- ✅ **Multi-tenancy** - API key based tenant isolation
- ✅ **Real-time Streaming** - SSE endpoint for live updates
- ✅ **Rate Limiting** - Configurable per-key limits
- ✅ **Idempotency** - Safe event retries
- ✅ **Health Monitoring** - Comprehensive health checks

### Frontend Dashboard
- ✅ **Real-time Event Stream** - Live event monitoring with SSE
- ✅ **Event Actions** - Acknowledge and delete events directly from UI
- ✅ **System Status** - Real-time backend connectivity monitoring
- ✅ **API Playground** - Interactive testing of backend endpoints
- ✅ **Error Handling** - Comprehensive error states and retry logic
- ✅ **Responsive Design** - Mobile-friendly interface

## 🔧 Development Commands

```bash
# Development
make dev                # Start both servers
make dev-frontend       # Frontend only (port 3000)
make dev-backend        # Backend only (port 8000)

# Testing
make test               # Run all tests
make test-backend       # Backend tests
make test-backend-cov   # Backend tests with coverage

# Code Quality
make lint               # Lint all code
make lint-frontend      # Frontend linting
make lint-backend       # Backend linting

# Database
make db-init            # Initialize database
make db-reset           # Reset database

# Environment
make health-check       # Verify development environment
make status             # Show current status
make env-setup          # Set up .env file

# Cleanup
make clean              # Clean temporary files and caches
```

## 🌐 API Endpoints

### Authentication
All endpoints require API key authentication via:
- `Authorization: Bearer <API_KEY>` header
- `X-API-Key: <API_KEY>` header
- `?api_key=<API_KEY>` query parameter (for SSE)

### Core Endpoints

#### Event Ingestion
```http
POST /events
Content-Type: application/json
Authorization: Bearer dev_key_123

{
  "source": "billing",
  "type": "invoice.paid",
  "topic": "finance",
  "payload": { "invoiceId": "inv_123", "amount": 4200 }
}
```

#### Event Listing
```http
GET /inbox?limit=50&topic=finance&type=invoice.paid
Authorization: Bearer dev_key_123
```

#### Event Management
```http
POST /inbox/{id}/ack    # Acknowledge event
DELETE /inbox/{id}      # Delete event
```

#### Real-time Stream
```http
GET /inbox/stream?api_key=dev_key_123
Accept: text/event-stream
```

#### Health Check
```http
GET /health
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file from `.env.example`:

```env
# Frontend
NEXT_PUBLIC_ZAPSTREAM_API_URL=http://localhost:8000
NEXT_PUBLIC_ZAPSTREAM_API_KEY=dev_key_123

# Backend
APP_ENV=development
BACKEND_PORT=8000
API_KEYS=dev_key_123=tenant_dev
STORAGE_BACKEND=sqlite
DATABASE_URL=sqlite:///./data/events.db
RATE_LIMIT_PER_MINUTE=60
MAX_PAYLOAD_BYTES=524288
```

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
make test-backend

# Run with coverage
make test-backend-cov

# Run specific test types
make test-backend-unit    # Unit tests only
make test-backend-api     # Integration tests only
```

### Manual Testing
1. **Backend API**: Visit `http://localhost:8000/docs` for interactive API documentation
2. **Frontend**: Open `http://localhost:3000` to use the dashboard
3. **Health Check**: Monitor system status in the dashboard or via `GET /health`

## 📊 Deployment

### Production Setup
1. **Backend**: Set `STORAGE_BACKEND=dynamodb` and configure AWS credentials
2. **Database**: Create DynamoDB table as specified in deployment guide
3. **Frontend**: Configure production API URL in environment variables

### Local Development
Uses SQLite database stored in `./data/events.db` - no AWS setup required.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Design System

### Colors
- **Primary**: Vibrant Orange (Zapier-inspired) - `oklch(0.65 0.21 35)`
- **Accent**: Electric Blue - `oklch(0.60 0.24 250)`
- **Success**: Vibrant Green - `oklch(0.65 0.20 145)`
- **Warning**: Bright Yellow - `oklch(0.80 0.18 85)`
- **Destructive**: Bright Red - `oklch(0.60 0.24 25)`

### Typography
- **Headings**: Inter (multiple weights)
- **Body**: Inter
- **Code**: JetBrains Mono

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

\`\`\`bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
\`\`\`

### Environment Variables

Create a `.env.local` file:

\`\`\`env
# API Configuration
NEXT_PUBLIC_API_URL=https://api.zapier.com/v1
NEXT_PUBLIC_API_KEY=your_api_key_here
\`\`\`

## AWS Deployment

### Option 1: AWS Amplify

\`\`\`bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Initialize Amplify
amplify init

# Add hosting
amplify add hosting

# Deploy
amplify publish
\`\`\`

### Option 2: S3 + CloudFront

\`\`\`bash
# Build the app
npm run build

# Upload to S3
aws s3 sync out/ s3://your-bucket-name

# Configure CloudFront distribution
# Point CloudFront to your S3 bucket
\`\`\`

## Project Structure

\`\`\`
├── app/
│   ├── layout.tsx          # Root layout with fonts
│   ├── page.tsx            # Main dashboard page
│   └── globals.css         # Global styles & theme
├── components/
│   ├── nav-header.tsx      # Top navigation
│   ├── stat-card.tsx       # Statistics display
│   ├── event-log.tsx       # Event stream viewer
│   ├── api-playground.tsx  # Interactive API tester
│   ├── connection-status.tsx # System health monitor
│   └── footer.tsx          # Footer component
└── lib/
    └── utils.ts            # Utility functions
\`\`\`

## API Integration

The frontend is designed to work with a RESTful Python backend:

### Key Endpoints

- `POST /events` - Send new events
- `GET /inbox` - Retrieve undelivered events
- `DELETE /events/:id` - Acknowledge event delivery

### Example Integration

\`\`\`typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL

export async function sendEvent(payload: Record<string, unknown>) {
  const response = await fetch(`${API_URL}/events`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.NEXT_PUBLIC_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  
  return response.json()
}
\`\`\`

## Performance Optimizations

- **Code Splitting** - Automatic route-based splitting
- **Image Optimization** - Next.js Image component
- **Font Optimization** - next/font with variable fonts
- **CSS Optimization** - Tailwind JIT compilation
- **React Server Components** - Reduced client-side JavaScript

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

This project was built as a solo AI developer project using AI coding tools (Cursor, Claude Code, etc.).

## License

MIT
