# ZapStream AWS Deployment Guide

This guide provides step-by-step instructions for deploying the ZapStream application on AWS, including both frontend and backend components.

## 🎯 Overview

**What gets deployed:**
- Backend: Serverless API (Lambda + API Gateway + DynamoDB)
- Frontend: Static website (S3 + CloudFront)
- Full integration between frontend and backend

## 📋 Prerequisites

- AWS CLI installed and configured
- Node.js and npm installed
- Python 3.11+ installed
- AWS CDK installed (`npm install -g aws-cdk`)

## 🚀 Deployment Steps

### Step 1: Backend Deployment (Lambda + API Gateway + DynamoDB)

#### 1.1 Create Minimal Lambda Function
Create `lambda_simple.py` with minimal dependencies:

```python
import json
import os
import boto3
import uuid
import decimal
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'ZapStreamEventsTable'))

# API keys mapping
API_KEYS = {
    'dev_key_123': 'tenant_dev',
    'prod_key_456': 'tenant_prod'
}

def get_tenant_from_auth(event):
    """Extract tenant from Authorization header"""
    auth_header = event.get('headers', {}).get('Authorization', '')
    if auth_header.startswith('Bearer '):
        api_key = auth_header[7:]
        return API_KEYS.get(api_key)
    return None

def response(status_code, body, headers=None):
    """Create API Gateway response"""
    if headers is None:
        headers = {}
    headers.update({
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Idempotency-Key',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    })

    def decimal_default(obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        raise TypeError

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, default=decimal_default)
    }

def handler(event, context):
    """Main Lambda handler"""
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')

    if http_method == 'OPTIONS':
        return response(200, {})

    if path == '/health' and http_method == 'GET':
        return response(200, {'status': 'healthy', 'service': 'ZapStream API'})

    elif path == '/events' and http_method == 'POST':
        tenant_id = get_tenant_from_auth(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        try:
            body = json.loads(event.get('body', '{}'))
            required_fields = ['source', 'type', 'topic', 'payload']
            for field in required_fields:
                if field not in body:
                    return response(400, {'error': f'Missing required field: {field}'})

            event_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            item = {
                'tenant_id': tenant_id,
                'event_id': event_id,
                'created_at': now,
                'source': body['source'],
                'type': body['type'],
                'topic': body['topic'],
                'payload': body['payload'],
                'status': 'pending'
            }

            if 'idempotency_key' in body:
                item['idempotency_key'] = body['idempotency_key']

            table.put_item(Item=item)
            return response(201, {'event_id': event_id, 'status': 'created', 'created_at': now})

        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    elif path == '/inbox' and http_method == 'GET':
        tenant_id = get_tenant_from_auth(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        try:
            response_data = table.scan(
                FilterExpression='tenant_id = :tenant_id',
                ExpressionAttributeValues={':tenant_id': tenant_id},
                Limit=50
            )

            events = []
            for item in response_data.get('Items', []):
                events.append({
                    'event_id': item['event_id'],
                    'created_at': item['created_at'],
                    'source': item['source'],
                    'type': item['type'],
                    'topic': item['topic'],
                    'payload': item['payload'],
                    'status': item['status']
                })

            return response(200, {'events': events, 'count': len(events), 'limit': 50})

        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    elif path.startswith('/inbox/') and http_method == 'POST' and path.endswith('/ack'):
        tenant_id = get_tenant_from_auth(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        event_id = path.split('/')[2]
        try:
            table.update_item(
                Key={'tenant_id': tenant_id, 'event_id': event_id},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'acknowledged'}
            )
            return response(200, {'event_id': event_id, 'status': 'acknowledged'})
        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    elif path.startswith('/inbox/') and http_method == 'DELETE':
        tenant_id = get_tenant_from_auth(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        event_id = path.split('/')[2]
        try:
            table.delete_item(Key={'tenant_id': tenant_id, 'event_id': event_id})
            return response(200, {'event_id': event_id, 'status': 'deleted'})
        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    else:
        return response(404, {'error': 'Not found'})
```

#### 1.2 Create Minimal Requirements
Create `requirements_simple.txt`:
```
boto3>=1.34.0
```

#### 1.3 Package Lambda Function
```bash
# Create deployment package
mkdir -p package_simple_final
cp lambda_simple.py package_simple_final/
pip install -r requirements_simple.txt -t package_simple_final/
cd package_simple_final
zip -r ../lambda_simple_final.zip .
cd ..
```

#### 1.4 Deploy CDK Stack
Update `cdk/lib/zapstream-serverless-stack.ts` to use the simple lambda:
```typescript
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

// Lambda function using simple package
const apiLambda = new lambda.Function(this, 'ZapStreamAPIFunction', {
  runtime: lambda.Runtime.PYTHON_3_11,
  handler: 'lambda_simple.handler',
  timeout: Duration.seconds(30),
  memorySize: 512,
  environment: {
    STORAGE_BACKEND: 'dynamodb',
    DYNAMODB_TABLE: eventsTable.tableName,
    LOG_LEVEL: 'INFO',
    CORS_ALLOWED_ORIGINS: '*',
    API_KEYS: 'dev_key_123=tenant_dev,prod_key_456=tenant_prod',
  },
  logRetention: logs.RetentionDays.ONE_WEEK,
  code: lambda.Code.fromAsset('../lambda_simple_final.zip'),
});
```

