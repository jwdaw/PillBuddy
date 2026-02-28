# EventBridge Setup for PillBuddy Timeout Checker

This document provides instructions for setting up the Amazon EventBridge scheduled rule that triggers the Timeout Checker Lambda function every 5 minutes.

## Overview

The EventBridge scheduled rule is a critical component of the PillBuddy system that ensures bottles removed from the holder for more than 10 minutes trigger reminder notifications to users.

## Architecture

```
EventBridge Rule (rate: 5 minutes)
    ↓
PillBuddy_TimeoutChecker Lambda
    ↓
Scan PillBuddy_Prescriptions Table
    ↓
Send Alexa Notifications (if timeout exceeded)
```

## Prerequisites

- Lambda function `PillBuddy_TimeoutChecker` deployed
- Lambda function has appropriate IAM permissions
- AWS CLI configured or access to AWS Console

## Method 1: AWS CLI Setup

### Step 1: Create EventBridge Rule

```bash
# Set environment variables
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="123456789012"  # Replace with your account ID

# Create the scheduled rule
aws events put-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED \
  --region ${AWS_REGION} \
  --description "Trigger PillBuddy Timeout Checker every 5 minutes to check for bottles out >10 minutes"
```

**Expected Output**:

```json
{
  "RuleArn": "arn:aws:events:us-east-1:123456789012:rule/PillBuddy_TimeoutChecker_Schedule"
}
```

### Step 2: Add Lambda as Target

```bash
# Add Lambda function as target
aws events put-targets \
  --rule PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION} \
  --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:PillBuddy_TimeoutChecker"
```

**Expected Output**:

```json
{
  "FailedEntryCount": 0,
  "FailedEntries": []
}
```

### Step 3: Grant EventBridge Permission to Invoke Lambda

```bash
# Add permission for EventBridge to invoke Lambda
aws lambda add-permission \
  --function-name PillBuddy_TimeoutChecker \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --region ${AWS_REGION} \
  --source-arn arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/PillBuddy_TimeoutChecker_Schedule
```

**Expected Output**:

```json
{
  "Statement": "{\"Sid\":\"AllowEventBridgeInvoke\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"events.amazonaws.com\"},\"Action\":\"lambda:InvokeFunction\",\"Resource\":\"arn:aws:lambda:us-east-1:123456789012:function:PillBuddy_TimeoutChecker\",\"Condition\":{\"ArnLike\":{\"AWS:SourceArn\":\"arn:aws:events:us-east-1:123456789012:rule/PillBuddy_TimeoutChecker_Schedule\"}}}"
}
```

### Step 4: Verify Setup

```bash
# Verify rule exists and is enabled
aws events describe-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}

# Verify targets are configured
aws events list-targets-by-rule \
  --rule PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}

# Verify Lambda has permission
aws lambda get-policy \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION}
```

## Method 2: AWS Console Setup

### Step 1: Navigate to EventBridge

1. Open AWS Console
2. Navigate to **Amazon EventBridge**
3. Click **Rules** in the left sidebar
4. Click **Create rule**

### Step 2: Define Rule Details

1. **Name**: `PillBuddy_TimeoutChecker_Schedule`
2. **Description**: `Trigger PillBuddy Timeout Checker every 5 minutes to check for bottles out >10 minutes`
3. **Event bus**: `default`
4. **Rule type**: Select **Schedule**
5. Click **Next**

### Step 3: Configure Schedule Pattern

1. **Schedule pattern**: Select **A schedule that runs at a regular rate, such as every 10 minutes**
2. **Rate expression**:
   - Value: `5`
   - Unit: `Minutes`
3. Click **Next**

### Step 4: Select Target

1. **Target types**: Select **AWS service**
2. **Select a target**: Choose **Lambda function**
3. **Function**: Select `PillBuddy_TimeoutChecker` from dropdown
4. **Additional settings**: Leave defaults
   - Retry policy: Default (2 retries, 60 seconds)
   - Dead-letter queue: None (optional for production)
5. Click **Next**

### Step 5: Configure Tags (Optional)

1. Add tags if desired:
   - Key: `Project`, Value: `PillBuddy`
   - Key: `Component`, Value: `TimeoutChecker`
2. Click **Next**

### Step 6: Review and Create

1. Review all settings
2. Click **Create rule**
3. Verify rule appears in the rules list with status **Enabled**

