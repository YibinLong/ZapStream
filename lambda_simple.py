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