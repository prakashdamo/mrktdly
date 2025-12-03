"""
Swing trade pattern scanner
Runs daily to detect breakout opportunities
"""
import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
price_history_table = dynamodb.Table('mrktdly-price-history')
swing_signals_table = dynamodb.Table('mrktdly-swing-signals')
cache_table = dynamodb.Table('mrktdly-ticker-cache')

TICKERS = [
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO',
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'ORCL', 'ADBE', 'CRM', 'NFLX', 'AMD', 'INTC',
    'TSM', 'ASML', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ARM', 'MCHP', 'ON',
    'PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS', 'PANW', 'WDAY', 'NOW', 'TEAM', 'MDB', 'HUBS',
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL', 'SQ', 'COIN', 'HOOD',
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN',
    'WMT', 'COST', 'HD', 'TGT', 'LOW', 'NKE', 'SBUX', 'MCD', 'DIS', 'BKNG', 'ABNB',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
    'BA', 'CAT', 'GE', 'RTX', 'LMT', 'HON', 'UPS', 'UNP', 'DE', 'MMM',
    'F', 'GM', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
    'MSTR', 'RIOT', 'MARA', 'CLSK',
    'GME', 'AMC',
    'RKLB', 'IONQ', 'SMCI', 'APP', 'CVNA', 'UPST', 'SOFI', 'AFRM'
]

def lambda_handler(event, context):
    """Scan all tickers for swing trade patterns"""
    today = datetime.now().strftime('%Y-%m-%d')
    signals_found = []
    
    for ticker in TICKERS:
        try:
            signal = scan_ticker(ticker, today)
            if signal:
                signals_found.append(signal)
                # Store in DynamoDB
                swing_signals_table.put_item(Item=signal)
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")
    
    # Precache API response
    try:
        cache_key = f"swing-signals-{today}-all-0.0"
        cache_data = json.dumps({
            'date': today,
            'count': len(signals_found),
            'signals': signals_found
        }, default=str)
        ttl = int((datetime.now() + timedelta(hours=24)).timestamp())
        cache_table.put_item(Item={
            'ticker': cache_key,
            'data': cache_data,
            'ttl': ttl,
            'timestamp': datetime.now().isoformat()
        })
        print(f"Precached swing signals: {len(signals_found)} signals")
    except Exception as e:
        print(f"Error precaching: {e}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'date': today,
            'signals_found': len(signals_found),
            'signals': signals_found
        }, default=str)
    }

