#!/bin/bash

# ZapStream AWS Amplify Deployment Script
echo "🚀 Starting ZapStream deployment to AWS Amplify..."

# Check if AWS credentials are set
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Check if Amplify CLI is installed
if ! command -v amplify &> /dev/null; then
    echo "❌ Amplify CLI not found. Installing..."
    npm install -g @aws-amplify/cli
fi

# Test AWS credentials
echo "🔐 Verifying AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials verified"
else
    echo "❌ Invalid AWS credentials. Please check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

# Build the Next.js application for static export
echo "📦 Building the application for static export..."
npm run build

# Initialize Amplify if not already initialized
if [ ! -d "amplify" ]; then
    echo "🔧 Initializing Amplify..."
    amplify init \
        --yes \
        --app zapstream-app \
        --envName production \
        --defaultEditor vscode
fi

# Add hosting if not already configured
if ! amplify status | grep -q "Hosting"; then
    echo "🌐 Adding Amplify Hosting..."
    amplify add hosting \
        --yes \
        --serviceType Amplify \
        --customRule "source=</^[^.]+$|\\.(?!(css|gif|ico|jpg|jpeg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>,target=/index.html,status=404"
fi

# Publish the application
echo "📦 Publishing application to Amplify..."
amplify publish \
    --yes \
    --categories hosting

echo "✅ Deployment completed!"
echo "🌍 Your application should be available at the Amplify console URL"
echo "📊 Check deployment status at: https://console.aws.amazon.com/amplify/"