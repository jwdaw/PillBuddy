# PillBuddy Backend Infrastructure

This directory contains Infrastructure as Code (IaC) for the PillBuddy backend AWS resources.

## Overview

The infrastructure creates three DynamoDB tables:

1. **PillBuddy_Devices** - Stores device connection status and slot states
   - Partition Key: `device_id` (String)
   - Provisioned Capacity: 5 RCU / 5 WCU

2. **PillBuddy_Prescriptions** - Stores prescription data for each device slot
   - Partition Key: `device_id` (String)
   - Sort Key: `slot` (Number)
   - Provisioned Capacity: 5 RCU / 5 WCU

3. **PillBuddy_Events** - Stores time-series events from ESP32 devices
   - Partition Key: `device_id` (String)
   - Sort Key: `timestamp` (Number)
   - TTL enabled on `ttl` attribute (auto-delete after 30 days)
   - Provisioned Capacity: 5 RCU / 10 WCU

## Deployment Options

### Option 1: AWS CDK (Recommended)

#### Prerequisites

- Python 3.11 or later
- AWS CLI configured with credentials
- Node.js 14.x or later (for CDK CLI)

#### Setup

1. Install AWS CDK CLI:

```bash
npm install -g aws-cdk
```

2. Create and activate a Python virtual environment:

```bash
cd infrastructure
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

#### Deploy

1. Bootstrap CDK (first time only):

```bash
cdk bootstrap
```

2. Synthesize CloudFormation template (optional - to preview):

```bash
cdk synth
```

3. Deploy the stack:

```bash
cdk deploy
```

4. To destroy the stack (cleanup):

```bash
cdk destroy
```

### Option 2: CloudFormation Template

Use the pre-generated CloudFormation template for direct deployment:

```bash
aws cloudformation create-stack \
  --stack-name PillBuddyStack \
  --template-body file://cloudformation-template.yaml \
  --region us-east-1
```

To delete the stack:

```bash
aws cloudformation delete-stack \
  --stack-name PillBuddyStack \
  --region us-east-1
```

## Table Schemas

### Devices Table

```python
{
    "device_id": "string",      # Partition key
    "online": "boolean",        # Device connection status
    "last_seen": "number",      # Unix timestamp (milliseconds)
    "created_at": "number",     # Unix timestamp (milliseconds)
    "slots": {
        "1": {
            "in_holder": "boolean",
            "last_state_change": "number"
        },
        "2": {
            "in_holder": "boolean",
            "last_state_change": "number"
        },
        "3": {
            "in_holder": "boolean",
            "last_state_change": "number"
        }
    }
}
```

### Prescriptions Table

```python
{
    "device_id": "string",        # Partition key
    "slot": "number",             # Sort key (1, 2, or 3)
    "prescription_name": "string",
    "pill_count": "number",       # Current count
    "initial_count": "number",    # Starting count
    "has_refills": "boolean",
    "created_at": "number",       # Unix timestamp
    "updated_at": "number",       # Unix timestamp
    "removal_timestamp": "number" # Unix timestamp when bottle removed (null if in holder)
}
```

### Events Table

```python
{
    "device_id": "string",     # Partition key
    "timestamp": "number",     # Sort key (Unix timestamp milliseconds)
    "event_type": "string",    # "slot_state_changed"
    "slot": "number",          # 1, 2, or 3
    "state": "string",         # "in_holder" or "not_in_holder"
    "in_holder": "boolean",
    "sensor_level": "number",  # 0 (LOW) or 1 (HIGH)
    "sequence": "number",      # ESP32 sequence number
    "ttl": "number"            # DynamoDB TTL (auto-delete after 30 days)
}
```

## Configuration

### Environment Variables for Lambda Functions

After deployment, use these table names in your Lambda functions:

- `DEVICES_TABLE`: `PillBuddy_Devices`
- `PRESCRIPTIONS_TABLE`: `PillBuddy_Prescriptions`
- `EVENTS_TABLE`: `PillBuddy_Events`

### IAM Permissions

Lambda functions will need the following DynamoDB permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Devices",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Events"
      ]
    }
  ]
}
```

## Cost Estimation

For hackathon usage with provisioned capacity:

- Devices Table: 5 RCU + 5 WCU ≈ $0.65/month
- Prescriptions Table: 5 RCU + 5 WCU ≈ $0.65/month
- Events Table: 5 RCU + 10 WCU ≈ $0.98/month

**Total: ~$2.28/month** (plus minimal storage costs)

## Notes

- Tables are configured with `RemovalPolicy.DESTROY` for easy cleanup during hackathon
- For production, change to `RemovalPolicy.RETAIN` to prevent accidental data loss
- TTL on Events table automatically deletes events older than 30 days
- Provisioned capacity is set for hackathon scale (low traffic)
- Consider switching to on-demand billing for production if traffic is unpredictable