## Method 3: AWS CDK Setup (Infrastructure as Code)

If using AWS CDK for infrastructure deployment:

```python
from aws_cdk import (
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    Stack
)

class PillBuddyStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Assume timeout_checker Lambda is already defined
        timeout_checker = lambda_.Function(
            self, "TimeoutChecker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/timeout_checker"),
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={
                "PRESCRIPTIONS_TABLE": prescriptions_table.table_name,
                "ALEXA_SKILL_ID": alexa_skill_id
            }
        )

        # Create EventBridge rule
        rule = events.Rule(
            self, "TimeoutCheckerSchedule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            description="Trigger PillBuddy Timeout Checker every 5 minutes"
        )

        # Add Lambda as target
        rule.add_target(targets.LambdaFunction(timeout_checker))
```

Deploy with:

```bash
cdk deploy
```

## Method 4: CloudFormation Template

```yaml
Resources:
  TimeoutCheckerScheduleRule:
    Type: AWS::Events::Rule
    Properties:
      Name: PillBuddy_TimeoutChecker_Schedule
      Description: Trigger PillBuddy Timeout Checker every 5 minutes
      ScheduleExpression: rate(5 minutes)
      State: ENABLED
      Targets:
        - Arn: !GetAtt TimeoutCheckerFunction.Arn
          Id: TimeoutCheckerTarget

  TimeoutCheckerSchedulePermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref TimeoutCheckerFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt TimeoutCheckerScheduleRule.Arn
```

## Verification

### Test Manual Invocation

Before relying on the schedule, test manual invocation:

```bash
# Manually invoke Lambda
aws lambda invoke \
  --function-name PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --payload '{}' \
  response.json

# Check response
cat response.json
```

**Expected Response**:

```json
{
  "statusCode": 200,
  "body": "{\"status\": \"success\", \"prescriptions_checked\": 0, \"notifications_sent\": 0, \"within_timeout\": 0}"
}
```

### Monitor Scheduled Invocations

Wait 5-10 minutes after creating the rule, then check CloudWatch Logs:

```bash
# Tail CloudWatch Logs
aws logs tail /aws/lambda/PillBuddy_TimeoutChecker \
  --region ${AWS_REGION} \
  --follow
```

**Expected Log Output** (every 5 minutes):

```
START RequestId: abc123...
Starting timeout check...
Found 0 prescriptions with bottles removed
Timeout check complete: 0 notifications sent, 0 within timeout
END RequestId: abc123...
REPORT RequestId: abc123... Duration: 1234.56 ms Billed Duration: 1235 ms Memory Size: 128 MB Max Memory Used: 65 MB
```

### Check EventBridge Metrics

1. Go to **EventBridge Console** → **Rules**
2. Click on `PillBuddy_TimeoutChecker_Schedule`
3. Click **Monitoring** tab
4. Verify **Invocations** metric shows activity every 5 minutes

### Check Lambda Metrics

1. Go to **Lambda Console** → **Functions**
2. Click on `PillBuddy_TimeoutChecker`
3. Click **Monitor** tab
4. Verify **Invocations** metric shows activity every 5 minutes

## Troubleshooting

### Issue: Rule Not Triggering Lambda

**Symptoms**: No CloudWatch Logs, no Lambda invocations

**Checks**:

1. Verify rule is **ENABLED**:

   ```bash
   aws events describe-rule --name PillBuddy_TimeoutChecker_Schedule --region ${AWS_REGION}
   ```

   Look for `"State": "ENABLED"`

2. Verify target is configured:

   ```bash
   aws events list-targets-by-rule --rule PillBuddy_TimeoutChecker_Schedule --region ${AWS_REGION}
   ```

   Should show Lambda ARN

3. Verify Lambda permission:
   ```bash
   aws lambda get-policy --function-name PillBuddy_TimeoutChecker --region ${AWS_REGION}
   ```
   Should include `events.amazonaws.com` principal

**Solution**: Re-run Step 3 to add Lambda permission

### Issue: Lambda Invocation Fails

**Symptoms**: EventBridge shows invocations, but Lambda shows errors

**Checks**:

1. Check CloudWatch Logs for error messages
2. Verify Lambda has correct IAM permissions for DynamoDB
3. Verify environment variables are set correctly

**Solution**: Review Lambda configuration and IAM role

