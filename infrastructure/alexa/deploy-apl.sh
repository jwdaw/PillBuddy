#!/bin/bash

# APL Visual Display Deployment Script
# This script deploys the APL-enabled Lambda function and skill configuration

set -e

SKILL_ID="amzn1.ask.skill.74757f0a-fe9f-4daa-b11b-31832cf97e17"
REGION="us-east-1"

echo "🚀 Deploying APL Visual Display Feature..."
echo ""

# Step 1: Deploy Lambda Function
echo "📦 Step 1: Deploying Lambda function..."
cd lambda/alexa_handler
zip -r alexa_handler.zip lambda_function.py apl_templates/
aws lambda update-function-code \
  --function-name PillBuddy_AlexaHandler \
  --zip-file fileb://alexa_handler.zip \
  --region $REGION
cd ../..
echo "✅ Lambda deployed successfully!"
echo ""

# Step 2: Instructions for Alexa Developer Console
echo "📋 Step 2: Enable APL Interface in Alexa Developer Console"
echo ""
echo "Please complete these manual steps:"
echo ""
echo "1. Go to: https://developer.amazon.com/alexa/console/ask"
echo "2. Click on your 'PillBuddy' skill"
echo "3. Click 'Build' tab"
echo "4. In left sidebar, click 'Interfaces'"
echo "5. Find 'Alexa Presentation Language'"
echo "6. Toggle the switch to ON"
echo "7. Click 'Save Interfaces'"
echo "8. Click 'Build Model' (top right)"
echo "9. Wait for build to complete (~30-60 seconds)"
echo ""
echo "Your Skill ID: $SKILL_ID"
echo ""
echo "✅ Deployment complete!"
echo ""
echo "🧪 To test:"
echo "   - In Alexa Developer Console Test tab, say: 'open pill buddy'"
echo "   - Then say: 'what's my status'"
echo "   - You should see the visual display on Echo Show devices!"