Deploy the stack:
```bash
cd cdk
npx cdk deploy ZapStreamServerlessStack --require-approval never
```

**Expected Output:** API Gateway URL like `https://xxxxx.execute-api.us-west-2.amazonaws.com/v1/`

### Step 2: Frontend Deployment (S3 Static Website)

#### 2.1 Update Environment Variables
Update `.env` file with the backend URL:
```env
# External API Configuration
NEXT_PUBLIC_API_URL=https://YOUR_API_GATEWAY_URL/v1
NEXT_PUBLIC_API_KEY=dev_key_123

# Production URL
NEXT_PUBLIC_APP_URL=http://zapstream-app-1762821749.s3-website-us-west-2.amazonaws.com
```

#### 2.2 Build Frontend
```bash
npm run build
```

#### 2.3 Create and Configure S3 Bucket
```bash
# Create S3 bucket (replace with your bucket name)
aws s3 mb s3://zapstream-app-1762821749 --region us-west-2

# Configure for static website hosting
aws s3 website s3://zapstream-app-1762821749 \
  --index-document index.html \
  --error-document 404.html \
  --region us-west-2

# Make bucket publicly readable
aws s3api put-bucket-policy --bucket zapstream-app-1762821749 --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::zapstream-app-1762821749/*"
    }
  ]
}' --region us-west-2
```

#### 2.4 Deploy Frontend Files
```bash
# Sync built frontend to S3
aws s3 sync out/ s3://zapstream-app-1762821749 --delete --region us-west-2
```

### Step 3: Testing and Verification

#### 3.1 Test Backend API
```bash
# Health check
curl -X GET "https://YOUR_API_GATEWAY_URL/v1/health"

# Create event
curl -X POST "https://YOUR_API_GATEWAY_URL/v1/events" \
  -H "Authorization: Bearer dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "billing",
    "type": "invoice.paid",
    "topic": "finance",
    "payload": {"invoiceId": "inv_123", "amount": 4200}
  }'

# List events
curl -X GET "https://YOUR_API_GATEWAY_URL/v1/inbox" \
  -H "Authorization: Bearer dev_key_123"
```

#### 3.2 Test Frontend
Open in browser: `http://zapstream-app-1762821749.s3-website-us-west-2.amazonaws.com`

**Expected:**
- Beautiful dashboard loads
- Statistics cards displayed
- Event stream shows (currently mock data)
- System status shows "Connected"

## 🎯 Final URLs

- **Frontend:** `http://zapstream-app-1762821749.s3-website-us-west-2.amazonaws.com`
- **Backend API:** `https://YOUR_API_GATEWAY_URL/v1/`
- **Health Endpoint:** `https://YOUR_API_GATEWAY_URL/v1/health`

## ⚠️ Important Notes

### Current Limitations
1. **Frontend shows mock data** - The beautiful dashboard displays static sample data, not real API data
2. **No real-time updates** - The event stream doesn't auto-update with new events
3. **API key authentication** - Backend uses simple API key authentication (dev_key_123)

### To Make Frontend Real-Time
1. Update frontend components to fetch data from the backend API
2. Implement real-time polling or WebSocket connections
3. Connect the Event Stream component to actual backend data
4. Update statistics based on real data

### Security Considerations
- The S3 bucket is publicly accessible for simplicity
- API keys are hardcoded (use AWS Secrets Manager for production)
- Consider adding CloudFront CDN for better performance and HTTPS

### Cost Optimization
- All services use pay-per-request pricing
- Lambda is configured with minimal memory (512MB)
- DynamoDB uses on-demand capacity

## 🔄 Troubleshooting

### Common Issues

**Lambda deployment fails with size limit:**
- Use the minimal lambda package approach shown above
- Keep dependencies to minimum (only boto3)

**API Gateway returns "Missing Authentication Token":**
- Check Authorization header format: `Bearer dev_key_123`
- Ensure API key exists in the API_KEYS mapping

**S3 website returns 403 Forbidden:**
- Verify bucket policy allows public reads
- Check bucket exists in correct region
- Ensure website configuration is enabled

**Frontend doesn't load:**
- Wait a few minutes for S3 changes to propagate
- Check that index.html exists in bucket root
- Verify bucket name and region are correct

### Debugging Commands

```bash
# Check Lambda logs
aws logs tail /aws/lambda/ZapStreamServerlessStack-ZapStreamAPIFunction-Yz2PincHh1Z1 --follow

# Check DynamoDB table
aws dynamodb scan --table-name ZapStreamServerlessStack-ZapStreamEventsTable5C49E7EC-6X7MQ7GYCCRI

# Check API Gateway deployment
aws apigateway get-stages --rest-api-id YOUR_API_ID
```

## 🎉 Success Criteria

✅ Backend API deployed and responds to health checks
✅ Events can be created and retrieved via API
✅ Frontend website loads and displays correctly
✅ CORS is properly configured for cross-origin requests
✅ All infrastructure is serverless and pay-per-use

**Deployment Complete!** 🚀