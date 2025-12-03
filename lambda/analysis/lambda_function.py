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

def convert_floats_to_strings(obj):
    """Recursively convert float values to strings for DynamoDB compatibility"""
    if isinstance(obj, dict):
        return {k: convert_floats_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_strings(item) for item in obj]
    elif isinstance(obj, float):
        return str(obj)
    return obj

def lambda_handler(event, context):
    """Generates text analysis using Bedrock"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Fetch raw market data - try today first, then fall back to most recent
    try:
        response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'MARKET'})
        raw_data = response['Item']
    except:
        # Fall back to most recent data by scanning
        try:
            response = table.scan(
                FilterExpression='sk = :sk',
                ExpressionAttributeValues={':sk': 'MARKET'},
                Limit=10
            )
            if response['Items']:
                # Get most recent by date
                items_with_dates = [item for item in response['Items'] if 'date' in item]
                if items_with_dates:
                    raw_data = max(items_with_dates, key=lambda x: x['date'])
                    date_key = raw_data['date']
                    print(f"Using most recent data from {date_key}")
                else:
                    return {'statusCode': 404, 'body': json.dumps('No market data available')}
            else:
                return {'statusCode': 404, 'body': json.dumps('No market data available')}
        except Exception as e:
            return {'statusCode': 404, 'body': json.dumps(f'Error fetching data: {str(e)}')}
    
    # Generate analysis with pre-filtered unusual activity
    unusual_activity = raw_data.get('unusual_activity', [])
    analysis = generate_analysis(raw_data['market_data'], unusual_activity)
    
    # Store analysis
    table.put_item(Item={
        'pk': f'DATA#{date_key}',
        'sk': 'ANALYSIS',
        'date': date_key,
        'analysis': analysis,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Analysis generated')}

def generate_analysis(market_data, unusual_activity):
    """Use Bedrock to create educational market analysis"""
    
    # Format unusual activity for Claude
    unusual_summary = "\n".join([
        f"- {item['symbol']}: {item['move']}% ({', '.join(item['reasons'])})"
        for item in unusual_activity[:15]
    ])
    
    prompt = f"""You are a senior technical analyst with 15+ years of experience. Analyze today's market data and provide context for unusual moves.

Market Data:
{json.dumps(market_data, indent=2, default=decimal_to_float)}

Pre-filtered Unusual Activity (volume spikes, breakouts, big moves):
{unusual_summary}

Output JSON with:

1. market_overview: 2-3 sentences with actual prices and notable patterns
   Example: "SPY closed at $679.68 (+0.69%), QQQ at $614.27 (+0.88%). Semiconductors led with NVDA +1.37%, while software lagged with ZS -13.03%, indicating rotation from high-valuation SaaS to hardware."

2. market_insights: 3 specific observations with tickers and percentages
   GOOD: "Semis outperforming software: NVDA +1.37%, AMD +3.93% vs WDAY -7.85%, ZS -13.03%. Hardware strength over cloud suggests investors favoring tangible earnings. Watch if this continues - could signal broader risk-off in SaaS."
   BAD: "Technology sector showing mixed performance today."
   Max 50 words each. Use actual tickers and percentages.

3. levels_to_watch: 5-7 tickers, ONE entry per ticker
   Format: "{{TICKER}} at ${{current}}. Resistance ${{above}} (technical reason: ATH, MA, swing high). Support ${{below}} (technical reason). Trend analysis. Price targets."
   Example: "SPY at $679.68. Resistance $688 (Nov 22 ATH, strong selling). Support $672 (20-day MA, prior breakout). Bullish momentum with higher lows. Break above targets $695-700."
   Max 80 words per ticker. Focus on: swing highs/lows, moving averages, breakout levels, volume. Avoid generic "round number" unless it aligns with technical level.

