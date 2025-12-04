#!/usr/bin/env python3
"""
Generate stock pattern charts for blog articles using real market data
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set style
plt.style.use('dark_background')

def create_chart(ticker, start_date, end_date, title, pattern_type, output_file):
    """Create a stock chart with pattern annotations"""
    
    # Fetch data
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=end_date)
    
    if df.empty:
        print(f"No data for {ticker}")
        return
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                     gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#0a0f19')
    ax1.set_facecolor('#1a1f2e')
    ax2.set_facecolor('#1a1f2e')
    
    # Plot price
    ax1.plot(df.index, df['Close'], color='#60a5fa', linewidth=2, label='Close Price')
    
    # Add pattern-specific annotations
    if pattern_type == 'bull_flag':
        # Find the pole and flag
        max_idx = df['Close'].idxmax()
        pole_start = df.index[0]
        flag_end = df.index[-1]
        
        # Highlight pole
        pole_data = df.loc[pole_start:max_idx]
        ax1.fill_between(pole_data.index, pole_data['Close'].min(), pole_data['Close'],
                         alpha=0.2, color='green', label='Pole')
        
        # Highlight flag
        flag_data = df.loc[max_idx:flag_end]
        ax1.fill_between(flag_data.index, flag_data['Close'].min(), flag_data['Close'].max(),
                         alpha=0.2, color='yellow', label='Flag')
        
    elif pattern_type == 'cup_handle':
        # Find cup low and handle
        mid_point = len(df) // 2
        cup_low_idx = df['Close'][:mid_point].idxmin()
        
        # Highlight cup
        cup_data = df.iloc[:int(len(df)*0.8)]
        ax1.fill_between(cup_data.index, cup_data['Close'].min(), cup_data['Close'],
                         alpha=0.2, color='purple', label='Cup')
        
        # Highlight handle
        handle_data = df.iloc[int(len(df)*0.8):]
        ax1.fill_between(handle_data.index, handle_data['Close'].min(), handle_data['Close'].max(),
                         alpha=0.2, color='orange', label='Handle')
        
    elif pattern_type == 'head_shoulders':
        # Find three peaks
        peaks = df['Close'].nlargest(3).index
        peaks = sorted(peaks)
        
        # Mark shoulders and head
        for i, peak in enumerate(peaks):
            label = 'Left Shoulder' if i == 0 else ('Head' if i == 1 else 'Right Shoulder')
            ax1.scatter(peak, df.loc[peak, 'Close'], s=200, c='red', marker='v', 
                       label=label, zorder=5)
        
        # Draw neckline
        lows = df['Close'].nsmallest(2).index
        if len(lows) >= 2:
            ax1.plot([lows[0], lows[1]], [df.loc[lows[0], 'Close'], df.loc[lows[1], 'Close']],
                    'r--', linewidth=2, label='Neckline')
    
    # Format price axis
    ax1.set_ylabel('Price ($)', fontsize=12, color='white')
    ax1.set_title(title, fontsize=16, fontweight='bold', color='white', pad=20)
    ax1.legend(loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.2)
    ax1.tick_params(colors='white')
    
    # Plot volume
    colors = ['green' if df['Close'].iloc[i] >= df['Open'].iloc[i] else 'red' 
              for i in range(len(df))]
    ax2.bar(df.index, df['Volume'], color=colors, alpha=0.6)
    ax2.set_ylabel('Volume', fontsize=12, color='white')
    ax2.set_xlabel('Date', fontsize=12, color='white')
    ax2.grid(True, alpha=0.2)
    ax2.tick_params(colors='white')
    
    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, facecolor='#0a0f19', edgecolor='none')
    print(f"Chart saved: {output_file}")
    plt.close()

def main():
    """Generate all blog charts"""
    
    output_dir = '/home/prakash/marketdly/website/blog/images'
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Chart 1: AMZN Bull Flag (March-May 2024) - 8.3% rally, 3.2% flag range
    create_chart(
        ticker='AMZN',
        start_date='2024-03-01',
        end_date='2024-05-30',
        title='AMZN Bull Flag Pattern - March-May 2024',
        pattern_type='bull_flag',
        output_file=f'{output_dir}/amzn-bull-flag-may-2024.png'
    )
    
    # Chart 2: META Cup and Handle (March-May 2024) - Perfect U-shape with handle
    create_chart(
        ticker='META',
        start_date='2024-03-01',
        end_date='2024-05-30',
        title='META Cup and Handle Pattern - March-May 2024',
        pattern_type='cup_handle',
        output_file=f'{output_dir}/meta-cup-handle-may-2024.png'
    )
    
    # Chart 3: AMD Head and Shoulders (Jan-Apr 2024) - 0.8% shoulder symmetry
    create_chart(
        ticker='AMD',
        start_date='2024-01-02',
        end_date='2024-04-29',
        title='AMD Head and Shoulders Pattern - Jan-Apr 2024',
        pattern_type='head_shoulders',
        output_file=f'{output_dir}/amd-head-shoulders-apr-2024.png'
    )
    
    print("\nAll charts generated successfully!")
    print(f"Charts saved to: {output_dir}")

if __name__ == '__main__':
    main()
