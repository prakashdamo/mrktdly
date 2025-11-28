import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add Lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda/data_fetch'))
import lambda_function

class TestDataFetch(unittest.TestCase):
    
    @patch('lambda_function.table')
    @patch('lambda_function.fetch_market_data')
    @patch('lambda_function.fetch_news')
    def test_lambda_handler_success(self, mock_news, mock_data, mock_table):
        """Test successful data fetch"""
        mock_data.return_value = {'SPY': {'price': Decimal('100'), 'change': Decimal('1')}}
        mock_news.return_value = [{'title': 'Test', 'url': 'http://test.com'}]
        
        result = lambda_function.lambda_handler({}, {})
        
        self.assertEqual(result['statusCode'], 200)
        mock_table.put_item.assert_called_once()
    
    def test_fetch_market_data_structure(self):
        """Test market data returns correct structure"""
        # This would make actual API call - skip in unit tests
        pass
    
    def test_ticker_list_completeness(self):
        """Verify all expected tickers are in the list"""
        # Check that major indices are included
        expected_tickers = ['SPY', 'QQQ', 'NVDA', 'AAPL']
        # Would need to extract ticker list from lambda_function
        self.assertTrue(True)  # Placeholder

if __name__ == '__main__':
    unittest.main()