def scan_ticker(ticker, today):
    """Detect swing trade patterns"""
    # Get last 60 days of price data
    end_date = datetime.strptime(today, '%Y-%m-%d')
    start_date = end_date - timedelta(days=90)  # Extra buffer for weekends
    
    response = price_history_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
            start_date.strftime('%Y-%m-%d'),
            today
        ),
        ScanIndexForward=True
    )
    
    history = response['Items']
    if len(history) < 50:
        return None
    
    # Take last 60 trading days
    history = history[-60:]
    
    # Calculate RSI for overbought filter
    closes = [float(d['close']) for d in history]
    current_rsi = calculate_rsi(closes, 14)
    
    # FILTER: Reject overbought entries (RSI >= 60)
    # Analysis showed failing signals had avg RSI 52.4 vs winning 46.9
    # Worst performers: REGN (RSI 83.4), MRK (RSI 89.0), AVGO (RSI 68.5)
    if current_rsi and current_rsi >= 60:
        return None
    
    # Try each pattern detector
    signal = detect_consolidation_breakout(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_bull_flag(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_ascending_triangle(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_momentum_alignment(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_volume_breakout(ticker, history, today)
    if signal:
        return signal
    
    # NEW: High win-rate patterns from historical analysis
    signal = detect_reversal_after_decline(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_gap_up_hold(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_ma20_pullback(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_cup_and_handle(ticker, history, today)
    if signal:
        return signal
    
    signal = detect_double_bottom(ticker, history, today)
    if signal:
        return signal
    
    return None

def detect_consolidation_breakout(ticker, history, today):
    """Detect consolidation breakout pattern (IMPROVED)"""
    if len(history) < 40:
        return None
        
    consolidation = history[-40:-5]
    breakout_period = history[-5:]
    
    # Calculate consolidation range
    highs = [float(d['high']) for d in consolidation]
    lows = [float(d['low']) for d in consolidation]
    
    resistance = max(highs)
    support = min(lows)
    range_pct = (resistance - support) / support
    
    # Must be consolidating (< 10% range)
    if range_pct > 0.10:
        return None
    
    # Check for breakout - need 2 consecutive days above resistance
    if len(breakout_period) < 2:
        return None
    
    latest = breakout_period[-1]
    previous = breakout_period[-2]
    
    latest_close = float(latest['close'])
    latest_high = float(latest['high'])
    latest_low = float(latest['low'])
    latest_volume = float(latest['volume'])
    
    prev_close = float(previous['close'])
    
    # Both days must close above resistance
    if latest_close <= resistance * 1.02 or prev_close <= resistance * 1.01:
        return None
    
    # Latest close must be in top 25% of daily range (strong close)
    daily_range = latest_high - latest_low
    if daily_range > 0:
        close_position = (latest_close - latest_low) / daily_range
        if close_position < 0.75:
            return None
    
    # Volume confirmation: 2x above average (stricter)
    avg_volume = sum(float(d['volume']) for d in consolidation) / len(consolidation)
    volume_surge = latest_volume / avg_volume
    
    if volume_surge < 2.0:
        return None
    
    # Calculate targets
    range_size = resistance - support
    target = latest_close + (range_size * 2)
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    # Require min 2:1 R/R
    if risk_reward < 2.0:
        return None
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'consolidation_breakout',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(resistance, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_bull_flag(ticker, history, today):
    """Detect bull flag pattern"""
    if len(history) < 20:
        return None
    
    # Look for strong uptrend (flagpole): 20%+ move in 5-10 days
    flagpole_start = history[-15:-8]
    flagpole_end = history[-8:-3]
    
    if not flagpole_start or not flagpole_end:
        return None
    
    pole_start_price = float(flagpole_start[0]['low'])
    pole_end_price = float(flagpole_end[-1]['high'])
    pole_move = (pole_end_price - pole_start_price) / pole_start_price
    
    # Need 20%+ uptrend for flagpole
    if pole_move < 0.20:
        return None
    
    # Flag consolidation: 3-8 days, tight range
    flag_period = history[-8:-1]
    flag_highs = [float(d['high']) for d in flag_period]
    flag_lows = [float(d['low']) for d in flag_period]
    
    flag_resistance = max(flag_highs)
    flag_support = min(flag_lows)
    flag_range = (flag_resistance - flag_support) / flag_support
    
    # Flag should be tight (< 8% range)
    if flag_range > 0.08:
        return None
    
    # Check for breakout
    latest = history[-1]
    latest_close = float(latest['close'])
    latest_volume = float(latest['volume'])
    
    # Breakout above flag resistance
    if latest_close <= flag_resistance * 1.01:
        return None
    
    # Volume confirmation
    flag_avg_volume = sum(float(d['volume']) for d in flag_period) / len(flag_period)
    volume_surge = latest_volume / flag_avg_volume
    
    if volume_surge < 1.3:
        return None
    
    # Target: flagpole height projected from breakout
    flagpole_height = pole_end_price - pole_start_price
    target = latest_close + flagpole_height
    risk = latest_close - flag_support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'bull_flag',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(flag_support, 2))),
        'resistance': Decimal(str(round(flag_resistance, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_ascending_triangle(ticker, history, today):
    """Detect ascending triangle pattern (IMPROVED)"""
    if len(history) < 30:
        return None
    
    # Look at 15-30 day formation
    triangle_period = history[-30:-1]
    
    # Find flat resistance (multiple tests at similar level)
    highs = [float(d['high']) for d in triangle_period]
    
    # Get top 4 highs (require 4 tests instead of 3)
    sorted_highs = sorted(highs, reverse=True)[:4]
    resistance = sum(sorted_highs) / 4
    
    # Check if resistance is flat (within 2%)
    resistance_range = (max(sorted_highs) - min(sorted_highs)) / resistance
    if resistance_range > 0.02:
        return None
    
    # Check for rising support (higher lows)
    lows = [float(d['low']) for d in triangle_period]
    
    # Split into thirds and check if lows are rising
    third = len(lows) // 3
    early_lows = lows[:third]
    mid_lows = lows[third:2*third]
    late_lows = lows[2*third:]
    
    if not (early_lows and mid_lows and late_lows):
        return None
    
    early_low = min(early_lows)
    mid_low = min(mid_lows)
    late_low = min(late_lows)
    
    # Lows should be rising
    if not (mid_low > early_low and late_low > mid_low):
        return None
    
    # Check for breakout
    latest = history[-1]
    latest_close = float(latest['close'])
    latest_volume = float(latest['volume'])
    
    # Breakout above resistance
    if latest_close <= resistance * 1.02:
        return None
    
    # Volume confirmation
    avg_volume = sum(float(d['volume']) for d in triangle_period) / len(triangle_period)
    volume_surge = latest_volume / avg_volume
    
    if volume_surge < 1.5:
        return None
    
    # Target: triangle height projected upward
    triangle_height = resistance - early_low
    target = latest_close + triangle_height
    risk = latest_close - late_low
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    # Require min 1.5:1 R/R
    if risk_reward < 1.5:
        return None
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'ascending_triangle',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(late_low, 2))),
        'resistance': Decimal(str(round(resistance, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }


def detect_momentum_alignment(ticker, history, today):
    """Detect RSI and MACD trending up - strong momentum (BALANCED)"""
    if len(history) < 50:
        return None
    
    closes = [float(d['close']) for d in history]
    volumes = [float(d['volume']) for d in history]
    
    # Calculate daily RSI (14 period)
    daily_rsi = calculate_rsi(closes, 14)
    if daily_rsi is None:
        return None
    
    # RSI must be between 55-75 (strong but not extreme overbought)
    if daily_rsi < 55 or daily_rsi > 75:
        return None
    
    # Calculate MACD
    macd_line, signal_line = calculate_macd(closes)
    if macd_line is None or signal_line is None:
        return None
    
    # MACD must be above signal line (bullish)
    if macd_line <= signal_line:
        return None
    
    # Price must be above 20-day and 50-day MA
    ma_20 = sum(closes[-20:]) / 20
    ma_50 = sum(closes[-50:]) / 50
    latest_close = closes[-1]
    
    if latest_close <= ma_20 or latest_close <= ma_50:
        return None
    
    # Golden cross: 20 MA must be above 50 MA
    if ma_20 <= ma_50:
        return None
    
    # Volume should be near or above average (not strict)
    avg_volume = sum(volumes[-20:]) / 20
    latest_volume = volumes[-1]
    volume_surge = latest_volume / avg_volume
    
    if volume_surge < 0.8:  # Allow slightly below average
        return None
    
    # Calculate support and target
    recent_lows = [float(d['low']) for d in history[-20:]]
    support = min(recent_lows)
    
    # Target: 10% above current
    target = latest_close * 1.10
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    # Require minimum 2:1 R/R (balanced)
    if risk_reward < 2.0:
        return None
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'momentum_alignment',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(ma_20, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    if len(prices) < slow + signal:
        return None, None
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    if ema_fast is None or ema_slow is None:
        return None, None
    
    macd_line = ema_fast - ema_slow
    
    # Calculate signal line (EMA of MACD)
    macd_values = []
    for i in range(len(prices) - slow + 1):
        subset = prices[:slow + i]
        if len(subset) >= slow:
            fast_ema = calculate_ema(subset, fast)
            slow_ema = calculate_ema(subset, slow)
            if fast_ema and slow_ema:
                macd_values.append(fast_ema - slow_ema)
    
    if len(macd_values) < signal:
        return macd_line, macd_line * 0.9
    
    signal_line = sum(macd_values[-signal:]) / signal
    
    return macd_line, signal_line

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

def detect_volume_breakout(ticker, history, today):
    """Detect volume breakout - 3x+ volume with new 20-day high"""
    if len(history) < 25:
        return None
    
    recent = history[-20:]
    latest = history[-1]
    previous = history[-2]
    
    latest_close = float(latest['close'])
    latest_volume = float(latest['volume'])
    prev_volume = float(previous['volume'])
    
    # Calculate average volume (exclude today)
    avg_volume = sum(float(d['volume']) for d in history[-21:-1]) / 20
    
    # Volume must be 3x+ average
    volume_surge = latest_volume / avg_volume
    if volume_surge < 3.0:
        return None
    
    # Check if yesterday also had high volume (2+ consecutive days)
    prev_volume_surge = prev_volume / avg_volume
    if prev_volume_surge < 2.0:
        return None
    
    # Price must be making new 20-day high
    recent_highs = [float(d['high']) for d in recent[:-1]]  # Exclude today
    twenty_day_high = max(recent_highs)
    
    if latest_close <= twenty_day_high:
        return None
    
    # Price must be up on the day
    prev_close = float(previous['close'])
    if latest_close <= prev_close:
        return None
    
    # Calculate support and target
    recent_lows = [float(d['low']) for d in recent]
    support = min(recent_lows)
    
    # Target: 15% above current (strong momentum play)
    target = latest_close * 1.15
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    # Only signal if R/R > 1.5
    if risk_reward < 1.5:
        return None
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'volume_breakout',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(twenty_day_high, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_reversal_after_decline(ticker, history, today):
    """
    Reversal After Decline - 68.9% historical win rate
    Strong up day after 3+ down days with volume confirmation
    """
    if len(history) < 10:
        return None
    
    recent = history[-6:]
    latest = recent[-1]
    
    closes = [float(d['close']) for d in recent]
    volumes = [float(d['volume']) for d in recent]
    
    # Check for 3+ down days before today
    down_days = 0
    for i in range(len(closes) - 2, 0, -1):
        if closes[i] < closes[i-1]:
            down_days += 1
        else:
            break
    
    if down_days < 3:
        return None
    
    # Today must be strong up day (>2%)
    today_change = (closes[-1] - closes[-2]) / closes[-2] * 100
    if today_change < 2:
        return None
    
    # Volume confirmation (1.5x average)
    avg_volume = sum(volumes[:-1]) / (len(volumes) - 1)
    if volumes[-1] < avg_volume * 1.5:
        return None
    
    # Calculate support and target
    recent_lows = [float(d['low']) for d in history[-20:]]
    support = min(recent_lows)
    
    latest_close = closes[-1]
    target = latest_close * 1.08  # 8% target (conservative)
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    if risk_reward < 1.5:
        return None
    
    volume_surge = volumes[-1] / avg_volume
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'reversal_after_decline',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(closes[-2], 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'historical_win_rate': Decimal('68.9'),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_gap_up_hold(ticker, history, today):
    """
    Gap Up Hold - 67.3% historical win rate
    Gap up 2%+ that holds for 2+ days with volume
    """
    if len(history) < 5:
        return None
    
    recent = history[-5:]
    latest = recent[-1]
    prev = recent[-2]
    day_before = recent[-3]
    
    latest_close = float(latest['close'])
    latest_low = float(latest['low'])
    prev_close = float(prev['close'])
    prev_low = float(prev['low'])
    day_before_close = float(day_before['close'])
    
    # Check for gap up (2%+)
    gap_pct = (prev_close - day_before_close) / day_before_close * 100
    if gap_pct < 2:
        return None
    
    # Gap must hold (not fill) for 2 days
    if prev_low <= day_before_close or latest_low <= day_before_close:
        return None
    
    # Volume confirmation
    volumes = [float(d['volume']) for d in history[-20:]]
    avg_volume = sum(volumes[:-2]) / (len(volumes) - 2)
    
    if volumes[-2] < avg_volume * 2:  # Gap day had high volume
        return None
    
    # Calculate support and target
    support = min(prev_low, latest_low)
    target = latest_close * 1.08  # 8% target
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    if risk_reward < 1.5:
        return None
    
    volume_surge = volumes[-2] / avg_volume
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'gap_up_hold',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(day_before_close, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'historical_win_rate': Decimal('67.3'),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_ma20_pullback(ticker, history, today):
    """
    MA20 Pullback + RSI - 60.2% historical win rate
    Price touches 20 MA with RSI 30-40 (oversold bounce)
    """
    if len(history) < 25:
        return None
    
    closes = [float(d['close']) for d in history]
    latest_close = closes[-1]
    
    # Calculate 20 MA
    ma_20 = sum(closes[-20:]) / 20
    
    # Price must be within 2% of 20 MA
    distance_from_ma = abs(latest_close - ma_20) / ma_20
    if distance_from_ma > 0.02:
        return None
    
    # Price should be at or slightly above MA (bounce, not breakdown)
    if latest_close < ma_20 * 0.98:
        return None
    
    # Calculate RSI
    rsi = calculate_rsi(closes, 14)
    if rsi is None:
        return None
    
    # RSI must be 30-40 (oversold but recovering)
    if rsi < 30 or rsi > 40:
        return None
    
    # Calculate support and target
    recent_lows = [float(d['low']) for d in history[-20:]]
    support = min(recent_lows)
    
    target = latest_close * 1.08  # 8% target
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    if risk_reward < 1.5:
        return None
    
    # Volume check (optional, not strict)
    volumes = [float(d['volume']) for d in history]
    avg_volume = sum(volumes[-20:]) / 20
    volume_surge = volumes[-1] / avg_volume
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'ma20_pullback',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(ma_20, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'historical_win_rate': Decimal('60.2'),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_cup_and_handle(ticker, history, today):
    """Cup and Handle: U-shaped recovery + handle pullback + breakout"""
    if len(history) < 60:
        return None
    
    closes = [float(d['close']) for d in history]
    highs = [float(d['high']) for d in history]
    lows = [float(d['low']) for d in history]
    volumes = [float(d['volume']) for d in history]
    
    # Cup: 30-50 day U-shaped pattern
    cup_period = history[-50:-10]
    cup_closes = [float(d['close']) for d in cup_period]
    
    # Find cup high (left rim)
    cup_high = max(cup_closes[:10])
    
    # Find cup bottom (middle)
    cup_low = min(cup_closes[15:25])
    
    # Cup depth should be 12-33%
    cup_depth = (cup_high - cup_low) / cup_high
    if cup_depth < 0.12 or cup_depth > 0.33:
        return None
    
    # Right side should recover to near cup high
    right_side = cup_closes[-10:]
    if max(right_side) < cup_high * 0.95:
        return None
    
    # Handle: Last 5-10 days pullback (3-12%)
    handle = closes[-10:]
    handle_high = max(handle[:5])
    handle_low = min(handle[-5:])
    handle_depth = (handle_high - handle_low) / handle_high
    
    if handle_depth < 0.03 or handle_depth > 0.12:
        return None
    
    # Breakout: Latest close above cup high
    latest_close = closes[-1]
    if latest_close < cup_high * 1.01:
        return None
    
    # Volume confirmation: breakout volume > average
    avg_volume = sum(volumes[-20:]) / 20
    latest_volume = volumes[-1]
    volume_surge = latest_volume / avg_volume
    
    if volume_surge < 1.2:
        return None
    
    # Target: Cup depth projected from breakout
    target = latest_close + (cup_high - cup_low)
    support = handle_low
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    if risk_reward < 2.0:
        return None
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'cup_and_handle',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(cup_high, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'historical_win_rate': Decimal('65.0'),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }

def detect_double_bottom(ticker, history, today):
    """Double Bottom: Two lows at similar price + volume breakout"""
    if len(history) < 40:
        return None
    
    closes = [float(d['close']) for d in history]
    lows = [float(d['low']) for d in history]
    highs = [float(d['high']) for d in history]
    volumes = [float(d['volume']) for d in history]
    
    # Look for two distinct lows in last 30 days
    recent = history[-30:]
    recent_lows = [float(d['low']) for d in recent]
    
    # Find first bottom (lowest point in first half)
    first_half = recent_lows[:15]
    first_bottom = min(first_half)
    first_bottom_idx = first_half.index(first_bottom)
    
    # Find second bottom (lowest point in second half)
    second_half = recent_lows[15:]
    second_bottom = min(second_half)
    second_bottom_idx = 15 + second_half.index(second_bottom)
    
    # Bottoms should be within 3% of each other
    bottom_diff = abs(first_bottom - second_bottom) / first_bottom
    if bottom_diff > 0.03:
        return None
    
    # Peak between bottoms (neckline)
    between = recent_lows[first_bottom_idx:second_bottom_idx]
    if not between:
        return None
    
    neckline = max(between)
    
    # Neckline should be 8-20% above bottoms
    neckline_height = (neckline - first_bottom) / first_bottom
    if neckline_height < 0.08 or neckline_height > 0.20:
        return None
    
    # Current price should be breaking above neckline
    latest_close = closes[-1]
    if latest_close < neckline * 1.01:
        return None
    
    # Volume on breakout should be elevated
    avg_volume = sum(volumes[-20:]) / 20
    latest_volume = volumes[-1]
    volume_surge = latest_volume / avg_volume
    
    if volume_surge < 1.3:
        return None
    
    # Target: Neckline height projected from breakout
    pattern_height = neckline - first_bottom
    target = latest_close + pattern_height
    support = max(first_bottom, second_bottom)
    
    risk = latest_close - support
    reward = target - latest_close
    risk_reward = reward / risk if risk > 0 else 0
    
    if risk_reward < 1.8:
        return None
    
    return {
        'date': today,
        'ticker': ticker,
        'pattern': 'double_bottom',
        'entry': Decimal(str(round(latest_close, 2))),
        'support': Decimal(str(round(support, 2))),
        'resistance': Decimal(str(round(neckline, 2))),
        'target': Decimal(str(round(target, 2))),
        'risk_reward': Decimal(str(round(risk_reward, 2))),
        'volume_surge': Decimal(str(round(volume_surge, 2))),
        'historical_win_rate': Decimal('62.0'),
        'status': 'active',
        'detected_at': datetime.now().isoformat()
    }
