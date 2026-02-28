# PillBuddy Timeout Checker Lambda

This Lambda function periodically checks for pill bottles that have been removed from the holder for more than 10 minutes and sends Alexa reminder notifications to users.

## Overview

The Timeout Checker runs on a scheduled basis (every 5 minutes via EventBridge) to monitor prescription bottles that are out of the holder. It implements Algorithm 3 from the design document to ensure users are reminded to return bottles to their PillBuddy device.

## Architecture

```
EventBridge (every 5 min) → Lambda → DynamoDB Scan
                                   ↓
                              Alexa Notifications
```

## Environment Variables

| Variable              | Description                      | Example                   |
| --------------------- | -------------------------------- | ------------------------- |
| `PRESCRIPTIONS_TABLE` | DynamoDB table for prescriptions | `PillBuddy_Prescriptions` |
| `ALEXA_SKILL_ID`      | Alexa skill ID for notifications | `amzn1.ask.skill.xxxxx`   |

## IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:Scan", "dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions"
    },
    {
      "Effect": "Allow",
      "Action": "alexa:SendNotification",
      "Resource": "*"
    }
  ]
}
```

## Lambda Configuration

- **Runtime**: Python 3.11
- **Memory**: 128 MB
- **Timeout**: 10 seconds
- **Handler**: `lambda_function.lambda_handler`
- **Trigger**: EventBridge scheduled rule (rate: 5 minutes)

## Processing Logic

### Algorithm 3: Check Bottle Return Timeout

1. **Scan Prescriptions**: Query all prescriptions with non-null `removal_timestamp`
2. **Calculate Elapsed Time**: For each prescription, compute `current_time - removal_timestamp`
3. **Check Threshold**: If elapsed time >= 10 minutes (600,000 ms), send notification
4. **Send Notification**: Create Alexa reminder message with prescription name and slot number

### Correctness Properties

- **Property 4**: Removal Timestamp Invariant - only processes prescriptions with removal_timestamp set
- **Timeout Threshold**: 10 minutes (600,000 milliseconds)

## EventBridge Scheduled Rule

### Rule Configuration

**Rule Name**: `PillBuddy_TimeoutChecker_Schedule`

**Schedule Expression**: `rate(5 minutes)`

**Target**: Lambda function `PillBuddy_TimeoutChecker`

### Creating the Rule (AWS CLI)

```bash
# Create EventBridge rule
aws events put-rule \
  --name PillBuddy_TimeoutChecker_Schedule \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED \
  --description "Trigger PillBuddy Timeout Checker every 5 minutes"

# Add Lambda as target
aws events put-targets \
  --rule PillBuddy_TimeoutChecker_Schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:PillBuddy_TimeoutChecker"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name PillBuddy_TimeoutChecker \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:REGION:ACCOUNT:rule/PillBuddy_TimeoutChecker_Schedule
