import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses', region_name='us-east-1')
table = dynamodb.Table('mrktdly-data')
waitlist_table = dynamodb.Table('mrktdly-waitlist')

def lambda_handler(event, context):
    """Delivers daily analysis via email"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Fetch today's analysis
    try:
        response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'ANALYSIS'})
        analysis = response['Item']['analysis']
        print(f"Retrieved analysis: {json.dumps(analysis, default=str)}")
    except Exception as e:
        print(f"Error fetching analysis: {e}")
        return {'statusCode': 404, 'body': json.dumps(f'No analysis for {date_key}')}
    
    # Get waitlist emails
    waitlist_response = waitlist_table.scan()
    emails = [item['email'] for item in waitlist_response['Items']]
    
    if not emails:
        return {'statusCode': 200, 'body': json.dumps('No subscribers yet')}
    
    # Send emails
    sent_count = 0
    for email in emails:
        try:
            send_email(email, analysis, date_key)
            sent_count += 1
        except Exception as e:
            print(f'Failed to send to {email}: {e}')
    
    return {'statusCode': 200, 'body': json.dumps(f'Sent to {sent_count} subscribers')}

def send_email(email, analysis, date_key):
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
    insights_html = ''.join([f'<li style="margin-bottom: 10px;">{insight}</li>' for insight in analysis['market_insights']])
    
    # Handle levels_to_watch as either strings or objects
    levels_html = ''
    for level in analysis['levels_to_watch']:
        if isinstance(level, dict):
            levels_html += (
                f'<div style="background: #252a3a; padding: 15px; border-radius: 8px; margin-bottom: 10px;">'
                f'<strong style="color: #4a9eff; font-size: 16px;">{level.get("symbol", "")}</strong> - {level.get("level", "")}'
                f'<p style="color: #aaaaaa; margin: 5px 0 0; font-size: 14px;">{level.get("note", "")}</p></div>'
            )
        else:
            levels_html += f'<div style="background: #252a3a; padding: 15px; border-radius: 8px; margin-bottom: 10px; color: #cccccc; font-size: 15px; line-height: 1.6;">{level}</div>'
    
    # Build unusual activity section if present
    unusual_html = ''
    if 'unusual_activity' in analysis and analysis['unusual_activity']:
        for item in analysis['unusual_activity']:
            unusual_html += (
                f'<div style="background: #252a3a; padding: 15px; border-radius: 8px; margin-bottom: 10px;">'
                f'<strong style="color: #ffa500; font-size: 16px;">{item.get("symbol", "")}</strong> '
                f'<span style="color: #4a9eff;">{item.get("move", "")}%</span>'
                f'<p style="color: #cccccc; margin: 5px 0 0; font-size: 14px;">{item.get("note", "")}</p></div>'
            )
    
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
                            <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">📊 Market Overview</h2>
                            <p style="color: #cccccc; font-size: 16px; line-height: 1.7; margin: 0;">{analysis['market_overview']}</p>
                        </td>
                    </tr>
                    
                    <!-- Market Insights -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">💡 Market Insights</h2>
                            <ul style="color: #cccccc; font-size: 15px; line-height: 1.8; margin: 0; padding-left: 20px;">
                                {insights_html}
                            </ul>
                        </td>
                    </tr>
                    
                    <!-- Levels to Watch -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">🎯 Levels to Watch</h2>
                            {levels_html}
                        </td>
                    </tr>
                    
                    <!-- Unusual Activity (if present) -->
                    {'<tr><td style="padding: 20px 40px;"><h2 style="color: #ffffff; font-size: 22px; margin: 0 0 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">🔥 Unusual Activity</h2>' + unusual_html + '</td></tr>' if unusual_html else ''}
                    
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
