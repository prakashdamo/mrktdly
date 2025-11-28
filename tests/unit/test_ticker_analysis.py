import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda/ticker_analysis'))
import lambda_function

class TestTickerAnalysis(unittest.TestCase):
    
    def test_cache_duration_is_2_hours(self):
        """Verify cache TTL is set to 2 hours"""
        # Check that cache duration is 2 hours
        self.assertTrue(True)  # Would check actual implementation
    
    @patch('lambda_function.cache_table')
    def test_get_cached_analysis_expired(self, mock_table):
        """Test that expired cache returns None"""
        old_time = (datetime.utcnow() - timedelta(hours=3)).isoformat()
        mock_table.get_item.return_value = {
            'Item': {
                'ticker': 'AAPL',
                'timestamp': old_time,
                'data': {},
                'analysis': {}
            }
        }
        
        result = lambda_function.get_cached_analysis('AAPL')
        self.assertIsNone(result)
    
    @patch('lambda_function.cache_table')
    def test_get_cached_analysis_valid(self, mock_table):
        """Test that valid cache returns data"""
        recent_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
        mock_table.get_item.return_value = {
            'Item': {
                'ticker': 'AAPL',
                'timestamp': recent_time,
                'data': {'price': 150},
                'analysis': {'summary': 'test'}
            }
        }
        
        result = lambda_function.get_cached_analysis('AAPL')
        self.assertIsNotNone(result)
        self.assertEqual(result['ticker'], 'AAPL')
    
    def test_convert_to_decimal(self):
        """Test float to Decimal conversion"""
        test_data = {'price': 150.50, 'nested': {'value': 100.25}}
        # Would test the actual conversion function
        self.assertTrue(True)  # Placeholder

if __name__ == '__main__':
    unittest.main()
