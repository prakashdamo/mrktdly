import json
import boto3

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    """Generate AI analysis using Bedrock Claude"""
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt')
        
        if not prompt:
            return response(400, {'error': 'prompt required'})
        
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
        
        return response(200, {'analysis': analysis})
        
    except Exception as e:
        return response(500, {'error': str(e)})

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
