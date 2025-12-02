import json
import os
import boto3
import uuid
import decimal
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

def decimal_default(obj):
    """JSON serializer for DynamoDB Decimal values."""
    if isinstance(obj, decimal.Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'ZapStreamEventsTable'))

# API keys mapping
API_KEYS = {
    'dev_key_123': 'tenant_dev',
    'prod_key_456': 'tenant_prod'
}


def normalize_event(item):
    """
    Normalize a DynamoDB record into the event payload expected by the UI.

    DynamoDB can contain legacy or partially-written rows. This helper validates
    events to keep garbage rows from breaking the UI or showing red highlight
    states.
    """
    event_id = item.get('event_id')
    created_at = item.get('created_at') or item.get('timestamp')
    payload = item.get('payload')

    # Skip malformed records that do not have the minimum shape
    if not event_id or not created_at or payload is None:
        return None

    return {
        'event_id': event_id,
        'created_at': created_at,
        'source': item.get('source') or 'unknown',
        'type': item.get('type') or 'event',
        'topic': item.get('topic') or 'general',
        'payload': payload,
        'status': item.get('status') or 'pending'
    }

def get_tenant_from_event(event):
    """Extract tenant from Authorization header or query parameters"""
    # Try Authorization header first
    auth_header = event.get('headers', {}).get('Authorization', '')
    if auth_header and auth_header.startswith('Bearer '):
        api_key = auth_header[7:]
        tenant = API_KEYS.get(api_key)
        if tenant:
            return tenant

    # Try query parameters
    query_params = event.get('queryStringParameters', {}) or {}
    api_key = query_params.get('api_key')
    if api_key:
        tenant = API_KEYS.get(api_key)
        if tenant:
            return tenant

    return None

def response(status_code, body, headers=None, cors_only=False):
    """Create API Gateway response with aggressive CORS"""
    if headers is None:
        headers = {}

    # Aggressive CORS headers for MVP
    headers.update({
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Idempotency-Key,Accept,Cache-Control',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS,PATCH',
        'Access-Control-Max-Age': '86400'
    })

    if cors_only:
        return {
            'statusCode': status_code,
            'headers': headers,
            'body': ''
        }

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, default=decimal_default)
    }

