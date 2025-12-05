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
subscriptions_table = dynamodb.Table('mrktdly-subscriptions')

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
    
    # Fetch all active signals from unified swing-signals table
    all_signals = []
    try:
        # Get active signals
        scan_response = swing_signals_table.scan(
            FilterExpression='#s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'active'}
        )
        all_signals = scan_response.get('Items', [])
        
        # Sort by confirmation count (desc), then risk/reward (desc)
        all_signals.sort(key=lambda x: (
            -float(x.get('signal_count', 1)),
            -float(x.get('risk_reward', 0))
        ))
        
        print(f"Retrieved {len(all_signals)} active signals (Technical + AI)")
    except Exception as e:
        print(f"Error fetching signals: {e}")
        # Continue without signals
    
    # Get waitlist emails
    waitlist_response = waitlist_table.scan()
    emails = [item['email'] for item in waitlist_response['Items']]
    
    if not emails:
        return {'statusCode': 200, 'body': json.dumps('No subscribers yet')}
        print(f"Error fetching predictions: {e}")
    
    # Send emails based on subscription tier
    current_hour = datetime.now(timezone.utc).hour
    is_morning = current_hour < 18  # Before 6pm UTC (1pm EST)
    
    sent_count = 0
    for email in emails:
        try:
            tier = get_subscription_tier(email)
            
            # Basic users: only evening email with 10 signals
            # Pro users: configurable emails (both morning and evening) with all signals
            # Free users: no signals
            if tier == 'basic':
                if not is_morning:  # Evening only
                    # Limit to 10 signals for basic tier
                    limited_signals = all_signals[:10]
                    send_email(email, analysis, limited_signals, date_key)
                    sent_count += 1
                else:
                    print(f'Skipping morning email for basic user: {email}')
            elif tier == 'pro':
                send_email(email, analysis, all_signals, date_key)
                sent_count += 1
            else:
                send_email(email, analysis, [], date_key)  # No signals for free
                sent_count += 1
        except Exception as e:
            print(f'Failed to send to {email}: {e}')
    
    return {'statusCode': 200, 'body': json.dumps(f'Sent to {sent_count} subscribers')}

