import unittest
import boto3
import json
import time

class TestEndToEnd(unittest.TestCase):
    """Integration tests that verify the entire system works together"""
    
    @classmethod
    def setUpClass(cls):
        cls.lambda_client = boto3.client('lambda', region_name='us-east-1')
        cls.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    def test_ticker_analysis_caching(self):
        """Test that ticker analysis is cached properly"""
        # First call - should generate analysis
        response1 = self.lambda_client.invoke(
            FunctionName='mrktdly-ticker-analysis',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'POST',
                'body': json.dumps({'ticker': 'AAPL'})
            })
        )
        
        result1 = json.loads(response1['Payload'].read())
        self.assertEqual(result1['statusCode'], 200)
        
        # Second call - should use cache (faster)
        start = time.time()
        response2 = self.lambda_client.invoke(
            FunctionName='mrktdly-ticker-analysis',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'POST',
                'body': json.dumps({'ticker': 'AAPL'})
            })
        )
        duration = time.time() - start
        
        result2 = json.loads(response2['Payload'].read())
        self.assertEqual(result2['statusCode'], 200)
        # Cached response should be under 1 second
        self.assertLess(duration, 1.0)
    
    def test_precache_creates_cache_entries(self):
        """Test that pre-cache Lambda creates cache entries"""
        # Invoke pre-cache
        response = self.lambda_client.invoke(
            FunctionName='mrktdly-ticker-precache',
            InvocationType='RequestResponse'
        )
        
        result = json.loads(response['Payload'].read())
        self.assertEqual(result['statusCode'], 200)
        
        # Wait for async invocations to complete
        time.sleep(10)
        
        # Check that cache entries exist for popular tickers
        cache_table = self.dynamodb.Table('mrktdly-ticker-cache')
        response = cache_table.get_item(Key={'ticker': 'SPY'})
        self.assertIn('Item', response)
    
    def test_api_returns_analysis(self):
        """Test that API endpoint returns analysis"""
        # This would test the actual API Gateway endpoint
        pass

if __name__ == '__main__':
    unittest.main()
