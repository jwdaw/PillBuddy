# PillBuddy Infrastructure Deployment Guide

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
cd infrastructure
./deploy.sh
```

This script will:

1. Check for AWS CLI and CDK installation
2. Create Python virtual environment
3. Install dependencies
4. Bootstrap CDK (if needed)
5. Deploy the infrastructure

### Option 2: Manual CDK Deployment

```bash
cd infrastructure

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install CDK CLI (if not already installed)
npm install -g aws-cdk

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy
cdk deploy
```

### Option 3: CloudFormation Direct Deployment

```bash
cd infrastructure

aws cloudformation create-stack \
  --stack-name PillBuddyStack \
  --template-body file://cloudformation-template.yaml \
  --region us-east-1
```

## What Gets Created

### DynamoDB Tables

1. **PillBuddy_Devices**
   - Partition Key: device_id (String)
   - Capacity: 5 RCU / 5 WCU
   - Purpose: Device status and slot states

2. **PillBuddy_Prescriptions**
   - Partition Key: device_id (String)
   - Sort Key: slot (Number)
   - Capacity: 5 RCU / 5 WCU
   - Purpose: Prescription data per slot

3. **PillBuddy_Events**
   - Partition Key: device_id (String)
   - Sort Key: timestamp (Number)
   - Capacity: 5 RCU / 10 WCU
   - TTL: Enabled on 'ttl' attribute
   - Purpose: Time-series event logging

## Verification

After deployment, verify the tables exist:

```bash
aws dynamodb list-tables --region us-east-1
```

Expected output should include:

- PillBuddy_Devices
- PillBuddy_Prescriptions
- PillBuddy_Events

Check table details:

```bash
aws dynamodb describe-table --table-name PillBuddy_Devices --region us-east-1
aws dynamodb describe-table --table-name PillBuddy_Prescriptions --region us-east-1
aws dynamodb describe-table --table-name PillBuddy_Events --region us-east-1
```

## Next Steps

1. **Configure AWS IoT Core** (Task 2)
   - Create IoT Thing Type
   - Set up IoT Policy
   - Create IoT Rule for event processing

2. **Implement Lambda Functions** (Tasks 3-6)
   - Use these environment variables:
     - `DEVICES_TABLE=PillBuddy_Devices`
     - `PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions`
     - `EVENTS_TABLE=PillBuddy_Events`

3. **Set up IAM Permissions**
   - Grant Lambda functions DynamoDB access
   - See README.md for required permissions

## Cleanup

To delete all resources:

### Using CDK

```bash
cd infrastructure
cdk destroy
```

### Using CloudFormation

```bash
aws cloudformation delete-stack --stack-name PillBuddyStack --region us-east-1
```

## Troubleshooting

### CDK Bootstrap Error

If you get "CDK bootstrap required" error:

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Permission Denied

Ensure your AWS credentials have permissions to:

- Create DynamoDB tables
- Create CloudFormation stacks
- Create IAM roles (for CDK)

### Table Already Exists

If tables already exist, either:

1. Delete them manually: `aws dynamodb delete-table --table-name TABLE_NAME`
2. Use a different stack name: `cdk deploy --stack-name PillBuddyStack2`

## Cost Monitoring

Monitor costs in AWS Console:

1. Go to AWS Cost Explorer
2. Filter by Service: DynamoDB
3. Expected cost: ~$2.28/month for hackathon usage

## Support

For issues or questions:

- Check TABLE_SCHEMAS.md for data model reference
- Review README.md for detailed documentation
- Verify AWS credentials: `aws sts get-caller-identity`
