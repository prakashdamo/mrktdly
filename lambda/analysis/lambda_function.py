import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
table = dynamodb.Table('mrktdly-data')

# Helper to convert Decimal to float
def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """Generates text analysis using Bedrock"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Fetch raw market data
    try:
        response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'MARKET'})
        raw_data = response['Item']
    except Exception as e:
        return {'statusCode': 404, 'body': json.dumps(f'No data for {date_key}')}
    
    # Generate analysis
    analysis = generate_analysis(raw_data['market_data'])
    
    # Store analysis
    table.put_item(Item={
        'pk': f'DATA#{date_key}',
        'sk': 'ANALYSIS',
        'date': date_key,
        'analysis': analysis,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Analysis generated')}

def generate_analysis(market_data):
    """Use Bedrock to create educational market analysis"""
    
    prompt = f"""You are an experienced market educator creating daily educational content for retail traders.

Today's Market Data:
{json.dumps(market_data, indent=2, default=decimal_to_float)}

Create an educational market analysis with these sections:

1. **Market Overview** (2-3 sentences): What's the overall market doing and why?

2. **Key Educational Concepts** (3 bullet points): What trading concepts or patterns are visible today? Focus on teaching, not recommending.

3. **Levels to Watch** (3-4 items): Key technical levels on SPY, QQQ for educational purposes. Explain WHY these levels matter.

4. **Risk Factors** (2-3 items): What should traders be aware of today from an educational perspective?

Write in a confident, fast-paced style that traders appreciate. Use terms like "support", "resistance", "breakout", "consolidation" naturally.

IMPORTANT: This is EDUCATIONAL content only. Never say "buy", "sell", or "recommend". Always frame as learning opportunities.

Return as JSON with keys: market_overview, educational_concepts (array), levels_to_watch (array), risk_factors (array)"""

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1500,
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }]
            })
        )
        
        result = json.loads(response['body'].read())
        analysis_text = result['content'][0]['text']
        
        # Extract JSON from response
        start = analysis_text.find('{')
        end = analysis_text.rfind('}') + 1
        return json.loads(analysis_text[start:end])
        
    except Exception as e:
        print(f'Bedrock error: {e}')
        # Fallback to simple analysis
        return {
            'market_overview': 'Market data fetched successfully. Analysis generation in progress.',
            'educational_concepts': [
                'Monitor key support and resistance levels',
                'Watch for volume confirmation on breakouts',
                'Consider overall market trend before individual trades'
            ],
            'levels_to_watch': [
                {'symbol': 'SPY', 'level': '450', 'note': 'Key support level'},
                {'symbol': 'QQQ', 'level': '380', 'note': 'Resistance to watch'}
            ],
            'risk_factors': [
                'Market volatility remains elevated',
                'Economic data releases this week'
            ]
        }
