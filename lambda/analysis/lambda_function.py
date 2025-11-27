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
    
    prompt = f"""You are a seasoned market and technical analyst with 15+ years of experience analyzing price action, support/resistance levels, and market structure. You have deep expertise in technical analysis, chart patterns, and identifying key price levels.

Today's Market Data (includes major holdings for rotation analysis):
{json.dumps(market_data, indent=2, default=decimal_to_float)}

Analyze this data for sector rotation, unusual moves, and market trends. Look for stocks moving >3%, sector rotation patterns, and divergences.

CRITICAL for Levels to Watch: 
- When identifying resistance, the level MUST be ABOVE the current price
- When identifying support, the level MUST be BELOW the current price
- Calculate levels based on: round numbers, recent swing highs/lows, percentage-based levels (1-2% moves)
- For SPY at $679.68: resistance would be $685, $690, $695 (above current). Support would be $675, $670, $665 (below current)
- Double-check every level against current price to ensure it makes technical sense

Create an educational market analysis with these sections:

1. **Market Overview** (2-3 sentences): What's the overall market doing? MUST include actual closing prices (e.g., "SPY closed at $XXX.XX, up/down X.XX%"). Mention any notable rotation patterns or unusual moves.

2. **Market Insights** (3 bullet points): What trading concepts or patterns are visible today? MUST be specific to today's data with actual examples:
   - BAD: "Sector rotation can signal shifts in investor sentiment"
   - GOOD: "Semiconductors outperforming software today: NVDA +1.37%, AMD +3.93% while WDAY -7.85%, ZS -13.03%. This rotation from high-valuation SaaS to hardware suggests investors favoring tangible earnings over growth stories. Watch if this continues - could signal broader risk-off in cloud names."
   
   Use ACTUAL tickers, prices, and percentages from the data. Explain WHY it matters and WHAT to watch next. Make it actionable and specific to today.

3. **Levels to Watch** (array of objects): Key technical levels based on chart analysis. Each item MUST be an object with:
   - "symbol": ticker symbol (e.g., "SPY")
   - "level": specific price level (e.g., "685.00")
   - "note": comprehensive technical analysis for this ticker
   
   CRITICAL RULES:
   - ONE entry per ticker only (no duplicates - combine all analysis into one note)
   - Each note should cover BOTH support and resistance in a single comprehensive analysis
   - RESISTANCE must be ABOVE current price, SUPPORT must be BELOW current price
   - Prioritize technical analysis over round numbers: recent swing highs/lows, breakout levels, trend lines, moving averages, volume patterns, relative strength
   - Only mention round numbers if they align with actual technical levels
   
   Example format:
   "SPY currently at $679.68. Key resistance at $688 (recent all-time high from Nov 22, strong selling pressure here). Support at $672 (20-day moving average and previous breakout level). Price showing bullish momentum with higher lows, but watch for rejection at $688. Break above targets $695-$700 zone."
   
   Provide 5-7 tickers (one entry each) focusing on: 
   - SPY and QQQ (always include with comprehensive analysis)
   - Stocks with unusual activity showing clear technical setups
   - Sector leaders/laggards with actionable levels
   
   Focus on REAL technical analysis: swing points, moving averages, breakout/breakdown levels, trend analysis, volume confirmation. Avoid generic "round number" reasoning unless it's a true technical confluence.

4. **Unusual Activity** (array): Stocks that moved >5% or show unusual patterns. List 5-10 of the most notable moves with:
   - "symbol": ticker
   - "move": percentage change (e.g., "10.93" or "-7.85")
   - "note": brief explanation of what's notable and why it matters (e.g., "PLTR up 8.2% - significant breakout above resistance on high volume, watch for continuation or profit-taking")
   
   Prioritize the largest moves (both up and down). Include at least 5 if there are significant moves >5%. If fewer than 5 stocks moved >5%, include stocks with moves >3% that show interesting technical patterns.

CRITICAL REQUIREMENTS:
- Use ACTUAL NUMBERS from the market data provided
- Identify sector rotation if present (e.g., small caps outperforming, tech lagging)
- Highlight unusual moves (>5% changes) as learning opportunities
- Include specific prices in market_overview
- Write in a confident, fast-paced style
- This is EDUCATIONAL content only - never say "buy", "sell", or "recommend"

Return ONLY valid JSON with keys: market_overview, market_insights (array), levels_to_watch (array of objects with symbol/level/note), unusual_activity (array of objects with symbol/move/note - include at least 5 if available)"""

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
