import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

cloudwatch = boto3.client('cloudwatch')
dynamodb = boto3.resource('dynamodb')
ce = boto3.client('ce')
ses = boto3.client('ses', region_name='us-east-1')
logs = boto3.client('logs')

ADMIN_EMAIL = 'prakash@dalalbytes.com'

def lambda_handler(event, context):
    """Generate and send daily status email"""
    
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Determine if morning or evening
    time_of_day = event.get('time', 'morning')  # 'morning' or 'evening'
    
    # Collect all metrics
    aws_health = get_aws_health(yesterday)
    user_metrics = get_user_metrics()
    trading_health = get_trading_health()
    revenue = get_revenue_metrics()
    costs = get_cost_summary(yesterday)
    alerts = get_alerts()
    
    # Debug output
    print(f"User metrics: {user_metrics}")
    print(f"Trading health: {trading_health}")
    print(f"Revenue: {revenue}")
    print(f"Costs: {costs}")
    print(f"AWS health Lambda count: {len(aws_health['lambda'])}")
    
    # Generate email
    html = generate_email_html(aws_health, user_metrics, trading_health, revenue, costs, alerts, yesterday, time_of_day)
    text = generate_text_email(aws_health, user_metrics, trading_health, revenue, costs, alerts, yesterday)
    
    # Send email
    send_email(html, text, yesterday, time_of_day)
    
    return {'statusCode': 200, 'body': 'Status email sent'}

def get_aws_health(date):
    """Get AWS service health metrics"""
    
    # Lambda metrics
    lambda_functions = [
        'mrktdly-swing-scanner', 'mrktdly-signal-tracker', 'mrktdly-delivery',
        'mrktdly-data-fetch', 'mrktdly-ai-analysis', 'mrktdly-ticker-analysis'
    ]
    
    lambda_stats = []
    for func in lambda_functions:
        try:
            invocations = get_metric_sum('AWS/Lambda', 'Invocations', 'FunctionName', func, date)
            errors = get_metric_sum('AWS/Lambda', 'Errors', 'FunctionName', func, date)
            throttles = get_metric_sum('AWS/Lambda', 'Throttles', 'FunctionName', func, date)
            duration = get_metric_avg('AWS/Lambda', 'Duration', 'FunctionName', func, date)
            
            lambda_stats.append({
                'name': func.replace('mrktdly-', ''),
                'invocations': int(invocations),
                'errors': int(errors),
                'throttles': int(throttles),
                'avg_duration': int(duration)
            })
        except:
            pass
    
    # API Gateway metrics
    api_requests = get_metric_sum('AWS/ApiGateway', 'Count', 'ApiName', 'mrktdly-api', date)
    api_4xx = get_metric_sum('AWS/ApiGateway', '4XXError', 'ApiName', 'mrktdly-api', date)
    api_5xx = get_metric_sum('AWS/ApiGateway', '5XXError', 'ApiName', 'mrktdly-api', date)
    
    return {
        'lambda': lambda_stats,
        'api': {
            'requests': int(api_requests),
            '4xx': int(api_4xx),
            '5xx': int(api_5xx)
        }
    }

def get_user_metrics():
    """Get user and subscription metrics"""
    
    subscriptions_table = dynamodb.Table('mrktdly-subscriptions')
    
    # Count by tier
    response = subscriptions_table.scan()
    items = response.get('Items', [])
    
    free = sum(1 for i in items if i.get('tier', 'free') == 'free')
    basic = sum(1 for i in items if i.get('tier') == 'basic' and i.get('status') == 'active')
    pro = sum(1 for i in items if i.get('tier') == 'pro' and i.get('status') == 'active')
    
    # Calculate MRR
    mrr = (basic * 9.99) + (pro * 19.99)
    
    return {
        'total': len(items),
        'free': free,
        'basic': basic,
        'pro': pro,
        'mrr': round(mrr, 2)
    }

