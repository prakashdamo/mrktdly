"""
Export features + labels to CSV for ML training
"""
import boto3
import csv
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-features')

def export_to_csv(output_file='training_data.csv'):
    """Export all features with labels to CSV"""
    
    print('Scanning DynamoDB for training data...')
    
    # Scan all records
    response = table.scan()
    items = response['Items']
    
    # Continue scanning if there are more items
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    print(f'Found {len(items)} total records')
    
    # Filter records with labels
    labeled_items = [item for item in items if 'label' in item]
    print(f'Records with labels: {len(labeled_items)}')
    
    if not labeled_items:
        print('No labeled data found!')
        return
    
    # Define feature columns (exclude metadata)
    exclude_cols = ['ticker', 'date', 'timestamp', 'label', 'future_return_5d']
    feature_cols = sorted([k for k in labeled_items[0].keys() if k not in exclude_cols])
    
    # CSV columns: ticker, date, features..., label
    columns = ['ticker', 'date'] + feature_cols + ['label', 'future_return_5d']
    
    print(f'Features: {len(feature_cols)}')
    print(f'Columns: {columns[:5]}... + {len(columns)-5} more')
    print()
    
    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for item in labeled_items:
            # Convert all values to strings
            row = {col: item.get(col, '') for col in columns}
            writer.writerow(row)
    
    print(f'✅ Exported to {output_file}')
    print(f'Rows: {len(labeled_items)}')
    print(f'Columns: {len(columns)}')
    
    # Show label distribution
    labels = [int(item['label']) for item in labeled_items]
    positive = sum(labels)
    negative = len(labels) - positive
    print()
    print(f'Label Distribution:')
    print(f'  Positive (>3% move): {positive} ({positive/len(labels)*100:.1f}%)')
    print(f'  Negative (<=3% move): {negative} ({negative/len(labels)*100:.1f}%)')
    
    return output_file

if __name__ == '__main__':
    export_to_csv()