def send_email(email, analysis, signals, date_key):
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
            move = str(item.get("move", "")).replace('%', '')
            unusual_html += (
                f'<div style="background: #374151; padding: 18px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #fbbf24;">'
                f'<strong style="color: #fcd34d; font-size: 17px;">{item.get("symbol", "")}</strong> '
                f'<span style="color: #93c5fd; font-size: 16px;">{move}%</span>'
                f'<p style="color: #f3f4f6; margin: 8px 0 0; font-size: 15px;">{item.get("note", "")}</p></div>'
            )
    
    # Build signals from unified table (already has Technical + AI)
    combined_signals = []
    
    for signal in signals:
        ticker = signal.get('ticker', '')
        source = signal.get('source', 'Technical')
        pattern_name = signal.get('pattern', '').replace('_', ' ').title()
        entry = float(signal.get('entry', 0))
        support = float(signal.get('support', 0))
        target = float(signal.get('target', 0))
        rr = float(signal.get('risk_reward', 0))
        volume_surge = float(signal.get('volume_surge', 0))
        historical_wr = signal.get('historical_win_rate', 0)
        
        # Signal repetition data
        signal_count = int(signal.get('signal_count', 1))
        
        # Pattern-specific reasoning
        if source == 'AI':
            reason = f"AI prediction with {signal_count}x confirmation" if signal_count > 1 else "AI prediction"
        elif signal.get('pattern') == 'ma20_pullback':
            reason = f"Oversold bounce at 20-day MA support"
        elif signal.get('pattern') == 'reversal_after_decline':
            reason = f"Strong reversal after 3+ down days with volume"
        elif signal.get('pattern') == 'gap_up_hold':
            reason = f"Gap up holding for 2+ days"
        elif signal.get('pattern') == 'consolidation_breakout':
            reason = f"Breaking out of consolidation with {int(volume_surge * 100)}% volume"
        elif signal.get('pattern') == 'bull_flag':
            reason = f"Bull flag pattern with {int(volume_surge * 100)}% volume"
        else:
            reason = f"Technical breakout with {int(volume_surge * 100)}% volume"
        
        wr_text = f" • {float(historical_wr):.0f}% historical win rate" if historical_wr else ""
        
        # Add confirmation badge if signal repeated
        confirmation_text = ""
        if signal_count > 1:
            confirmation_text = f" • 🔥 <strong>{signal_count}x Confirmed</strong>"
        
        combined_signals.append({
            'ticker': ticker,
            'entry': entry,
            'stop': support,
            'target': target,
            'rr': rr,
            'pattern': pattern_name,
            'reason': reason + wr_text + confirmation_text,
            'source': source
        })
    
    # Build unified signals HTML
    signals_html = ''
    for sig in combined_signals[:10]:  # Top 10
        entry = sig['entry']
        stop = sig['stop']
        target = sig['target']
        rr = sig['rr']
        
        # Badge color based on source
        badge_color = '#667eea' if sig['source'] == 'Technical' else '#10b981'
        
        signals_html += f'''
            <div style="background: #2d3748; padding: 20px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid {badge_color};">
                <div style="margin-bottom: 10px;">
                    <strong style="color: #60a5fa; font-size: 20px;">{sig['ticker']}</strong>
                    <span style="color: #93c5fd; font-size: 16px; margin-left: 8px;">${entry:.2f}</span>
                    <span style="background: #065f46; color: #6ee7b7; padding: 6px 14px; border-radius: 6px; font-size: 14px; font-weight: 600; margin-left: 10px;">
                        R:R 1:{rr:.1f}
                    </span>
                    <span style="background: {badge_color}; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 8px;">
                        {sig['source']}
                    </span>
                </div>
                <div style="color: #d1d5db; font-size: 14px; margin-bottom: 12px;">
                    <strong style="color: #f3f4f6;">{sig['pattern']}</strong> - {sig['reason']}
                </div>
                <table style="width: 100%; border-collapse: collapse; background: #1f2937; border-radius: 6px; padding: 12px;">
                    <tr>
                        <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Pattern Level</div>
                            <div style="color: #f9fafb; font-size: 18px; font-weight: 700; margin-top: 4px;">${entry:.2f}</div>
                        </td>
                        <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Support Level</div>
                            <div style="color: #fca5a5; font-size: 18px; font-weight: 700; margin-top: 4px;">${stop:.2f}</div>
                            <div style="font-size: 11px; color: #fca5a5; margin-top: 2px;">-{((entry - stop) / entry * 100):.1f}%</div>
                        </td>
                        <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Resistance Level</div>
                            <div style="color: #6ee7b7; font-size: 18px; font-weight: 700; margin-top: 4px;">${target:.2f}</div>
                            <div style="font-size: 11px; color: #6ee7b7; margin-top: 2px;">+{((target - entry) / entry * 100):.1f}%</div>
                        </td>
                        <td style="padding: 10px; color: #9ca3af; font-size: 13px; width: 25%;">
                            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Potential Move</div>
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
                    
                    <!-- Pattern Examples (Combined) -->
                    {'<tr><td style="padding: 20px 40px;"><h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">📚 Educational Pattern Examples</h2><p style="color: #aaaaaa; font-size: 14px; margin: 0 0 15px;">Technical patterns and AI analysis for learning purposes. Shows pattern levels, support/resistance, and potential price targets.</p>' + signals_html + '</td></tr>' if signals_html else '<tr><td style="padding: 20px 40px;"><div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 30px; text-align: center;"><h2 style="color: #ffffff; font-size: 24px; margin: 0 0 15px;">🔒 Unlock Pattern Alerts</h2><p style="color: #e0e0e0; font-size: 16px; margin: 0 0 20px;">Upgrade to Pro to receive daily pattern examples with technical levels and AI analysis.</p><a href="https://marketdly.com/pricing.html" style="display: inline-block; background: #ffffff; color: #667eea; padding: 12px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px;">View Pricing →</a></div></td></tr>'}
                    
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
        Source='no-reply@marketdly.com',
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': f'📊 Daily Market Summary - {date_str}'},
            'Body': {'Html': {'Data': html_body}}
        }
    )

def get_subscription_tier(email):
    """Get user's subscription tier"""
    try:
        response = subscriptions_table.get_item(Key={'email': email})
        if 'Item' in response and response['Item'].get('status') == 'active':
            return response['Item'].get('tier', 'free')
        return 'free'
    except Exception as e:
        print(f'Error getting subscription for {email}: {e}')
        return 'free'