def get_trading_health():
    """Get trading system health"""
    
    signals_table = dynamodb.Table('mrktdly-swing-signals')
    
    # Active signals
    response = signals_table.scan(
        FilterExpression='#s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'active'}
    )
    active = len(response.get('Items', []))
    
    # Today's signals
    today = datetime.utcnow().strftime('%Y-%m-%d')
    response = signals_table.scan(
        FilterExpression='#d = :date',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':date': today}
    )
    today_signals = response.get('Items', [])
    technical = sum(1 for s in today_signals if s.get('source') == 'technical')
    ai = sum(1 for s in today_signals if s.get('source') == 'ai_prediction')
    
    # Closed today
    response = signals_table.scan(
        FilterExpression='#s = :status AND exit_date = :date',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'closed', ':date': today}
    )
    closed_today = response.get('Items', [])
    wins = sum(1 for s in closed_today if float(s.get('return_pct', 0)) > 0)
    
    return {
        'active': active,
        'today_total': len(today_signals),
        'today_technical': technical,
        'today_ai': ai,
        'closed_today': len(closed_today),
        'wins_today': wins
    }

def get_revenue_metrics():
    """Get revenue and conversion metrics"""
    
    # This would integrate with Stripe API
    # For now, calculate from subscriptions
    
    subscriptions_table = dynamodb.Table('mrktdly-subscriptions')
    response = subscriptions_table.scan()
    items = response.get('Items', [])
    
    basic = sum(1 for i in items if i.get('tier') == 'basic' and i.get('status') == 'active')
    pro = sum(1 for i in items if i.get('tier') == 'pro' and i.get('status') == 'active')
    
    daily_revenue = ((basic * 9.99) + (pro * 19.99)) / 30
    
    return {
        'daily_revenue': round(daily_revenue, 2),
        'paying_users': basic + pro
    }

def get_cost_summary(date):
    """Get AWS cost breakdown"""
    
    start = date.strftime('%Y-%m-%d')
    end = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        # Total cost
        response = ce.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['BlendedCost']
        )
        total = float(response['ResultsByTime'][0]['Total']['BlendedCost']['Amount'])
        
        # Service breakdown
        response = ce.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        services = {}
        for group in response['ResultsByTime'][0]['Groups']:
            service = group['Keys'][0]
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            if cost > 0.01:
                services[service] = round(cost, 2)
        
        return {
            'total': round(total, 2),
            'services': services,
            'projected_monthly': round(total * 30, 2)
        }
    except Exception as e:
        print(f"Cost API error: {e}")
        return {
            'total': 0,
            'services': {},
            'projected_monthly': 0
        }

def get_alerts():
    """Get critical alerts"""
    
    alerts = []
    
    # Check for Lambda errors
    lambda_functions = ['mrktdly-swing-scanner', 'mrktdly-delivery', 'mrktdly-signal-tracker']
    for func in lambda_functions:
        errors = get_metric_sum('AWS/Lambda', 'Errors', 'FunctionName', func, datetime.utcnow().date())
        if errors > 5:
            alerts.append(f"🔴 {func}: {int(errors)} errors in last 24h")
    
    return alerts

def get_metric_sum(namespace, metric, dim_name, dim_value, date):
    """Get CloudWatch metric sum"""
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric,
            Dimensions=[{'Name': dim_name, 'Value': dim_value}],
            StartTime=datetime.combine(date, datetime.min.time()),
            EndTime=datetime.combine(date, datetime.max.time()),
            Period=86400,
            Statistics=['Sum']
        )
        if response['Datapoints']:
            return response['Datapoints'][0]['Sum']
        return 0
    except:
        return 0

def get_metric_avg(namespace, metric, dim_name, dim_value, date):
    """Get CloudWatch metric average"""
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric,
            Dimensions=[{'Name': dim_name, 'Value': dim_value}],
            StartTime=datetime.combine(date, datetime.min.time()),
            EndTime=datetime.combine(date, datetime.max.time()),
            Period=86400,
            Statistics=['Average']
        )
        if response['Datapoints']:
            return response['Datapoints'][0]['Average']
        return 0
    except:
        return 0

def fmt(num):
    """Format number with commas"""
    if num is None:
        return "0"
    if isinstance(num, (int, float)):
        if isinstance(num, float):
            return f"{num:,.2f}"
        return f"{num:,}"
    return str(num)

