import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from bedrock_limiter import check_and_increment, BedrockLimitExceeded

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table('mrktdly-analysis-cache')

def lambda_handler(event, context):
    """Generate AI analysis using Bedrock Claude with 24h caching"""
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt')
        portfolio_id = body.get('portfolio_id', 'unknown')
        
        if not prompt:
            return response(400, {'error': 'prompt required'})
        
        # Check cache first
        cache_key = f"ai-{portfolio_id}"
        cached = get_from_cache(cache_key)
        if cached:
            return response(200, {'analysis': cached, 'cached': True})
        
        # Check Bedrock rate limit
        try:
            check_and_increment()
        except BedrockLimitExceeded as e:
            return response(429, {'error': str(e)})
        
        # Call Bedrock Claude
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        bedrock_response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps(payload)
        )
        
        response_body = json.loads(bedrock_response['body'].read())
        analysis = response_body['content'][0]['text']
        
        # Cache for 24 hours
        save_to_cache(cache_key, analysis)
        
        return response(200, {'analysis': analysis, 'cached': False})
        
    except Exception as e:
        return response(500, {'error': str(e)})

def get_from_cache(cache_key):
    """Get cached analysis if not expired"""
    try:
        result = cache_table.get_item(Key={'cache_key': cache_key})
        if 'Item' in result:
            item = result['Item']
            expires_at = datetime.fromisoformat(item['expires_at'])
            if datetime.utcnow() < expires_at:
                return item['analysis']
    except Exception:
        pass
    return None

def save_to_cache(cache_key, analysis):
    """Save analysis to cache with 24h TTL"""
    try:
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        cache_table.put_item(Item={
            'cache_key': cache_key,
            'analysis': analysis,
            'expires_at': expires_at,
            'created_at': datetime.utcnow().isoformat()
        })
    except Exception:
        pass

def response(status_code, body):
    """Return API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }
