#!/bin/bash
# PillBuddy Infrastructure Deployment Script

set -e

echo "🚀 PillBuddy Infrastructure Deployment"
echo "======================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "⚠️  AWS CDK is not installed. Installing..."
    npm install -g aws-cdk
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install -q -r requirements.txt

# Bootstrap CDK (if needed)
echo "🏗️  Checking CDK bootstrap status..."
cdk bootstrap 2>/dev/null || echo "CDK already bootstrapped"

# Synthesize template
echo "🔍 Synthesizing CloudFormation template..."
cdk synth

# Deploy
echo ""
echo "🚀 Deploying infrastructure..."
cdk deploy --require-approval never

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Table Names:"
echo "  - PillBuddy_Devices"
echo "  - PillBuddy_Prescriptions"
echo "  - PillBuddy_Events"
echo ""
echo "💡 Use these table names in your Lambda environment variables:"
echo "  DEVICES_TABLE=PillBuddy_Devices"
echo "  PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions"
echo "  EVENTS_TABLE=PillBuddy_Events"
