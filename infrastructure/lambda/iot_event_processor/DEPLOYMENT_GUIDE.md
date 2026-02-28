# IoT Event Processor Lambda Deployment Guide

This guide walks through deploying the PillBuddy IoT Event Processor Lambda function.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.11 installed locally
- DynamoDB tables created (Devices, Prescriptions, Events)
- AWS IoT Core endpoint configured
- IAM role with required permissions

## Step 1: Create IAM Role

Create an IAM role for the Lambda function with the following trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Attach the following managed policies:

- `AWSLambdaBasicExecutionRole` (for CloudWatch Logs)

Create a custom policy for DynamoDB and IoT access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Devices",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Events"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/pillbuddy/cmd/*"
    },
    {
      "Effect": "Allow",
      "Action": ["events:PutRule", "events:PutTargets"],
      "Resource": "*"
    }
  ]
}
```

Save the role ARN for later use.

## Step 2: Get IoT Core Endpoint

Get your AWS IoT Core endpoint:

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

Save the endpoint URL (e.g., `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com`).

## Step 3: Package Lambda Function

```bash
cd infrastructure/lambda/iot_event_processor

# Create deployment package
zip -r function.zip lambda_function.py

# Verify contents
unzip -l function.zip
```

## Step 4: Create Lambda Function

Replace the placeholders with your actual values:

```bash
aws lambda create-function \
  --function-name PillBuddy_IoTEventProcessor \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/PillBuddyIoTProcessorRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    EVENTS_TABLE=PillBuddy_Events,
    IOT_ENDPOINT=YOUR_IOT_ENDPOINT,
    ALEXA_SKILL_ID=YOUR_SKILL_ID,
    AWS_REGION=us-east-1
  }" \
  --description "Processes IoT events from PillBuddy ESP32 devices"
```

Save the Lambda ARN from the output.

## Step 5: Create IoT Rule

Create an IoT Rule to trigger the Lambda function:

```bash
# Create rule
aws iot create-topic-rule \
  --rule-name PillBuddyEventProcessor \
  --topic-rule-payload '{
    "sql": "SELECT * FROM '\''pillbuddy/events/+'\''",
    "description": "Forward PillBuddy device events to Lambda",
    "actions": [
      {
        "lambda": {
          "functionArn": "arn:aws:lambda:REGION:ACCOUNT:function:PillBuddy_IoTEventProcessor"
        }
      }
    ],
    "ruleDisabled": false
  }'
```

## Step 6: Grant IoT Permission to Invoke Lambda

```bash
aws lambda add-permission \
  --function-name PillBuddy_IoTEventProcessor \
  --statement-id IoTInvoke \
  --action lambda:InvokeFunction \
  --principal iot.amazonaws.com \
  --source-arn arn:aws:iot:REGION:ACCOUNT:rule/PillBuddyEventProcessor
```

## Step 7: Test the Lambda Function

### Test with AWS Console

1. Go to AWS Lambda Console
2. Select `PillBuddy_IoTEventProcessor`
3. Click "Test" tab
4. Create a new test event using the JSON from `test_events.json`
5. Click "Test" to invoke

### Test with AWS CLI

```bash
# Test bottle removal event
aws lambda invoke \
  --function-name PillBuddy_IoTEventProcessor \
  --payload file://test_events.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# View response
cat response.json
```

### Test with IoT Core

Publish a test message to IoT Core:

```bash
aws iot-data publish \
  --topic pillbuddy/events/esp32_001 \
  --payload '{
    "device_id": "esp32_001",
    "event_type": "slot_state_changed",
    "slot": 2,
    "state": "not_in_holder",
    "in_holder": false,
    "sensor_level": 0,
    "ts_ms": 1700000000000,
    "sequence": 120
  }' \
  --cli-binary-format raw-in-base64-out
```

Check CloudWatch Logs to verify processing.

## Step 8: Verify DynamoDB Updates

After testing, verify the data in DynamoDB:

```bash
# Check Events table
aws dynamodb query \
  --table-name PillBuddy_Events \
  --key-condition-expression "device_id = :did" \
  --expression-attribute-values '{":did":{"S":"esp32_001"}}'

# Check Devices table
aws dynamodb get-item \
  --table-name PillBuddy_Devices \
  --key '{"device_id":{"S":"esp32_001"}}'

# Check Prescriptions table
aws dynamodb query \
  --table-name PillBuddy_Prescriptions \
  --key-condition-expression "device_id = :did" \
  --expression-attribute-values '{":did":{"S":"esp32_001"}}'
```

## Step 9: Monitor CloudWatch Logs

View Lambda execution logs:

```bash
# Get log group
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/PillBuddy_IoTEventProcessor

# Tail logs (requires awslogs tool)
awslogs get /aws/lambda/PillBuddy_IoTEventProcessor --watch
```

Or use the AWS Console:

1. Go to CloudWatch → Log groups
2. Find `/aws/lambda/PillBuddy_IoTEventProcessor`
3. View recent log streams

## Step 10: Update Lambda Function (for changes)

When you make code changes:

```bash
# Re-package
cd infrastructure/lambda/iot_event_processor
zip -r function.zip lambda_function.py

# Update function code
aws lambda update-function-code \
  --function-name PillBuddy_IoTEventProcessor \
  --zip-file fileb://function.zip

# Update environment variables (if needed)
aws lambda update-function-configuration \
  --function-name PillBuddy_IoTEventProcessor \
  --environment Variables="{
    DEVICES_TABLE=PillBuddy_Devices,
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    EVENTS_TABLE=PillBuddy_Events,
    IOT_ENDPOINT=YOUR_IOT_ENDPOINT,
    ALEXA_SKILL_ID=YOUR_SKILL_ID,
    AWS_REGION=us-east-1
  }"
```

## Troubleshooting

### Lambda not being triggered

**Check**:

1. IoT Rule is active: `aws iot get-topic-rule --rule-name PillBuddyEventProcessor`
2. Lambda has permission from IoT: Check resource-based policy
3. Topic pattern matches: Ensure device publishes to `pillbuddy/events/{device_id}`

### DynamoDB access errors

**Check**:

1. IAM role has correct permissions
2. Table names in environment variables match actual tables
3. Tables exist in the same region as Lambda

### IoT publish errors

**Check**:

1. IoT endpoint is correct
2. Lambda has `iot:Publish` permission
3. Topic format is correct: `pillbuddy/cmd/{device_id}`

### Timeout errors

**Check**:

1. DynamoDB tables have sufficient capacity
2. Network connectivity to DynamoDB and IoT
3. Increase Lambda timeout if needed (max 30s configured)

## Monitoring and Alerts

### CloudWatch Metrics to Monitor

- `Invocations`: Number of times Lambda is invoked
- `Errors`: Number of failed invocations
- `Duration`: Execution time
- `Throttles`: Number of throttled invocations

### Create CloudWatch Alarms

```bash
# Alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name PillBuddy-IoTProcessor-Errors \
  --alarm-description "Alert on IoT Processor errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=PillBuddy_IoTEventProcessor
```

## Cost Optimization

For hackathon/development:

- Use provisioned capacity (5-10 RCU/WCU) for DynamoDB
- Lambda free tier: 1M requests/month, 400,000 GB-seconds/month

For production:

- Consider DynamoDB on-demand pricing
- Use Lambda reserved concurrency if needed
- Enable TTL on Events table (already configured)

## Security Best Practices

1. **Least Privilege**: IAM role has only required permissions
2. **Encryption**: Enable encryption at rest for DynamoDB tables
3. **VPC**: Consider running Lambda in VPC for production
4. **Secrets**: Store sensitive values in AWS Secrets Manager
5. **Logging**: Enable CloudTrail for API audit logs

## Next Steps

1. Deploy Timeout Checker Lambda (Task 6)
2. Test end-to-end flow with ESP32 device
3. Configure Alexa proactive notifications
4. Set up monitoring dashboards
5. Test error scenarios

## Related Documentation

- [README.md](README.md) - Function overview and API
- [test_events.json](test_events.json) - Test event samples
- [../alexa_handler/README.md](../alexa_handler/README.md) - Alexa Handler Lambda
- [../../IOT_CORE_SETUP.md](../../IOT_CORE_SETUP.md) - IoT Core configuration
- [../../TABLE_SCHEMAS.md](../../TABLE_SCHEMAS.md) - DynamoDB schemas
