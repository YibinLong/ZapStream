"""
AWS Lambda handler for ZapStream FastAPI application.
"""
import json
import logging
from mangum import Mangum
from backend.main import app

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create Mangum handler for FastAPI app
handler = Mangum(app)

def lambda_handler(event, context):
    """
    AWS Lambda handler for ZapStream API.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        response = handler(event, context)
        logger.info(f"Response: {json.dumps(response)}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                }
            })
        }