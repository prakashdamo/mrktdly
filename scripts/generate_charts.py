#!/usr/bin/env python3
"""Generate performance charts using matplotlib"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

# Load analysis data
with open('/tmp/performance_analysis.json', 'r') as f:
    data = json.load(f)

analysis = data['analysis']
charts = data['charts']

# Set style
plt.style.use('dark_background')
fig_width = 12
fig_height = 8

# Create output directory
import os
os.makedirs('/home/prakash/marketdly/blog/images', exist_ok=True)

print("Generating charts...")

# Chart 1: Win Rate by Source
print("1. Win rate by source...")
fig, ax = plt.subplots(figsize=(10, 6))
sources = charts['source_comparison']['labels']
win_rates = charts['source_comparison']['win_rates']
totals = charts['source_comparison']['totals']

colors = ['#10b981', '#3b82f6']
bars = ax.bar(sources, win_rates, color=colors, alpha=0.8, edgecolor='white', linewidth=2)

# Add value labels
for i, (bar, total) in enumerate(zip(bars, totals)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 2,
            f'{height:.1f}%\n({total} trades)',
            ha='center', va='bottom', fontsize=12, fontweight='bold')

ax.set_ylabel('Win Rate (%)', fontsize=14, fontweight='bold')
ax.set_title('Win Rate by Signal Source', fontsize=16, fontweight='bold', pad=20)
ax.set_ylim(0, 100)
ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% Baseline')
ax.grid(axis='y', alpha=0.3)
ax.legend()

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/blog/images/win-rate-by-source.png', dpi=150, bbox_inches='tight')
plt.close()

# Chart 2: Pattern Performance
print("2. Pattern performance...")
fig, ax = plt.subplots(figsize=(12, 8))
patterns = charts['pattern_performance']['patterns']
win_rates = charts['pattern_performance']['win_rates']
totals = charts['pattern_performance']['totals']

y_pos = np.arange(len(patterns))
colors_pattern = ['#10b981' if wr >= 60 else '#ef4444' for wr in win_rates]

bars = ax.barh(y_pos, win_rates, color=colors_pattern, alpha=0.8, edgecolor='white', linewidth=1.5)

# Add labels
for i, (bar, total, wr) in enumerate(zip(bars, totals, win_rates)):
    ax.text(wr + 2, i, f'{wr:.1f}% ({total} trades)', 
            va='center', fontsize=10, fontweight='bold')

ax.set_yticks(y_pos)
ax.set_yticklabels(patterns, fontsize=11)
ax.set_xlabel('Win Rate (%)', fontsize=14, fontweight='bold')
ax.set_title('Pattern Performance (Min 3 Trades)', fontsize=16, fontweight='bold', pad=20)
ax.set_xlim(0, 110)
ax.axvline(x=50, color='gray', linestyle='--', alpha=0.5)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/blog/images/pattern-performance.png', dpi=150, bbox_inches='tight')
plt.close()

# Chart 3: Return Distribution
print("3. Return distribution...")
fig, ax = plt.subplots(figsize=(12, 6))
returns = charts['return_distribution']

bins = np.arange(-6, 10, 0.5)
n, bins, patches = ax.hist(returns, bins=bins, edgecolor='white', linewidth=1.5, alpha=0.8)

# Color bars
for i, patch in enumerate(patches):
    if bins[i] < 0:
        patch.set_facecolor('#ef4444')
    else:
        patch.set_facecolor('#10b981')

ax.axvline(x=0, color='white', linestyle='--', linewidth=2, label='Break-even')
ax.axvline(x=analysis['overview']['avg_win'], color='#10b981', linestyle=':', linewidth=2, label=f'Avg Win: +{analysis["overview"]["avg_win"]}%')
ax.axvline(x=analysis['overview']['avg_loss'], color='#ef4444', linestyle=':', linewidth=2, label=f'Avg Loss: {analysis["overview"]["avg_loss"]}%')

ax.set_xlabel('Return (%)', fontsize=14, fontweight='bold')
ax.set_ylabel('Number of Trades', fontsize=14, fontweight='bold')
ax.set_title('Return Distribution', fontsize=16, fontweight='bold', pad=20)
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/blog/images/return-distribution.png', dpi=150, bbox_inches='tight')
plt.close()

# Chart 4: Equity Curve
print("4. Equity curve...")
fig, ax = plt.subplots(figsize=(14, 7))
dates = charts['equity_curve']['dates']
returns = charts['equity_curve']['returns']

if dates and returns:
    ax.plot(range(len(returns)), returns, color='#10b981', linewidth=3, marker='o', markersize=4)
    ax.fill_between(range(len(returns)), returns, 0, alpha=0.3, color='#10b981')
    
    ax.axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('Trade Number', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Return (%)', fontsize=14, fontweight='bold')
    ax.set_title('Equity Curve (Cumulative Returns)', fontsize=16, fontweight='bold', pad=20)
    ax.grid(alpha=0.3)
    
    # Add final value
    final_return = returns[-1]
    ax.text(len(returns)-1, final_return, f'  {final_return:+.2f}%', 
            fontsize=12, fontweight='bold', va='center')

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/blog/images/equity-curve.png', dpi=150, bbox_inches='tight')
plt.close()

# Chart 5: Overview Dashboard
print("5. Overview dashboard...")
fig = plt.figure(figsize=(14, 10))
gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)

overview = analysis['overview']

# Big metrics
ax1 = fig.add_subplot(gs[0, 0])
ax1.text(0.5, 0.5, f"{overview['win_rate']}%", ha='center', va='center', 
         fontsize=48, fontweight='bold', color='#10b981')
ax1.text(0.5, 0.15, 'Win Rate', ha='center', va='center', fontsize=14, color='gray')
ax1.axis('off')

ax2 = fig.add_subplot(gs[0, 1])
ax2.text(0.5, 0.5, f"+{overview['expectancy']}%", ha='center', va='center', 
         fontsize=48, fontweight='bold', color='#10b981')
ax2.text(0.5, 0.15, 'Expectancy', ha='center', va='center', fontsize=14, color='gray')
ax2.axis('off')

ax3 = fig.add_subplot(gs[0, 2])
ax3.text(0.5, 0.5, f"{overview['closed']}", ha='center', va='center', 
         fontsize=48, fontweight='bold', color='#3b82f6')
ax3.text(0.5, 0.15, 'Total Trades', ha='center', va='center', fontsize=14, color='gray')
ax3.axis('off')

# Win/Loss breakdown
ax4 = fig.add_subplot(gs[1, :])
categories = ['Wins', 'Losses']
values = [overview['wins'], overview['losses']]
colors_wl = ['#10b981', '#ef4444']
bars = ax4.bar(categories, values, color=colors_wl, alpha=0.8, edgecolor='white', linewidth=2)
for bar, val in zip(bars, values):
    ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
            str(val), ha='center', va='bottom', fontsize=16, fontweight='bold')
ax4.set_ylabel('Count', fontsize=12, fontweight='bold')
ax4.set_title('Win/Loss Breakdown', fontsize=14, fontweight='bold')
ax4.grid(axis='y', alpha=0.3)

# Stats table
ax5 = fig.add_subplot(gs[2, :])
ax5.axis('off')
stats_text = f"""
Average Win: +{overview['avg_win']}%          Average Loss: {overview['avg_loss']}%
Average Hold: {overview['avg_days_held']} days          Stop Hit Rate: {overview['stop_out_pct']}%
Active Signals: {overview['active']}          Risk/Reward: {abs(overview['avg_win']/overview['avg_loss']):.2f}:1
"""
ax5.text(0.5, 0.5, stats_text, ha='center', va='center', fontsize=13, 
         family='monospace', bbox=dict(boxstyle='round', facecolor='#1e293b', alpha=0.8))

fig.suptitle('Performance Dashboard', fontsize=18, fontweight='bold', y=0.98)
plt.savefig('/home/prakash/marketdly/blog/images/performance-dashboard.png', dpi=150, bbox_inches='tight')
plt.close()

print("\n✓ All charts generated successfully!")
print("  Saved to: /home/prakash/marketdly/blog/images/")
print("\nGenerated files:")
print("  - win-rate-by-source.png")
print("  - pattern-performance.png")
print("  - return-distribution.png")
print("  - equity-curve.png")
print("  - performance-dashboard.png")