```

### Creating the Rule (AWS Console)

1. Go to Amazon EventBridge console
2. Click "Rules" → "Create rule"
3. Name: `PillBuddy_TimeoutChecker_Schedule`
4. Rule type: Schedule
5. Schedule pattern: Rate-based schedule
6. Rate expression: `5 minutes`
7. Target: Lambda function
8. Function: `PillBuddy_TimeoutChecker`
9. Create rule

## Input Event Format

EventBridge scheduled events have this format:

```json
{
  "version": "0",
  "id": "event-id",
  "detail-type": "Scheduled Event",
  "source": "aws.events",
  "account": "123456789012",
  "time": "2024-01-15T10:00:00Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:events:us-east-1:123456789012:rule/PillBuddy_TimeoutChecker_Schedule"
  ],
  "detail": {}
}
```

The Lambda function doesn't use the event content - it performs a full scan on each invocation.

## Output Format

```json
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "prescriptions_checked": 5,
    "notifications_sent": 2,
    "within_timeout": 3
  }
}
```

## Processing Flow

### Scenario 1: Bottle Out for 12 Minutes

**State**:

- Prescription: Aspirin, slot 2
- removal_timestamp: 1700000000000
- current_time: 1700000720000 (12 minutes later)

**Processing**:

1. Scan finds prescription with removal_timestamp
2. Calculate elapsed: 720,000 ms (12 minutes)
3. Check: 720,000 >= 600,000 (threshold)
4. Send notification: "Reminder: Please return your Aspirin bottle to slot 2 of your PillBuddy."

**Result**: `notification_sent`

### Scenario 2: Bottle Out for 7 Minutes

**State**:

- Prescription: Vitamin D, slot 1
- removal_timestamp: 1700000000000
- current_time: 1700000420000 (7 minutes later)

**Processing**:

1. Scan finds prescription with removal_timestamp
2. Calculate elapsed: 420,000 ms (7 minutes)
3. Check: 420,000 < 600,000 (threshold)
4. No notification sent

**Result**: `within_timeout`

### Scenario 3: Bottle Already Returned

**State**:

- Prescription: Ibuprofen, slot 3
- removal_timestamp: null

**Processing**:

1. Scan filters out prescription (removal_timestamp is null)
2. Not included in check

**Result**: Not processed

## Error Handling

### DynamoDB Scan Failure

**Condition**: Cannot scan Prescriptions table

**Response**:

- Log error to CloudWatch
- Return empty list
- Continue with remaining processing

**Recovery**: Next scheduled run will retry

### Notification Send Failure

**Condition**: Cannot send Alexa notification

**Response**:

- Log error to CloudWatch
- Continue processing other prescriptions
- Non-critical error

**Recovery**: Next scheduled run will retry if bottle still out

## Performance Considerations

### Scan Efficiency

- Uses DynamoDB Scan with FilterExpression
- For hackathon scale (few devices), scan is acceptable
- For production, consider:
  - GSI on removal_timestamp for efficient queries
  - Maintain separate "bottles_out" tracking table
  - Use DynamoDB Streams to trigger timeout checks

### Pagination

- Handles DynamoDB pagination automatically
- Processes all prescriptions across multiple pages
- No limit on number of prescriptions

### Execution Frequency

- Runs every 5 minutes
- Timeout threshold is 10 minutes
- Ensures at least 2 checks before timeout
- May send multiple notifications if bottle remains out

## Testing

### Test Scenario 1: Manual Invocation

```bash
# Invoke Lambda manually
aws lambda invoke \
  --function-name PillBuddy_TimeoutChecker \
  --payload '{}' \
  response.json

# View response
cat response.json
```

### Test Scenario 2: Create Test Prescription

```python
import boto3
import time

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('PillBuddy_Prescriptions')

# Create prescription with old removal timestamp (15 minutes ago)
table.put_item(
    Item={
        'device_id': 'test_device',
        'slot': 1,
        'prescription_name': 'Test Medication',
        'pill_count': 20,
        'initial_count': 30,
        'has_refills': True,
        'removal_timestamp': int((time.time() - 900) * 1000),  # 15 minutes ago
        'created_at': int(time.time() * 1000),
        'updated_at': int(time.time() * 1000)
    }
)
```

**Expected Behavior**:

- Lambda finds prescription with removal_timestamp
- Calculates elapsed time: ~900,000 ms (15 minutes)
- Sends notification (exceeds 10-minute threshold)
- Returns `notification_sent` status

### Test Scenario 3: Bottle Within Timeout

```python
# Create prescription with recent removal timestamp (3 minutes ago)
table.put_item(
    Item={
        'device_id': 'test_device',
        'slot': 2,
        'prescription_name': 'Test Medication 2',
        'pill_count': 15,
        'initial_count': 30,
        'has_refills': False,
        'removal_timestamp': int((time.time() - 180) * 1000),  # 3 minutes ago
        'created_at': int(time.time() * 1000),
        'updated_at': int(time.time() * 1000)
    }
)
```

**Expected Behavior**:

- Lambda finds prescription with removal_timestamp
- Calculates elapsed time: ~180,000 ms (3 minutes)
- No notification sent (within 10-minute threshold)
- Returns `within_timeout` status

## Deployment

### Using AWS CLI

```bash
# Package the Lambda
cd infrastructure/lambda/timeout_checker
zip -r function.zip lambda_function.py

# Create Lambda function
aws lambda create-function \
  --function-name PillBuddy_TimeoutChecker \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/PillBuddyTimeoutCheckerRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 10 \
  --memory-size 128 \
  --environment Variables="{
    PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,
    ALEXA_SKILL_ID=YOUR_SKILL_ID
  }"