def sse_response(data):
    """Create Server-Sent Events response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Idempotency-Key,Accept,Cache-Control',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS,PATCH',
            'Access-Control-Max-Age': '86400'
        },
        'body': data
    }

def handler(event, context):
    """Main Lambda handler"""
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')

    # Handle OPTIONS preflight requests for all paths
    if http_method == 'OPTIONS':
        return response(200, {}, cors_only=True)

    # Health check endpoint
    if path == '/health' and http_method == 'GET':
        return response(200, {
            'status': 'healthy',
            'service': 'ZapStream API',
            'timestamp': datetime.utcnow().isoformat()
        })

    # Events endpoint - Create new event
    elif path == '/events' and http_method == 'POST':
        tenant_id = get_tenant_from_event(event)
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
            return response(201, {
                'event_id': event_id,
                'status': 'created',
                'created_at': now,
                'tenant_id': tenant_id
            })

        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    # Inbox endpoint - List events
    elif path == '/inbox' and http_method == 'GET':
        tenant_id = get_tenant_from_event(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        try:
            query_params = event.get('queryStringParameters', {}) or {}
            limit = int(query_params.get('limit', 50))
            cursor = query_params.get('cursor')

            # Parse cursor for pagination
            exclusive_start_key = None
            if cursor:
                try:
                    # Decode base64 cursor
                    import base64
                    cursor_data = base64.b64decode(cursor).decode('utf-8')
                    cursor_parts = cursor_data.split('|', 1)
                    if len(cursor_parts) == 2:
                        created_at_str, event_id = cursor_parts
                        exclusive_start_key = {
                            'tenant_id': tenant_id,
                            'created_at': created_at_str,
                            'event_id': event_id
                        }
                except Exception:
                    # Invalid cursor, ignore it
                    pass

            query_params = {
                'IndexName': 'TenantStatusIndex',
                'KeyConditionExpression': Key('tenant_id').eq(tenant_id),
                'ScanIndexForward': False,
                'Limit': min(limit, 100)
            }

            if exclusive_start_key:
                query_params['ExclusiveStartKey'] = exclusive_start_key

            response_data = table.query(**query_params)

            events = []
            for item in response_data.get('Items', []):
                normalized = normalize_event(item)
                if normalized:
                    events.append(normalized)

            # Sort events by created_at descending (newest first)
            events.sort(key=lambda x: x['created_at'], reverse=True)

            # Generate next cursor if there are more items
            next_cursor = None
            last_evaluated_key = response_data.get('LastEvaluatedKey')
            if last_evaluated_key:
                import base64
                cursor_data = f"{last_evaluated_key['created_at']}|{last_evaluated_key['event_id']}"
                next_cursor = base64.b64encode(cursor_data.encode('utf-8')).decode('utf-8')

            return response(200, {
                'events': events,
                'count': len(events),
                'limit': limit,
                'tenant_id': tenant_id,
                'next_cursor': next_cursor
            })

        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    # Stream endpoint - Server-Sent Events
    elif path == '/inbox/stream' and http_method == 'GET':
        tenant_id = get_tenant_from_event(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        try:
            # Get recent events for streaming
            response_data = table.scan(
                FilterExpression='tenant_id = :tenant_id',
                ExpressionAttributeValues={':tenant_id': tenant_id},
                Limit=10
            )

            # Build SSE response
            sse_data = ""
            for item in response_data.get('Items', []):
                normalized = normalize_event(item)
                if not normalized:
                    continue
                event_data = {
                    'id': normalized['event_id'],
                    'event': 'message',
                    'data': json.dumps(normalized, default=decimal_default)
                }
                sse_data += f"id: {event_data['id']}\n"
                sse_data += f"event: {event_data['event']}\n"
                sse_data += f"data: {event_data['data']}\n\n"

            # Add heartbeat
            sse_data += "event: heartbeat\ndata: {\"type\":\"heartbeat\",\"timestamp\":\"" + datetime.utcnow().isoformat() + "\"}\n\n"

            return sse_response(sse_data)

        except Exception as e:
            error_data = f"event: error\ndata: {{\"error\":\"{str(e)}\"}}\n\n"
            return sse_response(error_data)

    # Acknowledge event endpoint
    elif path.startswith('/inbox/') and http_method == 'POST' and path.endswith('/ack'):
        tenant_id = get_tenant_from_event(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        event_id = path.split('/')[2]
        try:
            table.update_item(
                Key={'tenant_id': tenant_id, 'event_id': event_id},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'acknowledged'},
                ConditionExpression=Attr('event_id').exists()
            )
            return response(200, {'event_id': event_id, 'status': 'acknowledged'})
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                return response(404, {'error': f'Event {event_id} not found'})
            return response(500, {'error': f'Internal server error: {str(e)}'})
        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    # Delete event endpoint
    elif path.startswith('/inbox/') and http_method == 'DELETE':
        tenant_id = get_tenant_from_event(event)
        if not tenant_id:
            return response(401, {'error': 'Invalid or missing API key'})

        event_id = path.split('/')[2]
        try:
            table.delete_item(
                Key={'tenant_id': tenant_id, 'event_id': event_id},
                ConditionExpression=Attr('event_id').exists()
            )
            return response(200, {'event_id': event_id, 'status': 'deleted'})
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                return response(404, {'error': f'Event {event_id} not found'})
            return response(500, {'error': f'Internal server error: {str(e)}'})
        except Exception as e:
            return response(500, {'error': f'Internal server error: {str(e)}'})

    # Catch-all for unsupported paths
    else:
        return response(404, {
            'error': 'Not found',
            'path': path,
            'method': http_method,
            'message': 'The requested endpoint does not exist'
        })
