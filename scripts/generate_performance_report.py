#!/usr/bin/env python3
"""
Generate comprehensive performance analysis report with charts
"""
import boto3
import json
from datetime import datetime
from collections import defaultdict
import sys

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
signals_table = dynamodb.Table('mrktdly-swing-signals')

def get_all_signals():
    """Fetch all signals from DynamoDB"""
    response = signals_table.scan()
    return response['Items']

def analyze_performance(signals):
    """Comprehensive performance analysis"""
    
    # Separate active and closed
    closed = [s for s in signals if s.get('status') == 'closed']
    active = [s for s in signals if s.get('status') == 'active']
    
    # Basic stats
    wins = [s for s in closed if s.get('outcome') in ['WIN', 'EXPIRED'] and float(s.get('return_pct', 0)) > 0]
    losses = [s for s in closed if s not in wins]
    
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_win = sum(float(s['return_pct']) for s in wins) / len(wins) if wins else 0
    avg_loss = sum(float(s['return_pct']) for s in losses) / len(losses) if losses else 0
    
    # Expectancy
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
    
    # By source
    ai_closed = [s for s in closed if s.get('source') == 'AI']
    tech_closed = [s for s in closed if s.get('source') != 'AI']
    
    ai_wins = [s for s in ai_closed if s.get('outcome') in ['WIN', 'EXPIRED'] and float(s.get('return_pct', 0)) > 0]
    tech_wins = [s for s in tech_closed if s.get('outcome') in ['WIN', 'EXPIRED'] and float(s.get('return_pct', 0)) > 0]
    
    ai_win_rate = len(ai_wins) / len(ai_closed) * 100 if ai_closed else 0
    tech_win_rate = len(tech_wins) / len(tech_closed) * 100 if tech_closed else 0
    
    # By pattern
    pattern_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'returns': []})
    for s in closed:
        pattern = s.get('pattern', 'unknown')
        is_win = s.get('outcome') in ['WIN', 'EXPIRED'] and float(s.get('return_pct', 0)) > 0
        
        if is_win:
            pattern_stats[pattern]['wins'] += 1
        else:
            pattern_stats[pattern]['losses'] += 1
        
        pattern_stats[pattern]['returns'].append(float(s.get('return_pct', 0)))
    
    # By confirmation count
    conf_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for s in closed:
        count = int(s.get('signal_count', 1))
        is_win = s.get('outcome') in ['WIN', 'EXPIRED'] and float(s.get('return_pct', 0)) > 0
        
        if is_win:
            conf_stats[count]['wins'] += 1
        else:
            conf_stats[count]['losses'] += 1
    
    # Days held
    days_held = [int(s.get('days_held', 0)) for s in closed if s.get('days_held')]
    avg_days = sum(days_held) / len(days_held) if days_held else 0
    
    # Stop loss analysis
    stopped_out = [s for s in losses if abs(float(s.get('return_pct', 0)) - (-3.0)) < 0.5]
    stop_pct = len(stopped_out) / len(losses) * 100 if losses else 0
    
    return {
        'overview': {
            'total_signals': len(signals),
            'closed': len(closed),
            'active': len(active),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'expectancy': round(expectancy, 2),
            'avg_days_held': round(avg_days, 1),
            'stop_out_pct': round(stop_pct, 1)
        },
        'by_source': {
            'ai': {
                'total': len(ai_closed),
                'wins': len(ai_wins),
                'win_rate': round(ai_win_rate, 1)
            },
            'technical': {
                'total': len(tech_closed),
                'wins': len(tech_wins),
                'win_rate': round(tech_win_rate, 1)
            }
        },
        'by_pattern': {
            pattern: {
                'total': stats['wins'] + stats['losses'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': round(stats['wins'] / (stats['wins'] + stats['losses']) * 100, 1) if (stats['wins'] + stats['losses']) > 0 else 0,
                'avg_return': round(sum(stats['returns']) / len(stats['returns']), 2) if stats['returns'] else 0
            }
            for pattern, stats in pattern_stats.items()
        },
        'by_confirmation': {
            count: {
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': round(stats['wins'] / (stats['wins'] + stats['losses']) * 100, 1) if (stats['wins'] + stats['losses']) > 0 else 0
            }
            for count, stats in conf_stats.items()
        },
        'closed_signals': closed,
        'active_signals': active
    }

def generate_chart_data(analysis):
    """Generate data for matplotlib charts"""
    
    charts = {}
    
    # 1. Win rate by source
    charts['source_comparison'] = {
        'labels': ['AI Predictions', 'Technical Patterns'],
        'win_rates': [
            analysis['by_source']['ai']['win_rate'],
            analysis['by_source']['technical']['win_rate']
        ],
        'totals': [
            analysis['by_source']['ai']['total'],
            analysis['by_source']['technical']['total']
        ]
    }
    
    # 2. Pattern performance (top 10)
    patterns = sorted(
        [(p, s) for p, s in analysis['by_pattern'].items() if s['total'] >= 3],
        key=lambda x: x[1]['win_rate'],
        reverse=True
    )[:10]
    
    charts['pattern_performance'] = {
        'patterns': [p[0].replace('_', ' ').title() for p in patterns],
        'win_rates': [p[1]['win_rate'] for p in patterns],
        'totals': [p[1]['total'] for p in patterns]
    }
    
    # 3. Return distribution
    returns = [float(s.get('return_pct', 0)) for s in analysis['closed_signals']]
    charts['return_distribution'] = returns
    
    # 4. Confirmation count impact
    conf_sorted = sorted(analysis['by_confirmation'].items())
    charts['confirmation_impact'] = {
        'counts': [f"{c}x" for c, _ in conf_sorted],
        'win_rates': [s['win_rate'] for _, s in conf_sorted]
    }
    
    # 5. Equity curve
    closed_sorted = sorted(analysis['closed_signals'], key=lambda x: x.get('closed_date', ''))
    cumulative = 0
    equity_curve = []
    for s in closed_sorted:
        cumulative += float(s.get('return_pct', 0))
        equity_curve.append(cumulative)
    
    charts['equity_curve'] = {
        'dates': [s.get('closed_date', '') for s in closed_sorted],
        'returns': equity_curve
    }
    
    return charts

if __name__ == '__main__':
    print("Fetching signals from DynamoDB...")
    signals = get_all_signals()
    
    print(f"Analyzing {len(signals)} signals...")
    analysis = analyze_performance(signals)
    
    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("="*80)
    
    overview = analysis['overview']
    print(f"\nTotal Signals: {overview['total_signals']}")
    print(f"Closed Trades: {overview['closed']} | Active: {overview['active']}")
    print(f"Win Rate: {overview['win_rate']}% ({overview['wins']}W / {overview['losses']}L)")
    print(f"Average Win: +{overview['avg_win']}%")
    print(f"Average Loss: {overview['avg_loss']}%")
    print(f"Expectancy: {overview['expectancy']}% per trade")
    print(f"Average Hold Time: {overview['avg_days_held']} days")
    print(f"Stop Loss Hit Rate: {overview['stop_out_pct']}% of losses")
    
    print("\n" + "-"*80)
    print("BY SOURCE")
    print("-"*80)
    print(f"AI Predictions: {analysis['by_source']['ai']['win_rate']}% win rate ({analysis['by_source']['ai']['wins']}/{analysis['by_source']['ai']['total']})")
    print(f"Technical Patterns: {analysis['by_source']['technical']['win_rate']}% win rate ({analysis['by_source']['technical']['wins']}/{analysis['by_source']['technical']['total']})")
    
    print("\n" + "-"*80)
    print("TOP PATTERNS (min 3 trades)")
    print("-"*80)
    patterns = sorted(
        [(p, s) for p, s in analysis['by_pattern'].items() if s['total'] >= 3],
        key=lambda x: x[1]['win_rate'],
        reverse=True
    )
    for pattern, stats in patterns[:5]:
        print(f"{pattern:25} {stats['win_rate']:5.1f}% ({stats['wins']}/{stats['total']}) avg: {stats['avg_return']:+.2f}%")
    
    print("\n" + "-"*80)
    print("CONFIRMATION COUNT IMPACT")
    print("-"*80)
    for count in sorted(analysis['by_confirmation'].keys()):
        stats = analysis['by_confirmation'][count]
        total = stats['wins'] + stats['losses']
        print(f"{count}x Confirmed: {stats['win_rate']:5.1f}% ({stats['wins']}/{total})")
    
    # Generate chart data
    print("\nGenerating chart data...")
    charts = generate_chart_data(analysis)
    
    # Save to JSON for matplotlib script
    output = {
        'analysis': analysis,
        'charts': charts,
        'generated_at': datetime.now().isoformat()
    }
    
    with open('/tmp/performance_analysis.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print("\n✓ Analysis complete. Data saved to /tmp/performance_analysis.json")
    print("  Run generate_charts.py to create visualizations")