# Create EventBridge rule (see EventBridge section above)
```

### Using AWS CDK

```python
# Add to infrastructure/pillbuddy_stack.py

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

# Grant DynamoDB permissions
prescriptions_table.grant_read_data(timeout_checker)

# Create EventBridge rule
rule = events.Rule(
    self, "TimeoutCheckerSchedule",
    schedule=events.Schedule.rate(Duration.minutes(5))
)
rule.add_target(targets.LambdaFunction(timeout_checker))
```

## Monitoring

### CloudWatch Logs

Monitor these log entries:

- "Starting timeout check..."
- "Found X prescriptions with bottles removed"
- "Timeout notification sent for device X, slot Y"
- "Within timeout for device X, slot Y"
- "Timeout check complete: X notifications sent"

### CloudWatch Metrics

Track these metrics:

- Lambda invocations (should be ~12 per hour)
- Lambda errors
- Lambda duration
- Custom metric: notifications_sent (via log parsing)

### CloudWatch Alarms

Recommended alarms:

- Lambda errors > 0 in 5 minutes
- Lambda duration > 8 seconds (approaching timeout)
- No invocations in 10 minutes (EventBridge rule issue)

## Troubleshooting

### Issue: No notifications being sent

**Check**:

1. Prescriptions have non-null removal_timestamp
2. Elapsed time exceeds 10 minutes
3. CloudWatch Logs show "notification_sent" status
4. Alexa skill has proactive events enabled
5. User has granted notification permissions

### Issue: Lambda timing out

**Check**:

1. Number of prescriptions in table
2. DynamoDB scan performance
3. Increase timeout if needed (currently 10s)

### Issue: EventBridge not triggering

**Check**:

1. Rule is in ENABLED state
2. Rule has correct target (Lambda ARN)
3. Lambda has permission for events.amazonaws.com
4. CloudWatch Logs show invocations every 5 minutes

### Issue: Duplicate notifications

**Expected Behavior**: If bottle remains out, user will receive notifications every 5 minutes after the 10-minute threshold. This is intentional to ensure the user is reminded.

**To Reduce Frequency**: Modify EventBridge schedule to run less frequently (e.g., every 10 or 15 minutes).

## Alexa Proactive Notifications

### Setup Requirements

1. **Enable Proactive Events** in Alexa Developer Console:
   - Go to Build → Permissions
   - Enable "Alexa::Devices::All::Notifications::Write"

2. **User Consent**: Users must grant notification permissions when enabling the skill

3. **Production Implementation**: Replace placeholder with Alexa Events API:

```python
import requests

def send_alexa_notification(device_id, message):
    # Get OAuth token
    token = get_alexa_oauth_token()

    # Create proactive event
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "referenceId": f"timeout-{device_id}-{int(time.time())}",
        "expiryTime": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
        "event": {
            "name": "AMAZON.MessageAlert.Activated",
            "payload": {
                "state": {
                    "status": "UNREAD",
                    "freshness": "NEW"
                },
                "messageGroup": {
                    "creator": {
                        "name": "PillBuddy"
                    },
                    "count": 1,
                    "urgency": "URGENT"
                }
            }
        },
        "localizedAttributes": [
            {
                "locale": "en-US",
                "contentTitle": "PillBuddy Reminder",
                "contentBody": message
            }
        ],
        "relevantAudience": {
            "type": "Unicast",
            "payload": {
                "user": user_id  # Map device_id to Alexa user_id
            }
        }
    }

    # Send to Alexa Events API
    response = requests.post(
        "https://api.amazonalexa.com/v1/proactiveEvents/stages/development",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=event
    )

    return response.status_code == 202
```

## Related Components

- **IoT Event Processor Lambda**: Sets removal_timestamp when bottle removed
- **Alexa Handler Lambda**: Handles voice commands
- **DynamoDB Prescriptions Table**: Stores removal timestamps
- **EventBridge**: Triggers Lambda on schedule

## References

- Design Document: Algorithm 3 (checkBottleReturnTimeout)
- Design Document: Lambda Function Specifications - Timeout Checker
- Design Document: Correctness Property 4 (Removal Timestamp Invariant)
- AWS EventBridge Scheduled Rules: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html
- Alexa Proactive Events API: https://developer.amazon.com/docs/smapi/proactive-events-api.html
