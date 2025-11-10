# Zapier Triggers API Frontend

A modern, high-performance developer dashboard for managing real-time events through the Zapier Triggers API.

## Features

- **Real-time Event Dashboard** - Monitor incoming events with live status updates
- **API Playground** - Test endpoints with interactive request builder
- **Code Examples** - Ready-to-use snippets in cURL, Python, and Node.js
- **System Status** - Real-time service health monitoring
- **Beautiful UI** - Modern design with smooth animations and responsive layout

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui
- **Fonts**: Inter (sans-serif) & JetBrains Mono (code)
- **Icons**: Lucide React

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
