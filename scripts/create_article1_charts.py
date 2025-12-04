#!/usr/bin/env python3
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

plt.style.use('dark_background')

# Get data around April 9, 2025
spy = yf.Ticker('SPY').history(start='2025-03-15', end='2025-04-30')

# Chart 1: Hero Image
fig, ax = plt.subplots(figsize=(16, 9))
fig.patch.set_facecolor('#0a0f19')
ax.set_facecolor('#1a1f2e')
ax.axis('off')
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)

ax.text(50, 70, "The 10.5% Day", fontsize=52, fontweight='bold', ha='center', color='white')
ax.text(50, 58, "Trading the Biggest Single-Day Rally of 2025", fontsize=22, ha='center', color='#9ca3af')

# Draw dramatic upward arrow
arrow_x = np.linspace(20, 80, 100)
arrow_y = 25 + (arrow_x - 20) * 0.4
ax.plot(arrow_x, arrow_y, color='#10b981', linewidth=8)
ax.scatter([80], [49], s=2000, marker='^', color='#10b981', zorder=5)

# Stats
stats = [('April 9, 2025', 'Date'), ('+10.50%', 'Gain'), ('$545.49', 'Close')]
for i, (val, label) in enumerate(stats):
    x = 20 + i * 30
    ax.text(x, 12, val, fontsize=18, ha='center', color='white', fontweight='bold')
    ax.text(x, 7, label, fontsize=13, ha='center', color='#9ca3af')

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/website/blog/images/hero-10-percent-day.png', 
            dpi=150, facecolor='#0a0f19', bbox_inches='tight')
print("Hero image created")

# Chart 2: The actual day with volume
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
fig.patch.set_facecolor('#0a0f19')
ax1.set_facecolor('#1a1f2e')
ax2.set_facecolor('#1a1f2e')

# Price chart
ax1.plot(spy.index, spy['Close'], color='#60a5fa', linewidth=2)
april_9_date = pd.Timestamp('2025-04-09')
april_9 = spy.loc[april_9_date]
ax1.scatter([april_9_date], [april_9['Close']], s=300, c='#10b981', marker='o', zorder=5, edgecolors='white', linewidths=2)
ax1.axvline(april_9_date, color='#10b981', linestyle='--', alpha=0.5, linewidth=2)
ax1.text(april_9_date, april_9['Close'] + 20, '+10.5%', fontsize=14, ha='center', color='#10b981', fontweight='bold')

ax1.set_ylabel('SPY Price ($)', fontsize=12, color='white')
ax1.set_title('SPY Around April 9, 2025 - The 10.5% Rally', fontsize=16, fontweight='bold', color='white', pad=20)
ax1.grid(True, alpha=0.2)
ax1.tick_params(colors='white')

# Volume
colors = ['green' if spy['Close'].iloc[i] >= spy['Open'].iloc[i] else 'red' for i in range(len(spy))]
ax2.bar(spy.index, spy['Volume'], color=colors, alpha=0.6)
ax2.axvline(april_9_date, color='#10b981', linestyle='--', alpha=0.5, linewidth=2)
ax2.set_ylabel('Volume', fontsize=12, color='white')
ax2.set_xlabel('Date', fontsize=12, color='white')
ax2.grid(True, alpha=0.2)
ax2.tick_params(colors='white')

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/website/blog/images/spy-april-9-rally.png', 
            dpi=150, facecolor='#0a0f19', bbox_inches='tight')
print("Rally chart created")

# Chart 3: What happened after
spy_after = yf.Ticker('SPY').history(start='2025-04-09', end='2025-04-25')
fig, ax = plt.subplots(figsize=(14, 8))
fig.patch.set_facecolor('#0a0f19')
ax.set_facecolor('#1a1f2e')

ax.plot(spy_after.index, spy_after['Close'], color='#60a5fa', linewidth=3, marker='o', markersize=6)
ax.axhline(spy_after['Close'].iloc[0], color='yellow', linestyle='--', alpha=0.5, linewidth=2, label='April 9 Close')
ax.scatter([spy_after.index[0]], [spy_after['Close'].iloc[0]], s=300, c='#10b981', marker='o', zorder=5, edgecolors='white', linewidths=2)

# Annotate the drop
ax.annotate('', xy=(spy_after.index[1], spy_after['Close'].iloc[1]), 
            xytext=(spy_after.index[0], spy_after['Close'].iloc[0]),
            arrowprops=dict(arrowstyle='->', color='red', lw=3))
ax.text(spy_after.index[1], spy_after['Close'].iloc[1] - 10, '-4.4% next day', 
        fontsize=12, ha='center', color='red', fontweight='bold')

ax.set_ylabel('SPY Price ($)', fontsize=12, color='white')
ax.set_xlabel('Date', fontsize=12, color='white')
ax.set_title('What Happened After the 10.5% Rally', fontsize=16, fontweight='bold', color='white', pad=20)
ax.legend(loc='upper right', framealpha=0.9)
ax.grid(True, alpha=0.2)
ax.tick_params(colors='white')

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/website/blog/images/spy-after-rally.png', 
            dpi=150, facecolor='#0a0f19', bbox_inches='tight')
print("After-rally chart created")

print("\nAll charts for Article 1 created successfully!")
