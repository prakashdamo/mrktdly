"""
Preview email with ML predictions
"""
import boto3

dynamodb = boto3.resource('dynamodb')
predictions_table = dynamodb.Table('mrktdly-predictions')

# Get predictions for Nov 21
from boto3.dynamodb.conditions import Key
response = predictions_table.query(
    KeyConditionExpression=Key('date').eq('2025-11-21')
)

predictions = response.get('Items', [])
predictions.sort(key=lambda x: float(x.get('probability', 0)), reverse=True)

print('📧 EMAIL PREVIEW - AI Predictions Section')
print('=' * 70)
print()
print('🤖 AI Predictions')
print('Machine learning model predicts stocks likely to move >3% in next 5 days.')
print()

for i, pred in enumerate(predictions[:10], 1):
    ticker = pred.get('ticker', '')
    probability = float(pred.get('probability', 0))
    confidence = pred.get('confidence', 'medium')
    price = pred.get('price', '0')
    rsi = pred.get('rsi', '50')
    return_20d = pred.get('return_20d', '0')
    
    conf_emoji = '🟢' if confidence == 'high' else '🟡'
    
    print(f'{i}. {conf_emoji} {ticker:6} - {probability*100:.1f}% probability ({confidence})')
    print(f'   Price: ${price} | RSI: {rsi} | 20d Return: {return_20d}%')
    print()

print('=' * 70)
print(f'Total predictions: {len(predictions)}')