### Issue: Permission Already Exists Error

**Error**: "ResourceConflictException: The statement id (AllowEventBridgeInvoke) provided already exists"

**Solution**: This is expected if you've already added the permission. You can:

- Ignore the error (permission already exists)
- Remove and re-add:

  ```bash
  aws lambda remove-permission \
    --function-name PillBuddy_TimeoutChecker \
    --statement-id AllowEventBridgeInvoke \
    --region ${AWS_REGION}

  # Then re-run add-permission command
  ```

### Issue: Too Many Invocations

**Symptoms**: Lambda invoked more frequently than expected

**Check**: Verify schedule expression:

```bash
aws events describe-rule --name PillBuddy_TimeoutChecker_Schedule --region ${AWS_REGION}
```

**Solution**: Update schedule expression:

```bash
aws events put-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --schedule-expression "rate(5 minutes)" \
  --region ${AWS_REGION}
```

## Schedule Expression Options

### Rate-Based Schedules

Current configuration uses rate-based schedule:

```
rate(5 minutes)
```

Other options:

- `rate(1 minute)` - Every minute (more frequent checks)
- `rate(10 minutes)` - Every 10 minutes (less frequent)
- `rate(1 hour)` - Every hour (minimal checks)

### Cron-Based Schedules

For more control, use cron expressions:

```
cron(0/5 * * * ? *)  # Every 5 minutes
cron(0 * * * ? *)    # Every hour at minute 0
cron(0 9-17 * * ? *) # Every hour from 9 AM to 5 PM
```

**Note**: EventBridge cron uses UTC timezone

## Cost Considerations

### EventBridge Costs

- **Invocations**: ~8,640 per month (every 5 minutes)
- **Pricing**: First 1 million invocations free, then $1.00 per million
- **Estimated cost**: $0.00 (within free tier)

### Lambda Costs

- **Invocations**: ~8,640 per month
- **Duration**: ~1 second per invocation
- **Memory**: 128 MB
- **Pricing**: First 1 million requests free, 400,000 GB-seconds free
- **Estimated cost**: $0.00 (within free tier)

**Total estimated cost**: $0.00 for hackathon scale

## Modifying the Schedule

### Change Frequency

To change from 5 minutes to 10 minutes:

```bash
aws events put-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --schedule-expression "rate(10 minutes)" \
  --region ${AWS_REGION}
```

### Disable Rule Temporarily

```bash
aws events disable-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}
```

### Re-enable Rule

```bash
aws events enable-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}
```

### Delete Rule

```bash
# Remove targets first
aws events remove-targets \
  --rule PillBuddy_TimeoutChecker_Schedule \
  --ids "1" \
  --region ${AWS_REGION}

# Delete rule
aws events delete-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --region ${AWS_REGION}
```

## Monitoring and Alerts

### CloudWatch Alarms

Create alarms for monitoring:

```bash
# Alarm for no invocations (rule not working)
aws cloudwatch put-metric-alarm \
  --alarm-name PillBuddy_TimeoutChecker_NoInvocations \
  --alarm-description "Alert if Timeout Checker not invoked in 10 minutes" \
  --metric-name Invocations \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 600 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=FunctionName,Value=PillBuddy_TimeoutChecker

# Alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name PillBuddy_TimeoutChecker_Errors \
  --alarm-description "Alert if Timeout Checker has errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=FunctionName,Value=PillBuddy_TimeoutChecker
```

## Best Practices

1. **Test Before Enabling**: Test Lambda manually before enabling scheduled rule
2. **Monitor Initially**: Watch CloudWatch Logs for first few invocations
3. **Set Up Alarms**: Create CloudWatch alarms for errors and missing invocations
4. **Document Changes**: Keep track of schedule modifications
5. **Use Tags**: Tag EventBridge rules for organization
6. **Review Costs**: Monitor AWS billing for unexpected charges

## Related Documentation

- [Lambda Deployment Guide](lambda/timeout_checker/DEPLOYMENT_GUIDE.md)
- [Lambda README](lambda/timeout_checker/README.md)
- [AWS EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [EventBridge Schedule Expressions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html)

## Summary

The EventBridge scheduled rule is now configured to trigger the Timeout Checker Lambda every 5 minutes. This ensures timely detection and notification of bottles that have been out of the holder for more than 10 minutes, completing the timeout monitoring workflow for the PillBuddy system.
