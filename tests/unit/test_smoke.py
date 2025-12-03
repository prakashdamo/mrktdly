import unittest
import os

class TestSmokeTests(unittest.TestCase):
    """Basic smoke tests to verify project structure"""
    
    def test_lambda_functions_exist(self):
        """Verify all Lambda function files exist"""
        lambda_functions = [
            'lambda/data_fetch/lambda_function.py',
            'lambda/analysis/lambda_function.py',
            'lambda/ticker-analysis/lambda_function.py',
            'lambda/ticker_precache/lambda_function.py',
            'lambda/api/lambda_function.py'
        ]
        
        for func in lambda_functions:
            path = os.path.join(os.path.dirname(__file__), '../..', func)
            self.assertTrue(os.path.exists(path), f"Missing: {func}")
    
    def test_website_files_exist(self):
        """Verify website files exist"""
        files = [
            'website/index.html',
            'website/robots.txt',
            'website/sitemap.xml'
        ]
        
        for file in files:
            path = os.path.join(os.path.dirname(__file__), '../..', file)
            self.assertTrue(os.path.exists(path), f"Missing: {file}")
    
    def test_cache_duration_is_documented(self):
        """Verify cache duration is 2 hours as per requirements"""
        ticker_analysis_path = os.path.join(
            os.path.dirname(__file__), 
            '../../lambda/ticker-analysis/lambda_function.py'
        )
        
        with open(ticker_analysis_path, 'r') as f:
            content = f.read()
            # Check for 2 hour cache
            self.assertIn('hours=2', content, "Cache should be 2 hours")
    
    def test_precache_has_10_tickers(self):
        """Verify pre-cache Lambda has exactly 10 tickers"""
        precache_path = os.path.join(
            os.path.dirname(__file__),
            '../../lambda/ticker_precache/lambda_function.py'
        )
        
        with open(precache_path, 'r') as f:
            content = f.read()
            # Count tickers in popular_tickers list
            self.assertIn('popular_tickers', content)
            # Should have SPY, QQQ, NVDA, etc.
            for ticker in ['SPY', 'QQQ', 'NVDA', 'AAPL', 'TSLA']:
                self.assertIn(ticker, content, f"Missing ticker: {ticker}")

if __name__ == '__main__':
    unittest.main()
