# Lambda Functions Configuration Guide

This document provides a comprehensive reference for all Lambda function environment variables and IAM permissions required for the PillBuddy backend system.

## Overview

The PillBuddy system uses four Lambda functions:

1. **Alexa Skill Handler** - Processes voice commands
2. **IoT Event Processor** - Handles ESP32 device events
3. **Timeout Checker** - Monitors bottle return timeouts
4. **API Handler** - Provides REST API (optional)

## Quick Reference Table

| Lambda Function             | Memory | Timeout | Trigger                  |
| --------------------------- | ------ | ------- | ------------------------ |
| PillBuddy_AlexaHandler      | 256 MB | 10s     | Alexa Skills Kit         |
| PillBuddy_IoTEventProcessor | 256 MB | 30s     | IoT Rule                 |
| PillBuddy_TimeoutChecker    | 128 MB | 10s     | EventBridge (5 min rate) |
| PillBuddy_APIHandler        | 256 MB | 10s     | API Gateway              |

## 1. Alexa Skill Handler

### Environment Variables

| Variable              | Required | Description                           | Example Value                                |
| --------------------- | -------- | ------------------------------------- | -------------------------------------------- |
| `DEVICES_TABLE`       | Yes      | DynamoDB table name for devices       | `PillBuddy_Devices`                          |
| `PRESCRIPTIONS_TABLE` | Yes      | DynamoDB table name for prescriptions | `PillBuddy_Prescriptions`                    |
| `IOT_ENDPOINT`        | Yes      | AWS IoT Core endpoint URL             | `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com` |
| `AWS_REGION`          | Yes      | AWS region                            | `us-east-1`                                  |

### Getting IoT Endpoint

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text
```

### IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Devices",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions"
      ]
    },
    {
      "Sid": "IoTPublish",
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/pillbuddy/cmd/*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/lambda/PillBuddy_AlexaHandler:*"
    }
  ]
}
```

### Setting Environment Variables (AWS CLI)

```bash
aws lambda update-function-configuration \
  --function-name PillBuddy_AlexaHandler \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text),
    AWS_REGION=us-east-1
  }"
```

## 2. IoT Event Processor

### Environment Variables

| Variable              | Required | Description                           | Example Value                                |
| --------------------- | -------- | ------------------------------------- | -------------------------------------------- |
| `DEVICES_TABLE`       | Yes      | DynamoDB table name for devices       | `PillBuddy_Devices`                          |
| `PRESCRIPTIONS_TABLE` | Yes      | DynamoDB table name for prescriptions | `PillBuddy_Prescriptions`                    |
| `EVENTS_TABLE`        | Yes      | DynamoDB table name for events        | `PillBuddy_Events`                           |
| `IOT_ENDPOINT`        | Yes      | AWS IoT Core endpoint URL             | `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com` |
| `ALEXA_SKILL_ID`      | Yes      | Alexa skill ID for notifications      | `amzn1.ask.skill.xxxxx`                      |
| `AWS_REGION`          | Yes      | AWS region                            | `us-east-1`                                  |

### Getting Alexa Skill ID

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Open your PillBuddy skill
3. Click "Endpoint" in the left sidebar
4. Copy "Your Skill ID" at the top

### IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Devices",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Events"
      ]
    },
    {
      "Sid": "IoTPublish",
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/pillbuddy/cmd/*"
    },
    {
      "Sid": "EventBridgeScheduling",
      "Effect": "Allow",
      "Action": ["events:PutRule", "events:PutTargets"],
      "Resource": "arn:aws:events:REGION:ACCOUNT:rule/PillBuddy_*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/lambda/PillBuddy_IoTEventProcessor:*"
    }
  ]
}
```

### Setting Environment Variables (AWS CLI)

```bash
aws lambda update-function-configuration \
  --function-name PillBuddy_IoTEventProcessor \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    EVENTS_TABLE=PillBuddy_Events,
    IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text),
    ALEXA_SKILL_ID=YOUR_SKILL_ID,
    AWS_REGION=us-east-1
  }"
```

## 3. Timeout Checker

### Environment Variables

| Variable              | Required | Description                      | Example Value             |
| --------------------- | -------- | -------------------------------- | ------------------------- |
| `PRESCRIPTIONS_TABLE` | Yes      | DynamoDB table for prescriptions | `PillBuddy_Prescriptions` |
| `ALEXA_SKILL_ID`      | Yes      | Alexa skill ID for notifications | `amzn1.ask.skill.xxxxx`   |
| `AWS_REGION`          | No       | AWS region (auto-detected)       | `us-east-1`               |

### IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBScan",
      "Effect": "Allow",
      "Action": ["dynamodb:Scan", "dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/lambda/PillBuddy_TimeoutChecker:*"
    }
  ]
}
```

**Note**: Alexa notification permissions are handled through the Alexa skill configuration, not IAM.

### Setting Environment Variables (AWS CLI)

```bash
aws lambda update-function-configuration \
  --function-name PillBuddy_TimeoutChecker \
  --environment Variables="{
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    ALEXA_SKILL_ID=YOUR_SKILL_ID,
    AWS_REGION=us-east-1
  }"
```

## 4. API Handler (Optional)

### Environment Variables

| Variable              | Required | Description                      | Example Value             |
| --------------------- | -------- | -------------------------------- | ------------------------- |
| `DEVICES_TABLE`       | Yes      | DynamoDB table for devices       | `PillBuddy_Devices`       |
| `PRESCRIPTIONS_TABLE` | Yes      | DynamoDB table for prescriptions | `PillBuddy_Prescriptions` |
| `EVENTS_TABLE`        | Yes      | DynamoDB table for events        | `PillBuddy_Events`        |

### IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBRead",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:Query"],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Devices",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Events"
      ]
    },
    {
      "Sid": "DynamoDBWrite",
      "Effect": "Allow",
      "Action": "dynamodb:UpdateItem",
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/lambda/PillBuddy_APIHandler:*"
    }
  ]
}
```

### Setting Environment Variables (AWS CLI)

```bash
aws lambda update-function-configuration \
  --function-name PillBuddy_APIHandler \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    EVENTS_TABLE=PillBuddy_Events
  }"
```

## Deployment Automation

### Using AWS CDK

All environment variables and IAM permissions are automatically configured when deploying with CDK. See `infrastructure/pillbuddy_stack.py` for the complete implementation.

```bash
cd infrastructure
cdk deploy
```

### Using CloudFormation

The pre-generated CloudFormation template includes all configurations:

```bash
aws cloudformation create-stack \
  --stack-name PillBuddyStack \
  --template-body file://infrastructure/cloudformation-template.yaml \
  --capabilities CAPABILITY_IAM
```

### Manual Configuration Script

For manual deployment, use this script to configure all Lambda functions:

```bash
#!/bin/bash

# Get IoT endpoint
IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)

# Prompt for Alexa Skill ID
read -p "Enter your Alexa Skill ID: " ALEXA_SKILL_ID

# Configure Alexa Handler
aws lambda update-function-configuration \
  --function-name PillBuddy_AlexaHandler \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    IOT_ENDPOINT=$IOT_ENDPOINT,
    AWS_REGION=us-east-1
  }"

# Configure IoT Event Processor
aws lambda update-function-configuration \
  --function-name PillBuddy_IoTEventProcessor \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    EVENTS_TABLE=PillBuddy_Events,
    IOT_ENDPOINT=$IOT_ENDPOINT,
    ALEXA_SKILL_ID=$ALEXA_SKILL_ID,
    AWS_REGION=us-east-1
  }"

# Configure Timeout Checker
aws lambda update-function-configuration \
  --function-name PillBuddy_TimeoutChecker \
  --environment Variables="{
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    ALEXA_SKILL_ID=$ALEXA_SKILL_ID,
    AWS_REGION=us-east-1
  }"

# Configure API Handler (optional)
aws lambda update-function-configuration \
  --function-name PillBuddy_APIHandler \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    EVENTS_TABLE=PillBuddy_Events
  }"

echo "All Lambda functions configured successfully!"
```

## Verification

### Check Environment Variables

```bash
# Alexa Handler
aws lambda get-function-configuration \
  --function-name PillBuddy_AlexaHandler \
  --query 'Environment.Variables'

# IoT Event Processor
aws lambda get-function-configuration \
  --function-name PillBuddy_IoTEventProcessor \
  --query 'Environment.Variables'

# Timeout Checker
aws lambda get-function-configuration \
  --function-name PillBuddy_TimeoutChecker \
  --query 'Environment.Variables'

# API Handler
aws lambda get-function-configuration \
  --function-name PillBuddy_APIHandler \
  --query 'Environment.Variables'
```

### Check IAM Roles

```bash
# Get execution role ARN
aws lambda get-function-configuration \
  --function-name PillBuddy_AlexaHandler \
  --query 'Role' \
  --output text

# List attached policies
aws iam list-attached-role-policies \
  --role-name ROLE_NAME

# Get inline policies
aws iam list-role-policies \
  --role-name ROLE_NAME
```

## Troubleshooting

### Missing Environment Variables

**Symptom**: Lambda function fails with "KeyError" or "Environment variable not set"

**Solution**:

1. Check environment variables are set: `aws lambda get-function-configuration --function-name FUNCTION_NAME`
2. Update missing variables using the commands above
3. Redeploy if using CDK/CloudFormation

### IAM Permission Errors

**Symptom**: Lambda logs show "AccessDeniedException" or "User is not authorized"

**Solution**:

1. Verify IAM role has correct policies attached
2. Check resource ARNs match your account and region
3. Ensure Lambda execution role has trust relationship with `lambda.amazonaws.com`

### IoT Endpoint Not Working

**Symptom**: Cannot publish to IoT Core, connection errors

**Solution**:

1. Verify endpoint URL: `aws iot describe-endpoint --endpoint-type iot:Data-ATS`
2. Ensure endpoint doesn't include `https://` prefix
3. Check IoT publish permissions in IAM policy

### Alexa Notifications Not Working

**Symptom**: No notifications received on Alexa devices

**Solution**:

1. Verify Alexa Skill ID is correct
2. Enable proactive events in Alexa Developer Console
3. Ensure user has granted notification permissions
4. Check CloudWatch Logs for notification errors

## Security Best Practices

### For Production

1. **Least Privilege**: Grant only minimum required permissions
2. **Resource-Specific ARNs**: Replace wildcards with specific resource ARNs
3. **Encryption**: Enable encryption for environment variables containing sensitive data
4. **Secrets Manager**: Store Alexa Skill ID and other secrets in AWS Secrets Manager
5. **VPC**: Deploy Lambda functions in VPC for network isolation
6. **CloudWatch Alarms**: Set up alarms for permission errors and failures

### Example: Using Secrets Manager

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In Lambda function
secrets = get_secret('pillbuddy/config')
ALEXA_SKILL_ID = secrets['alexa_skill_id']
IOT_ENDPOINT = secrets['iot_endpoint']
```

## Cost Optimization

### Environment Variables

- No additional cost for environment variables
- Consider using Parameter Store for shared configuration (minimal cost)

### IAM Policies

- No cost for IAM policies
- Optimize by using resource-specific ARNs to prevent unauthorized access

## References

- [AWS Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [AWS IAM Policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)
- [AWS IoT Core Endpoints](https://docs.aws.amazon.com/iot/latest/developerguide/iot-connect-devices.html)
- [Alexa Proactive Events](https://developer.amazon.com/docs/smapi/proactive-events-api.html)
