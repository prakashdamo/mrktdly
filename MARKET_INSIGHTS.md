# Market Insights Page

Beautiful visualizations of year-to-date market data.

## Features

### 📊 Charts
1. **Top Performers YTD** - Bar chart of best performing stocks
2. **Market Volatility Trends** - Time series of average volatility
3. **Sector Heatmap** - Performance by sector
4. **Volume Patterns** - Trading volume trends for major indices
5. **RSI Distribution** - Current market momentum histogram
6. **Correlation Matrix** - Correlation between major indices

### 📈 Stats Dashboard
- Total data points analyzed
- Number of stocks tracked
- Days of historical data
- Average market volatility

## Deployment

### 1. Deploy Lambda Function
```bash
cd lambda/market-insights
zip -r function.zip lambda_function.py
aws lambda create-function \
  --function-name mrktdly-market-insights \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/mrktdly-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 512 \
  --region us-east-1
```

### 2. Add API Gateway Route
```bash
aws apigatewayv2 create-route \
  --api-id YOUR_API_ID \
  --route-key "GET /market-insights" \
  --target "integrations/YOUR_INTEGRATION_ID"
```

### 3. Upload Website
```bash
aws s3 cp website/market-insights.html s3://marketdly.com/market-insights.html \
  --content-type text/html \
  --cache-control "max-age=300"
```

## Tech Stack
- **Frontend**: Plotly.js for interactive charts
- **Backend**: AWS Lambda + DynamoDB
- **Data**: 1+ year of historical market data
- **Styling**: Custom CSS with gradient backgrounds

## URL
https://marketdly.com/market-insights.html
