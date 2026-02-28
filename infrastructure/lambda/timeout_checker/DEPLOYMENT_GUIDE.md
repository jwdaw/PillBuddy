# Timeout Checker Lambda - Deployment Guide

This guide provides step-by-step instructions for deploying the PillBuddy Timeout Checker Lambda function.

## Prerequisites

- AWS CLI configured with appropriate credentials
- DynamoDB table `PillBuddy_Prescriptions` already created
- Alexa Skill ID (if using proactive notifications)
- IAM permissions to create Lambda functions, IAM roles, and EventBridge rules

## Step 1: Create IAM Role

Create an IAM role for the Lambda function with necessary permissions.

### Create Trust Policy

```bash
cat > trust-policy.json << EOF
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
EOF
```

### Create IAM Role

```bash
aws iam create-role \
  --role-name PillBuddyTimeoutCheckerRole \
  --assume-role-policy-document file://trust-policy.json \
  --description "IAM role for PillBuddy Timeout Checker Lambda"
```

### Attach Policies

```bash
# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name PillBuddyTimeoutCheckerRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create custom policy for DynamoDB access
cat > dynamodb-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/PillBuddy_Prescriptions"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name PillBuddyTimeoutCheckerDynamoDBPolicy \
  --policy-document file://dynamodb-policy.json

# Attach custom policy (replace ACCOUNT with your AWS account ID)
aws iam attach-role-policy \
  --role-name PillBuddyTimeoutCheckerRole \
  --policy-arn arn:aws:iam::ACCOUNT:policy/PillBuddyTimeoutCheckerDynamoDBPolicy
```

## Step 2: Package Lambda Function

```bash
cd infrastructure/lambda/timeout_checker

# Create deployment package
zip -r function.zip lambda_function.py

# Verify package contents
unzip -l function.zip
```

## Step 3: Create Lambda Function

```bash
# Set environment variables
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="123456789012"  # Replace with your account ID
export ALEXA_SKILL_ID="amzn1.ask.skill.xxxxx"  # Replace with your skill ID

# Create Lambda function
aws lambda create-function \
  --function-name PillBuddy_TimeoutChecker \
  --runtime python3.11 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/PillBuddyTimeoutCheckerRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 10 \
  --memory-size 128 \
  --region ${AWS_REGION} \
  --environment Variables="{
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    ALEXA_SKILL_ID=${ALEXA_SKILL_ID}
  }" \
  --description "Checks for pill bottles out of holder for >10 minutes and sends reminders"
```

## Step 4: Create EventBridge Scheduled Rule

```bash
# Create EventBridge rule to trigger every 5 minutes
aws events put-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED \
  --region ${AWS_REGION} \
  --description "Trigger PillBuddy Timeout Checker every 5 minutes"

# Add Lambda as target
aws events put-targets \
  --rule PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION} \
  --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:PillBuddy_TimeoutChecker"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name PillBuddy_TimeoutChecker \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --region ${AWS_REGION} \
  --source-arn arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/PillBuddy_TimeoutChecker_Schedule
```

## Step 5: Test Lambda Function

### Manual Test Invocation

```bash
# Invoke Lambda manually
aws lambda invoke \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --payload '{}' \
  response.json

# View response
cat response.json
```

### Expected Response

```json
{
  "statusCode": 200,
  "body": "{\"status\": \"success\", \"prescriptions_checked\": 0, \"notifications_sent\": 0, \"within_timeout\": 0}"
}
```

### Test with Sample Data

Create a test prescription with an old removal timestamp:

```bash
# Create test prescription (15 minutes ago)
aws dynamodb put-item \
  --table-name PillBuddy_Prescriptions \
  --region ${AWS_REGION} \
  --item '{
    "device_id": {"S": "test_device_001"},
    "slot": {"N": "1"},
    "prescription_name": {"S": "Test Aspirin"},
    "pill_count": {"N": "20"},
    "initial_count": {"N": "30"},
    "has_refills": {"BOOL": true},
    "removal_timestamp": {"N": "'$(echo $(date +%s) - 900 | bc)000'"},
    "created_at": {"N": "'$(date +%s)000'"},
    "updated_at": {"N": "'$(date +%s)000'"}
  }'

# Invoke Lambda again
aws lambda invoke \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --payload '{}' \
  response.json

# Check response - should show 1 notification sent
cat response.json
```

### Clean Up Test Data

```bash
aws dynamodb delete-item \
  --table-name PillBuddy_Prescriptions \
  --region ${AWS_REGION} \
  --key '{
    "device_id": {"S": "test_device_001"},
    "slot": {"N": "1"}
  }'
```