def generate_email_html(aws_health, user_metrics, trading_health, revenue, costs, alerts, date, time_of_day):
    """Generate HTML email"""
    
    status_icon = '🟢' if not alerts else '🟡'
    status_text = 'Healthy' if not alerts else 'Warnings'
    time_label = '🌅 Morning Report' if time_of_day == 'morning' else '🌆 Evening Report'
    
    profit = revenue['daily_revenue'] - costs['total']
    margin = (profit / revenue['daily_revenue'] * 100) if revenue['daily_revenue'] > 0 else 0
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; line-height: 1.6; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 30px; }}
            h1 {{ color: #60a5fa; margin: 0 0 10px 0; font-size: 32px; }}
            h2 {{ color: #a78bfa; border-bottom: 2px solid #334155; padding-bottom: 12px; margin: 35px 0 20px 0; font-size: 22px; }}
            h3 {{ color: #94a3b8; font-size: 18px; margin: 25px 0 15px 0; }}
            .status {{ font-size: 18px; color: #94a3b8; margin-bottom: 30px; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin: 20px 0; }}
            .metric-card {{ background: #0f172a; padding: 20px; border-radius: 10px; border-left: 4px solid #60a5fa; }}
            .metric-label {{ color: #94a3b8; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
            .metric-value {{ font-size: 48px; font-weight: 700; margin: 8px 0; font-family: 'Courier New', monospace; color: #f1f5f9; }}
            .metric-sub {{ color: #64748b; font-size: 14px; margin-top: 6px; }}
            .alert {{ background: #7f1d1d; padding: 12px 16px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #ef4444; }}
            .success {{ color: #22c55e !important; }}
            .warning {{ color: #fbbf24 !important; }}
            .error {{ color: #f87171 !important; }}
            .neutral {{ color: #f1f5f9 !important; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: #0f172a; border-radius: 8px; overflow: hidden; }}
            th, td {{ padding: 14px 16px; text-align: left; }}
            th {{ background: #1e293b; color: #a78bfa; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
            td {{ border-bottom: 1px solid #334155; font-family: 'Courier New', monospace; color: #f1f5f9; font-size: 16px; }}
            tr:last-child td {{ border-bottom: none; }}
            .number {{ font-family: 'Courier New', monospace; font-weight: 700; color: #f1f5f9; font-size: 18px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{status_icon} MarketDly Daily Status</h1>
            <div class="status">{time_label} • {date.strftime('%A, %B %d, %Y')} • System Status: <strong>{status_text}</strong></div>
            
            <h2>💰 Financial Summary</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Daily Revenue</div>
                    <div class="metric-value success">${fmt(revenue['daily_revenue'])}</div>
                    <div class="metric-sub">{fmt(revenue['paying_users'])} paying users</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Daily AWS Cost</div>
                    <div class="metric-value error">${fmt(costs['total'])}</div>
                    <div class="metric-sub">Projected: ${fmt(costs['projected_monthly'])}/mo</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Daily Profit</div>
                    <div class="metric-value {'success' if profit > 0 else 'error'}">${fmt(profit)}</div>
                    <div class="metric-sub">Margin: {fmt(margin)}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">MRR</div>
                    <div class="metric-value neutral">${fmt(user_metrics['mrr'])}</div>
                    <div class="metric-sub">Monthly Recurring Revenue</div>
                </div>
            </div>
            
            <h2>👥 User Metrics</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Users</div>
                    <div class="metric-value neutral">{fmt(user_metrics['total'])}</div>
                    <div class="metric-sub">All tiers</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Free Tier</div>
                    <div class="metric-value neutral">{fmt(user_metrics['free'])}</div>
                    <div class="metric-sub">{fmt(user_metrics['free']/user_metrics['total']*100 if user_metrics['total'] > 0 else 0)}% of total</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Basic ($9.99)</div>
                    <div class="metric-value neutral">{fmt(user_metrics['basic'])}</div>
                    <div class="metric-sub">${fmt(user_metrics['basic'] * 9.99)}/mo</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Professional ($19.99)</div>
                    <div class="metric-value neutral">{fmt(user_metrics['pro'])}</div>
                    <div class="metric-sub">${fmt(user_metrics['pro'] * 19.99)}/mo</div>
                </div>
            </div>
            
            <h2>📊 Trading System Health</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Active Signals</div>
                    <div class="metric-value neutral">{fmt(trading_health['active'])}</div>
                    <div class="metric-sub">Currently monitoring</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Signals Generated Today</div>
                    <div class="metric-value neutral">{fmt(trading_health['today_total'])}</div>
                    <div class="metric-sub">Tech: {fmt(trading_health['today_technical'])}, AI: {fmt(trading_health['today_ai'])}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Closed Today</div>
                    <div class="metric-value neutral">{fmt(trading_health['closed_today'])}</div>
                    <div class="metric-sub">Wins: {fmt(trading_health['wins_today'])}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Win Rate Today</div>
                    <div class="metric-value neutral">
                        {fmt(trading_health['wins_today']/trading_health['closed_today']*100 if trading_health['closed_today'] > 0 else 0)}%
                    </div>
                    <div class="metric-sub">{fmt(trading_health['closed_today'])} trades</div>
                </div>
            </div>
                    <div class="metric-label">Basic ($9.99)</div>
                    <div class="metric-value">{fmt(user_metrics['basic'])}</div>
                    <div class="metric-sub">${fmt(user_metrics['basic'] * 9.99)}/mo</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Professional ($19.99)</div>
                    <div class="metric-value">{fmt(user_metrics['pro'])}</div>
                    <div class="metric-sub">${fmt(user_metrics['pro'] * 19.99)}/mo</div>
                </div>
            </div>
            
            <h2>📊 Trading System Health</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Active Signals</div>
                    <div class="metric-value">{fmt(trading_health['active'])}</div>
                    <div class="metric-sub">Currently monitoring</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Signals Generated Today</div>
                    <div class="metric-value">{fmt(trading_health['today_total'])}</div>
                    <div class="metric-sub">Tech: {fmt(trading_health['today_technical'])}, AI: {fmt(trading_health['today_ai'])}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Closed Today</div>
                    <div class="metric-value">{fmt(trading_health['closed_today'])}</div>
                    <div class="metric-sub">Wins: {fmt(trading_health['wins_today'])}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Win Rate Today</div>
                    <div class="metric-value">
                        {fmt(trading_health['wins_today']/trading_health['closed_today']*100 if trading_health['closed_today'] > 0 else 0)}%
                    </div>
                    <div class="metric-sub">{fmt(trading_health['closed_today'])} trades</div>
                </div>
            </div>
            
            <h2>☁️ AWS Service Health</h2>
            <table>
                <tr>
                    <th>Lambda Function</th>
                    <th style="text-align: right;">Invocations</th>
                    <th style="text-align: right;">Errors</th>
                    <th style="text-align: right;">Avg Duration</th>
                </tr>
    """
    
    for func in aws_health['lambda']:
        error_class = 'error' if func['errors'] > 0 else 'success'
        html += f"""
                <tr>
                    <td>{func['name']}</td>
                    <td style="text-align: right;" class="number">{fmt(func['invocations'])}</td>
                    <td style="text-align: right;" class="number {error_class}">{fmt(func['errors'])}</td>
                    <td style="text-align: right;" class="number">{fmt(func['avg_duration'])} ms</td>
                </tr>
        """
    
    html += f"""
            </table>
            
            <h3>API Gateway</h3>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value neutral">{fmt(aws_health['api']['requests'])}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">4xx Errors</div>
                    <div class="metric-value {'warning' if aws_health['api']['4xx'] > 0 else 'neutral'}">{fmt(aws_health['api']['4xx'])}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">5xx Errors</div>
                    <div class="metric-value {'error' if aws_health['api']['5xx'] > 0 else 'neutral'}">{fmt(aws_health['api']['5xx'])}</div>
                </div>
            </div>
            
            <h2>💵 Cost Breakdown</h2>
            <table>
                <tr>
                    <th>Service</th>
                    <th style="text-align: right;">Daily Cost</th>
                </tr>
    """
    
    for service, cost in sorted(costs['services'].items(), key=lambda x: x[1], reverse=True):
        html += f"""
                <tr>
                    <td>{service}</td>
                    <td style="text-align: right;" class="number">${fmt(cost)}</td>
                </tr>
        """
    
    html += f"""
            </table>
            
            <h2>🚨 Alerts</h2>
    """
    
    if alerts:
        for alert in alerts:
            html += f'<div class="alert">{alert}</div>'
    else:
        html += '<p class="success" style="padding: 15px; background: #064e3b; border-radius: 6px; border-left: 4px solid #10b981;">✅ No alerts - all systems operating normally</p>'
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html

def generate_text_email(aws_health, user_metrics, trading_health, revenue, costs, alerts, date):
    """Generate plain text email"""
    
    status_icon = '✓' if not alerts else '!'
    status_text = 'Healthy' if not alerts else 'Warnings'
    
    profit = revenue['daily_revenue'] - costs['total']
    margin = (profit / revenue['daily_revenue'] * 100) if revenue['daily_revenue'] > 0 else 0
    
    text = f"""
MarketDly Daily Status - {date.strftime('%A, %B %d, %Y')}
{'='*70}

[{status_icon}] System Status: {status_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 FINANCIAL SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Daily Revenue:        ${fmt(revenue['daily_revenue'])}  ({fmt(revenue['paying_users'])} paying users)
Daily AWS Cost:       ${fmt(costs['total'])}  (Projected: ${fmt(costs['projected_monthly'])}/mo)
Daily Profit:         ${fmt(profit)}  (Margin: {fmt(margin)}%)
MRR:                  ${fmt(user_metrics['mrr'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 USER METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Users:          {fmt(user_metrics['total'])}
  • Free:             {fmt(user_metrics['free'])}  ({fmt(user_metrics['free']/user_metrics['total']*100 if user_metrics['total'] > 0 else 0)}%)
  • Basic ($9.99):    {fmt(user_metrics['basic'])}  (${fmt(user_metrics['basic'] * 9.99)}/mo)
  • Pro ($19.99):     {fmt(user_metrics['pro'])}  (${fmt(user_metrics['pro'] * 19.99)}/mo)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TRADING SYSTEM HEALTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Active Signals:       {fmt(trading_health['active'])}
Today's Signals:      {fmt(trading_health['today_total'])}  (Technical: {fmt(trading_health['today_technical'])}, AI: {fmt(trading_health['today_ai'])})
Closed Today:         {fmt(trading_health['closed_today'])}  (Wins: {fmt(trading_health['wins_today'])})
Win Rate Today:       {fmt(trading_health['wins_today']/trading_health['closed_today']*100 if trading_health['closed_today'] > 0 else 0)}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☁️  AWS SERVICE HEALTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Lambda Functions:
"""
    
    for func in aws_health['lambda']:
        status = '✓' if func['errors'] == 0 else '✗'
        text += f"  [{status}] {func['name']:<25} {fmt(func['invocations']):>8} invocations, {fmt(func['errors']):>5} errors, {fmt(func['avg_duration']):>6} ms\n"
    
    text += f"""
API Gateway:
  • Total Requests:   {fmt(aws_health['api']['requests'])}
  • 4xx Errors:       {fmt(aws_health['api']['4xx'])}
  • 5xx Errors:       {fmt(aws_health['api']['5xx'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 COST BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for service, cost in sorted(costs['services'].items(), key=lambda x: x[1], reverse=True):
        text += f"  {service:<40} ${fmt(cost):>8}\n"
    
    text += f"\n  {'TOTAL':<40} ${fmt(costs['total']):>8}\n"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 ALERTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    if alerts:
        for alert in alerts:
            text += f"{alert}\n"
    else:
        text += "✓ No alerts - all systems operating normally\n"
    
    text += "\n" + "="*70 + "\n"
    
    return text

def send_email(html, text, date, time_of_day):
    """Send email via SES"""
    
    time_label = 'Morning' if time_of_day == 'morning' else 'Evening'
    
    ses.send_email(
        Source=ADMIN_EMAIL,
        Destination={'ToAddresses': [ADMIN_EMAIL]},
        Message={
            'Subject': {
                'Data': f'MarketDly {time_label} Status - {date.strftime("%b %d, %Y")}'
            },
            'Body': {
                'Text': {'Data': text},
                'Html': {'Data': html}
            }
        }
    )
