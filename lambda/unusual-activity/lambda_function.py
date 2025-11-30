import json
import boto3
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-data')
price_history_table = dynamodb.Table('mrktdly-price-history')

def lambda_handler(event, context):
    """Detect unusual activity using historical data"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Get market data
    try:
        response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'MARKET'})
        market_data = response['Item']['market_data']
    except Exception as e:
        return {'statusCode': 404, 'body': json.dumps(f'No market data for {date_key}')}
    
    # Detect unusual activity
    unusual_activity = detect_unusual_activity(market_data)
    
    # Update market data with unusual activity
    table.update_item(
        Key={'pk': f'DATA#{date_key}', 'sk': 'MARKET'},
        UpdateExpression='SET unusual_activity = :ua',
        ExpressionAttributeValues={':ua': unusual_activity}
    )
    
    print(f'Detected {len(unusual_activity)} unusual activities')
    return {'statusCode': 200, 'body': json.dumps(f'Detected {len(unusual_activity)} activities')}

def detect_unusual_activity(market_data):
    """Detect unusual activity using historical data"""
    
    unusual = []
    
    for ticker, data in market_data.items():
        try:
            if float(data.get('price', 0)) == 0:
                continue
            
            # Get 260-day history (1 year)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
            
            response = price_history_table.query(
                KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(start_date, end_date),
                Limit=260,
                ScanIndexForward=False
            )
            
            history = response.get('Items', [])
            if len(history) < 20:
                continue
            
            # Sort by date descending
            history.sort(key=lambda x: x['date'], reverse=True)
            
            # Calculate metrics
            closes = [float(h['close']) for h in history]
            highs = [float(h['high']) for h in history]
            lows = [float(h['low']) for h in history]
            volumes = [int(h.get('volume', 0)) for h in history]
            ranges = [float(h['high']) - float(h['low']) for h in history]
            
            # Current data
            current_price = float(data['price'])
            current_volume = int(data['volume'])
            current_high = float(data['high'])
            current_low = float(data['low'])
            current_range = current_high - current_low
            change_pct = float(data['change_percent'])
            prev_close = float(data['prev_close'])
            
            # Averages
            avg_volume_20 = sum(volumes[:20]) / 20 if len(volumes) >= 20 else current_volume
            avg_range_20 = sum(ranges[:20]) / 20 if len(ranges) >= 20 else current_range
            ma_20 = sum(closes[:20]) / 20 if len(closes) >= 20 else current_price
            ma_50 = sum(closes[:50]) / 50 if len(closes) >= 50 else current_price
            
            # Extremes
            high_20d = max(closes[:20]) if len(closes) >= 20 else current_price
            low_20d = min(closes[:20]) if len(closes) >= 20 else current_price
            high_52w = max(closes[:252]) if len(closes) >= 252 else current_price
            low_52w = min(closes[:252]) if len(closes) >= 252 else current_price
            
            # Previous day data
            prev_high = highs[1] if len(highs) > 1 else current_high
            prev_low = lows[1] if len(lows) > 1 else current_low
            
            # Check for consecutive days
            consecutive_up = 0
            for i in range(min(5, len(closes)-1)):
                if closes[i] > closes[i+1]:
                    consecutive_up += 1
                else:
                    break
            
            reasons = []
            score = 0
            
            # Volume patterns
            if avg_volume_20 > 0:
                vol_ratio = current_volume / avg_volume_20
                if vol_ratio > 5:
                    reasons.append(f"{vol_ratio:.1f}x EXTREME volume")
                    score += 3
                elif vol_ratio > 2:
                    reasons.append(f"{vol_ratio:.1f}x volume")
                    score += 2
                elif vol_ratio < 0.3:
                    reasons.append(f"Low volume ({vol_ratio:.1f}x)")
                    score += 1
            
            # Price moves
            if abs(change_pct) > 10:
                reasons.append(f"{change_pct:+.1f}% HUGE move")
                score += 3
            elif abs(change_pct) > 5:
                reasons.append(f"{change_pct:+.1f}% move")
                score += 2
            
            # 52-week extremes
            if current_price > high_52w * 1.001:
                reasons.append("52-week HIGH")
                score += 3
            elif current_price < low_52w * 0.999:
                reasons.append("52-week LOW")
                score += 3
            
            # 20-day extremes
            if current_price > high_20d * 1.01:
                reasons.append("20d breakout")
                score += 2
            elif current_price < low_20d * 0.99:
                reasons.append("20d breakdown")
                score += 2
            
            # MA crossovers
            if len(closes) >= 2:
                prev_price = closes[1]
                if prev_price < ma_20 and current_price > ma_20:
                    reasons.append("MA20 cross UP")
                    score += 2
                elif prev_price > ma_20 and current_price < ma_20:
                    reasons.append("MA20 cross DOWN")
                    score += 2
                
                if len(closes) >= 50:
                    if prev_price < ma_50 and current_price > ma_50:
                        reasons.append("MA50 cross UP")
                        score += 3
                    elif prev_price > ma_50 and current_price < ma_50:
                        reasons.append("MA50 cross DOWN")
                        score += 3
            
            # Gaps
            gap = (current_price - prev_close) / prev_close * 100
            if gap > 5:
                reasons.append(f"{gap:+.1f}% gap UP")
                score += 2
            elif gap < -5:
                reasons.append(f"{gap:+.1f}% gap DOWN")
                score += 2
            elif abs(gap) > 2:
                reasons.append(f"{gap:+.1f}% gap")
                score += 1
            
            # Momentum
            if consecutive_up >= 3:
                reasons.append(f"{consecutive_up} days UP")
                score += 1
            
            # Wide range day
            if avg_range_20 > 0 and current_range > avg_range_20 * 2:
                reasons.append(f"Wide range ({current_range/avg_range_20:.1f}x)")
                score += 1
            
            # Inside/Outside days
            if current_high < prev_high and current_low > prev_low:
                reasons.append("Inside day")
                score += 1
            elif current_high > prev_high and current_low < prev_low:
                reasons.append("Outside day")
                score += 2
            
            # Reversal (big move opposite to trend)
            if len(closes) >= 5:
                trend_5d = (closes[0] - closes[4]) / closes[4] * 100
                if trend_5d < -5 and change_pct > 5:
                    reasons.append("Reversal UP")
                    score += 2
                elif trend_5d > 5 and change_pct < -5:
                    reasons.append("Reversal DOWN")
                    score += 2
            
            if reasons:
                unusual.append({
                    'symbol': ticker,
                    'move': str(change_pct),
                    'reasons': reasons,
                    'score': score,
                    'volume_ratio': str(round(current_volume / avg_volume_20, 1)) if avg_volume_20 > 0 else '0',
                    'price': str(current_price)
                })
        
        except Exception as e:
            print(f'Error analyzing {ticker}: {e}')
    
    # Sort by score, then by absolute move
    unusual.sort(key=lambda x: (x['score'], abs(float(x['move']))), reverse=True)
    print(f'Detected {len(unusual)} unusual activities')
    return unusual[:30]  # Top 30