## Step 6: Monitor Lambda Function

### View CloudWatch Logs

```bash
# Get log group name
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/PillBuddy_TimeoutChecker \
  --region ${AWS_REGION}

# Get recent log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --order-by LastEventTime \
  --descending \
  --max-items 5

# Tail logs (requires log stream name from above)
aws logs tail /aws/lambda/PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --follow
```

### Check EventBridge Rule Status

```bash
# Verify rule is enabled
aws events describe-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}

# List targets
aws events list-targets-by-rule \
  --rule PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}
```

## Step 7: Update Lambda Function (if needed)

```bash
# Make changes to lambda_function.py

# Repackage
zip -r function.zip lambda_function.py

# Update function code
aws lambda update-function-code \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --zip-file fileb://function.zip

# Update environment variables (if needed)
aws lambda update-function-configuration \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --environment Variables="{
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    ALEXA_SKILL_ID=${ALEXA_SKILL_ID}
  }"
```

## Verification Checklist

- [ ] IAM role created with correct permissions
- [ ] Lambda function created successfully
- [ ] Environment variables configured correctly
- [ ] EventBridge rule created and enabled
- [ ] Lambda has permission for EventBridge invocation
- [ ] Manual test invocation succeeds
- [ ] CloudWatch Logs show function executions
- [ ] EventBridge triggers Lambda every 5 minutes

## Troubleshooting

### Lambda Creation Fails

**Error**: "The role defined for the function cannot be assumed by Lambda"

**Solution**: Wait 10-15 seconds after creating the IAM role before creating the Lambda function. IAM role propagation takes time.

### EventBridge Not Triggering

**Check**:

1. Rule is in ENABLED state
2. Target is correctly configured
3. Lambda has permission for events.amazonaws.com

```bash
# Check Lambda permissions
aws lambda get-policy \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION}
```

### DynamoDB Access Denied

**Error**: "User is not authorized to perform: dynamodb:Scan"

**Solution**: Verify IAM role has DynamoDB policy attached:

```bash
aws iam list-attached-role-policies \
  --role-name PillBuddyTimeoutCheckerRole
```

### No Prescriptions Found

**Expected**: If no prescriptions have `removal_timestamp` set, the function will return:

```json
{
  "prescriptions_checked": 0,
  "notifications_sent": 0,
  "within_timeout": 0
}
```

This is normal behavior when all bottles are in the holder.

## AWS Console Deployment (Alternative)

If you prefer using the AWS Console:

### Lambda Function

1. Go to AWS Lambda console
2. Click "Create function"
3. Choose "Author from scratch"
4. Function name: `PillBuddy_TimeoutChecker`
5. Runtime: Python 3.11
6. Architecture: x86_64
7. Execution role: Create new role or use existing
8. Click "Create function"
9. Upload `function.zip` in Code source section
10. Set environment variables in Configuration → Environment variables
11. Set timeout to 10 seconds in Configuration → General configuration
12. Set memory to 128 MB

### EventBridge Rule

1. Go to Amazon EventBridge console
2. Click "Rules" → "Create rule"
3. Name: `PillBuddy_TimeoutChecker_Schedule`
4. Rule type: Schedule
5. Schedule pattern: Rate-based schedule
6. Rate expression: `5 minutes`
7. Target: Lambda function
8. Function: `PillBuddy_TimeoutChecker`
9. Click "Create rule"

## Cost Estimation

### Lambda Costs

- Invocations: ~8,640 per month (every 5 minutes)
- Duration: ~1 second per invocation
- Memory: 128 MB
- **Estimated cost**: $0.00 (within free tier)

### DynamoDB Costs

- Scan operations: ~8,640 per month
- Read capacity: Minimal (few prescriptions)
- **Estimated cost**: $0.00 - $0.50 per month

### EventBridge Costs

- Rule invocations: ~8,640 per month
- **Estimated cost**: $0.00 (within free tier)

**Total estimated cost**: $0.00 - $0.50 per month for hackathon scale

## Next Steps

1. Deploy IoT Event Processor Lambda (sets removal_timestamp)
2. Deploy Alexa Handler Lambda (handles voice commands)
3. Configure Alexa Skill with proactive notifications
4. Test end-to-end workflow with ESP32 device

## References

- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Amazon EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [DynamoDB Scan Operation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html)
- [Alexa Proactive Events API](https://developer.amazon.com/docs/smapi/proactive-events-api.html)
