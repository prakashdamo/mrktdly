#!/usr/bin/env python3
"""
Create hero image for swing trading patterns blog article
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Set style
plt.style.use('dark_background')

# Create figure
fig, ax = plt.subplots(figsize=(16, 9))
fig.patch.set_facecolor('#0a0f19')
ax.set_facecolor('#1a1f2e')

# Remove axes
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Title
title_text = "Swing Trading Patterns"
subtitle_text = "A Data-Driven Guide to Bull Flags, Cup & Handle, and Head & Shoulders"

ax.text(50, 75, title_text, 
        fontsize=48, fontweight='bold', 
        ha='center', va='center',
        color='white')

ax.text(50, 65, subtitle_text, 
        fontsize=20, 
        ha='center', va='center',
        color='#9ca3af')

# Draw simplified pattern illustrations
# Bull Flag
x_bull = np.linspace(10, 25, 50)
y_bull_pole = 30 + (x_bull - 10) * 1.5
y_bull_flag = 52 + np.sin((x_bull - 18) * 2) * 0.5

ax.plot(x_bull[:30], y_bull_pole[:30], color='#60a5fa', linewidth=3, label='Bull Flag')
ax.plot(x_bull[28:], y_bull_flag[28:], color='#60a5fa', linewidth=3)
ax.fill_between(x_bull[28:], y_bull_flag[28:] - 1, y_bull_flag[28:] + 1, 
                alpha=0.2, color='#fbbf24')

# Cup and Handle
x_cup = np.linspace(35, 60, 100)
y_cup = 45 - 8 * np.sin((x_cup - 35) / 25 * np.pi) ** 2
y_handle = y_cup.copy()
y_handle[80:] = y_handle[80] - (x_cup[80:] - x_cup[80]) * 0.3

ax.plot(x_cup[:80], y_cup[:80], color='#a78bfa', linewidth=3, label='Cup & Handle')
ax.plot(x_cup[78:], y_handle[78:], color='#a78bfa', linewidth=3)
ax.fill_between(x_cup[:80], y_cup[:80] - 0.5, y_cup[:80] + 0.5, 
                alpha=0.2, color='#a78bfa')

# Head and Shoulders
x_hs = np.array([70, 75, 80, 85, 90])
y_hs = np.array([40, 48, 42, 52, 41])

ax.plot(x_hs, y_hs, color='#f87171', linewidth=3, marker='o', 
        markersize=8, label='Head & Shoulders')
ax.plot([70, 90], [40, 40], 'r--', linewidth=2, alpha=0.5)
ax.scatter(x_hs[[1, 3]], y_hs[[1, 3]], s=150, c='#f87171', marker='v', zorder=5)

# Add labels
ax.text(17.5, 25, 'Bull Flag', fontsize=14, ha='center', color='#60a5fa', fontweight='bold')
ax.text(47.5, 32, 'Cup & Handle', fontsize=14, ha='center', color='#a78bfa', fontweight='bold')
ax.text(80, 32, 'Head & Shoulders', fontsize=14, ha='center', color='#f87171', fontweight='bold')

# Add decorative elements
# Gradient overlay at bottom
gradient = np.linspace(0, 1, 100).reshape(1, -1)
ax.imshow(gradient, extent=[0, 100, 0, 15], aspect='auto', 
          cmap='Blues', alpha=0.3, zorder=0)

# Add stats boxes
stats = [
    ('55-65%', 'Win Rate'),
    ('1:2', 'Risk/Reward'),
    ('5.2 days', 'Avg Hold')
]

x_start = 15
for i, (value, label) in enumerate(stats):
    x_pos = x_start + i * 25
    # Box
    rect = patches.FancyBboxPatch((x_pos - 8, 5), 16, 8,
                                   boxstyle="round,pad=0.5",
                                   edgecolor='#3b82f6',
                                   facecolor='#1e3a8a',
                                   alpha=0.3,
                                   linewidth=2)
    ax.add_patch(rect)
    
    # Text
    ax.text(x_pos, 11, value, fontsize=16, ha='center', 
            color='white', fontweight='bold')
    ax.text(x_pos, 7, label, fontsize=11, ha='center', 
            color='#9ca3af')

plt.tight_layout()
plt.savefig('/home/prakash/marketdly/website/blog/images/hero-swing-trading-patterns.png', 
            dpi=150, facecolor='#0a0f19', edgecolor='none', bbox_inches='tight')
print("Hero image created successfully!")
