import json
import os
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses', region_name='us-east-1')
table = dynamodb.Table('mrktdly-data')
waitlist_table = dynamodb.Table('mrktdly-waitlist')
swing_signals_table = dynamodb.Table('mrktdly-swing-signals')

def lambda_handler(event, context):
    """Delivers daily analysis via email"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Fetch today's analysis - fall back to most recent if not available
    try:
        response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'ANALYSIS'})
        analysis = response['Item']['analysis']
        print(f"Retrieved analysis for {date_key}")
    except:
        # Fall back to most recent analysis by scanning
        try:
            response = table.scan(
                FilterExpression='sk = :sk',
                ExpressionAttributeValues={':sk': 'ANALYSIS'},
                Limit=10
            )
            if response['Items']:
                items_with_dates = [item for item in response['Items'] if 'date' in item]
                if items_with_dates:
                    most_recent = max(items_with_dates, key=lambda x: x['date'])
                    analysis = most_recent['analysis']
                    date_key = most_recent['date']
                    print(f"Using most recent analysis from {date_key}")
                else:
                    return {'statusCode': 404, 'body': json.dumps('No analysis available')}
            else:
                return {'statusCode': 404, 'body': json.dumps('No analysis available')}
        except Exception as e:
            print(f"Error fetching analysis: {e}")
            return {'statusCode': 404, 'body': json.dumps(f'Error: {str(e)}')}
    
    # Fetch swing signals - try today first, then most recent
    swing_signals = []
    try:
        swing_response = swing_signals_table.query(
            KeyConditionExpression=Key('date').eq(date_key)
        )
        swing_signals = swing_response.get('Items', [])
        
        # If no signals today, get most recent
        if not swing_signals:
            # Scan for most recent date
            scan_response = swing_signals_table.scan(Limit=100)
            if scan_response['Items']:
                # Group by date and get most recent
                from collections import defaultdict
                by_date = defaultdict(list)
                for item in scan_response['Items']:
                    by_date[item['date']].append(item)
                
                most_recent_date = max(by_date.keys())
                swing_signals = by_date[most_recent_date]
                print(f"Using swing signals from {most_recent_date}")
        
        # Sort by risk/reward descending
        swing_signals.sort(key=lambda x: float(x.get('risk_reward', 0)), reverse=True)
        # Take top 10
        swing_signals = swing_signals[:10]
        print(f"Retrieved {len(swing_signals)} swing signals")
    except Exception as e:
        print(f"Error fetching swing signals: {e}")
        # Continue without signals
    
    # Get waitlist emails
    waitlist_response = waitlist_table.scan()
    emails = [item['email'] for item in waitlist_response['Items']]
    
    if not emails:
        return {'statusCode': 200, 'body': json.dumps('No subscribers yet')}
    
    # Send emails
    sent_count = 0
    for email in emails:
        try:
            send_email(email, analysis, swing_signals, date_key)
            sent_count += 1
        except Exception as e:
            print(f'Failed to send to {email}: {e}')
    
    return {'statusCode': 200, 'body': json.dumps(f'Sent to {sent_count} subscribers')}

def send_email(email, analysis, swing_signals, date_key):
    """Send educational market analysis email"""
    
    date_str = datetime.strptime(date_key, '%Y-%m-%d').strftime('%B %d, %Y')
    
    # Validate analysis structure
    if not isinstance(analysis, dict):
        raise ValueError(f"Analysis is not a dict: {type(analysis)}")
    
    required_keys = ['market_overview', 'market_insights', 'levels_to_watch']
    for key in required_keys:
        if key not in analysis:
            raise ValueError(f"Missing required key: {key}")
    
    # Build dynamic content sections
    insights_html = ''.join([f'<li style="margin-bottom: 12px; color: #f3f4f6; font-size: 16px;">{insight}</li>' for insight in analysis['market_insights']])
    
    # Handle levels_to_watch as either strings or objects
    levels_html = ''
    for level in analysis['levels_to_watch']:
        if isinstance(level, dict):
            levels_html += (
                f'<div style="background: #374151; padding: 18px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #60a5fa;">'
                f'<strong style="color: #93c5fd; font-size: 17px;">{level.get("symbol", "")}</strong> - '
                f'<span style="color: #f3f4f6; font-size: 16px;">{level.get("level", "")}</span>'
                f'<p style="color: #f3f4f6; margin: 8px 0 0; font-size: 15px; line-height: 1.6;">{level.get("note", "")}</p></div>'
            )
        else:
            levels_html += f'<div style="background: #374151; padding: 18px; border-radius: 8px; margin-bottom: 12px; color: #f3f4f6; font-size: 16px; line-height: 1.7; border-left: 3px solid #60a5fa;">{level}</div>'
    
    # Build unusual activity section if present
    unusual_html = ''
    if 'unusual_activity' in analysis and analysis['unusual_activity']:
        for item in analysis['unusual_activity']:
            unusual_html += (
                f'<div style="background: #374151; padding: 18px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #fbbf24;">'
                f'<strong style="color: #fcd34d; font-size: 17px;">{item.get("symbol", "")}</strong> '
                f'<span style="color: #93c5fd; font-size: 16px;">{item.get("move", "")}%</span>'
                f'<p style="color: #f3f4f6; margin: 8px 0 0; font-size: 15px;">{item.get("note", "")}</p></div>'
            )
    
    # Build swing signals section
    swing_html = ''
    if swing_signals:
        for signal in swing_signals:
            pattern_name = signal.get('pattern', '').replace('_', ' ').title()
            entry = float(signal.get('entry', 0))
            support = float(signal.get('support', 0))
            target = float(signal.get('target', 0))
            rr = float(signal.get('risk_reward', 0))
            volume_surge = float(signal.get('volume_surge', 0))
            
            # Pattern-specific reasoning with historical win rates
            historical_wr = signal.get('historical_win_rate', 0)
            wr_text = f" (Historical: {float(historical_wr):.1f}% win rate)" if historical_wr else ""
            
            if signal.get('pattern') == 'consolidation_breakout':
                reason = f"Breaking out of 35-day consolidation with {int(volume_surge * 100)}% volume surge{wr_text}"
            elif signal.get('pattern') == 'bull_flag':
                reason = f"Bull flag pattern with strong uptrend, {int(volume_surge * 100)}% volume on breakout{wr_text}"
            elif signal.get('pattern') == 'ascending_triangle':
                reason = f"Ascending triangle breakout with rising support, {int(volume_surge * 100)}% volume{wr_text}"
            elif signal.get('pattern') == 'momentum_alignment':
                reason = f"RSI and MACD both trending up, price above 20-day MA - strong momentum{wr_text}"
            elif signal.get('pattern') == 'volume_breakout':
                reason = f"New 20-day high with {int(volume_surge * 100)}% volume surge - institutional buying{wr_text}"
            elif signal.get('pattern') == 'reversal_after_decline':
                reason = f"⭐ Strong reversal after 3+ down days with volume - 68.9% historical win rate"
            elif signal.get('pattern') == 'gap_up_hold':
                reason = f"⭐ Gap up holding for 2+ days - 67.3% historical win rate"
            elif signal.get('pattern') == 'ma20_pullback':
                reason = f"⭐ Oversold bounce at 20-day MA support - 60.2% historical win rate"
            else:
                reason = f"Technical breakout with {int(volume_surge * 100)}% volume surge{wr_text}"
            
            swing_html += f'''
                <div style="background: #2d3748; padding: 20px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #60a5fa;">
                    <div style="margin-bottom: 10px;">
                        <strong style="color: #60a5fa; font-size: 20px;">{signal.get("ticker", "")}</strong>
                        <span style="background: #065f46; color: #6ee7b7; padding: 6px 14px; border-radius: 6px; font-size: 14px; font-weight: 600; margin-left: 10px;">
                            Risk $1 to Make ${rr:.1f}
                        </span>
                    </div>
                    <div style="color: #d1d5db; font-size: 14px; margin-bottom: 12px;">
                        <strong style="color: #f3f4f6;">{pattern_name}</strong> - {reason}
                    </div>
                    <table style="width: 100%; border-collapse: collapse; background: #1f2937; border-radius: 6px; padding: 12px;">
                        <tr>
                            <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Entry Price</div>
                                <div style="color: #f9fafb; font-size: 18px; font-weight: 700; margin-top: 4px;">${entry:.2f}</div>
                            </td>
                            <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Stop Loss</div>
                                <div style="color: #fca5a5; font-size: 18px; font-weight: 700; margin-top: 4px;">${support:.2f}</div>
                                <div style="font-size: 11px; color: #fca5a5; margin-top: 2px;">Risk: ${(entry - support):.2f}</div>
                            </td>
                            <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Target</div>
                                <div style="color: #6ee7b7; font-size: 18px; font-weight: 700; margin-top: 4px;">${target:.2f}</div>
                                <div style="font-size: 11px; color: #6ee7b7; margin-top: 2px;">Gain: ${(target - entry):.2f}</div>
                            </td>
                            <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Upside</div>
                                <div style="color: #6ee7b7; font-size: 18px; font-weight: 700; margin-top: 4px;">+{((target - entry) / entry * 100):.1f}%</div>
                            </td>
                        </tr>
                    </table>
                </div>
            '''
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0f19;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0f19;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1f2e; border-radius: 12px; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 700;">Daily Market Summary</h1>
                            <p style="margin: 10px 0 0; color: #e0e0e0; font-size: 16px;">{date_str}</p>
                        </td>
                    </tr>
                    
                    <!-- Market Overview -->
                    <tr>
                        <td style="padding: 30px 40px;">
                            <h2 style="color: #ffffff; font-size: 24px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">📊 Market Overview</h2>
                            <p style="color: #f3f4f6; font-size: 17px; line-height: 1.8; margin: 0;">{analysis['market_overview']}</p>
                        </td>
                    </tr>
                    
                    <!-- Market Insights -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <h2 style="color: #ffffff; font-size: 24px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">💡 Market Insights</h2>
                            <ul style="color: #f3f4f6; font-size: 16px; line-height: 1.9; margin: 0; padding-left: 20px;">
                                {insights_html}
                            </ul>
                        </td>
                    </tr>
                    
                    <!-- Levels to Watch -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <h2 style="color: #ffffff; font-size: 24px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">🎯 Levels to Watch</h2>
                            {levels_html}
                        </td>
                    </tr>
                    
                    <!-- Unusual Activity (if present) -->
                    {'<tr><td style="padding: 20px 40px;"><h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">🔥 Unusual Activity</h2>' + unusual_html + '</td></tr>' if unusual_html else ''}
                    
                    <!-- Swing Trade Signals (if present) -->
                    {'<tr><td style="padding: 20px 40px;"><h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">🎯 Swing Trade Opportunities</h2><p style="color: #aaaaaa; font-size: 14px; margin: 0 0 15px;">Technical breakout patterns with defined entry, stop, and target levels.</p>' + swing_html + '</td></tr>' if swing_html else ''}
                    
                    <!-- Disclaimer -->
                    <tr>
                        <td style="padding: 30px 40px; border-top: 1px solid #2a2f3e;">
                            <p style="color: #666666; font-size: 12px; line-height: 1.6; margin: 0; text-align: center;">
                                <strong>EDUCATIONAL CONTENT ONLY</strong><br>
                                This content is for educational purposes only and does not constitute financial advice, investment recommendations, or an offer to buy or sell securities. 
                                Always conduct your own research and consult with a licensed financial advisor before making investment decisions.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px; text-align: center; background: #0a0f19;">
                            <p style="color: #666666; font-size: 13px; margin: 0;">
                                © 2025 Daily Market Summary. Educational market commentary.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    
    ses.send_email(
        Source='prakash@dalalbytes.com',
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': f'📊 Daily Market Summary - {date_str}'},
            'Body': {'Html': {'Data': html_body}}
        }
    )