4. unusual_activity: Explain WHY each pre-filtered move matters (5-10 stocks)
   Format: {{"symbol": "TICKER", "move": "10.93", "note": "Brief context: earnings, breakout, sector rotation, etc."}}
   Use the pre-filtered list above. Add context like: earnings, news, technical breakout, sector rotation.

Rules:
- Resistance MUST be ABOVE current price, support MUST be BELOW
- Use ONLY actual numbers from data - no estimates
- One entry per ticker in levels_to_watch
- For unusual_activity, explain WHY it matters (not just that it moved)
- Base insights and levels_to_watch STRICTLY on the input data provided - do NOT use tickers from examples unless they appear in the actual market data

Return ONLY valid JSON: {{"market_overview": "", "market_insights": [], "levels_to_watch": [{{"symbol": "", "level": "", "note": ""}}], "unusual_activity": [{{"symbol": "", "move": "", "note": ""}}]}}"""

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 2000,
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }]
            })
        )
        
        result = json.loads(response['body'].read())
        analysis_text = result['content'][0]['text']
        print(f"Bedrock response: {analysis_text[:500]}")
        
        # Extract JSON from response
        start = analysis_text.find('{')
        end = analysis_text.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = analysis_text[start:end]
        analysis_dict = json.loads(json_str)
        # Convert any float values to strings to avoid DynamoDB issues
        return convert_floats_to_strings(analysis_dict)
        
    except Exception as e:
        print(f'Bedrock error: {e}')
        # Fallback: Create analysis using actual market data
        spy_price = float(market_data.get('SPY', {}).get('price', 0))
        spy_change = float(market_data.get('SPY', {}).get('change_percent', 0))
        qqq_price = float(market_data.get('QQQ', {}).get('price', 0))
        qqq_change = float(market_data.get('QQQ', {}).get('change_percent', 0))
        
        # Calculate realistic technical levels using round numbers
        def get_support_resistance(price):
            if price == 0:
                return 0, 0
            # Find nearest round numbers (multiples of 5)
            lower_round = (price // 5) * 5
            upper_round = lower_round + 5
            # If price is very close to upper, use next level
            if price > upper_round - 1:
                upper_round += 5
            return round(lower_round, 2), round(upper_round, 2)
        
        spy_support, spy_resistance = get_support_resistance(spy_price)
        qqq_support, qqq_resistance = get_support_resistance(qqq_price)
        
        market_status = "up" if spy_change > 0 else "down" if spy_change < 0 else "flat"
        
        return {
            'market_overview': f'SPY closed at ${spy_price:.2f} ({spy_change:+.2f}%), QQQ at ${qqq_price:.2f} ({qqq_change:+.2f}%). Markets are {market_status} today, providing opportunities to study price action and market structure.',
            'market_insights': [
                'Monitor key support and resistance levels - these represent areas where buying or selling pressure historically increases',
                'Watch for volume confirmation on breakouts - higher volume validates price moves and suggests institutional participation',
                'Consider overall market trend before individual trades - trading with the trend improves probability of success'
            ],
            'levels_to_watch': [
                {'symbol': 'SPY', 'level': f'{spy_support:.2f}', 'note': f'SPY currently at ${spy_price:.2f}, support at ${spy_support:.0f} - psychological level where buyers typically step in'},
                {'symbol': 'SPY', 'level': f'{spy_resistance:.2f}', 'note': f'SPY currently at ${spy_price:.2f}, resistance at ${spy_resistance:.0f} - round number where profit-taking often occurs'},
                {'symbol': 'QQQ', 'level': f'{qqq_support:.2f}', 'note': f'QQQ currently at ${qqq_price:.2f}, support at ${qqq_support:.0f} - watch for institutional buying interest'},
                {'symbol': 'QQQ', 'level': f'{qqq_resistance:.2f}', 'note': f'QQQ currently at ${qqq_price:.2f}, resistance at ${qqq_resistance:.0f} - breakout above this could signal continuation'}
            ]
        }
