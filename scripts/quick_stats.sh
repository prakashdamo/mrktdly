#!/bin/bash
# Quick stats - one line
aws cognito-idp list-users --user-pool-id us-east-1_N5yuAGHc3 --region us-east-1 --output json | jq -r '"👥 Users: \(.Users | length) | ✅ Confirmed: \([.Users[] | select(.UserStatus == "CONFIRMED")] | length) | 🆕 Today: \([.Users[] | select(.UserCreateDate | startswith("'$(date -u +%Y-%m-%d)'"))] | length)"'
