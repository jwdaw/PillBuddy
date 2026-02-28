# PillBuddy IoT Event Processor Lambda

This Lambda function processes IoT Core events from ESP32 devices, manages device state, tracks pill counts, and sends notifications.

## Overview

The IoT Event Processor is triggered by AWS IoT Core rules when ESP32 devices publish events to the `pillbuddy/events/{device_id}` MQTT topic. It implements the core business logic for:

- Event logging with automatic 30-day TTL
- Device state tracking
- Pill count management with non-negativity guarantee
- Refill/disposal reminder notifications
- LED control via IoT commands
- Event deduplication using sequence numbers

## Architecture

```
ESP32 Device → IoT Core (MQTT) → IoT Rule → Lambda → DynamoDB
                                              ↓
                                         IoT Core (LED commands)
                                              ↓
                                         Alexa Notifications
```

## Environment Variables

| Variable              | Description                      | Example                                      |
| --------------------- | -------------------------------- | -------------------------------------------- |
| `DEVICES_TABLE`       | DynamoDB table for device state  | `PillBuddy_Devices`                          |
| `PRESCRIPTIONS_TABLE` | DynamoDB table for prescriptions | `PillBuddy_Prescriptions`                    |
| `EVENTS_TABLE`        | DynamoDB table for event logs    | `PillBuddy_Events`                           |
| `IOT_ENDPOINT`        | AWS IoT Core endpoint URL        | `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com` |
| `ALEXA_SKILL_ID`      | Alexa skill ID for notifications | `amzn1.ask.skill.xxxxx`                      |
| `AWS_REGION`          | AWS region                       | `us-east-1`                                  |

## IAM Permissions Required

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
      "Action": "events:PutRule",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "events:PutTargets",
      "Resource": "*"
    }
  ]
}
```

## Lambda Configuration

- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Handler**: `lambda_function.lambda_handler`

## Input Event Format

The Lambda expects IoT Core events in the following format:

```json
{
  "device_id": "esp32_001",
  "event_type": "slot_state_changed",
  "slot": 2,
  "state": "not_in_holder",
  "in_holder": false,
  "sensor_level": 0,
  "ts_ms": 1700000000000,
  "sequence": 120
}
```

### Event Fields

- `device_id` (string): Unique ESP32 device identifier
- `event_type` (string): Always "slot_state_changed"
- `slot` (number): Slot number (1, 2, or 3)
- `state` (string): "in_holder" or "not_in_holder"
- `in_holder` (boolean): True if bottle is in holder
- `sensor_level` (number): 0 (LOW) or 1 (HIGH)
- `ts_ms` (number): Unix timestamp in milliseconds
- `sequence` (number): Monotonically increasing sequence number for deduplication

## Processing Logic

### Algorithm 2: Process Slot State Changed

1. **Event Deduplication**: Check sequence number against last processed
2. **Event Logging**: Store event in Events table with 30-day TTL
3. **Device State Update**: Update slot state and last_seen timestamp
4. **Prescription Lookup**: Get prescription for the slot
5. **Bottle Removal** (if `in_holder = false`):
   - Decrement pill count (floor at 0)
   - Set removal_timestamp
   - Send refill/disposal reminder if count < 5
6. **Bottle Return** (if `in_holder = true`):
   - Clear removal_timestamp
   - Publish LED turn_off command

### Correctness Properties

- **Property 2**: Pill Count Non-Negativity - pill_count ≥ 0 always
- **Property 4**: Removal Timestamp Invariant - removal_timestamp set only when bottle out
- **Property 5**: Refill Reminder Threshold - reminder sent if count < 5 and has_refills

## Error Handling

### Scenario 4: Duplicate Event Processing

- Uses sequence numbers to detect duplicates
- Skips processing if sequence ≤ last processed
- Logs duplicate detection

### Scenario 6: Prescription Not Found

- Logs event normally
- Updates device state
- Skips pill count operations
- No notification sent

### Scenario 7: Negative Pill Count

- Floors pill count at 0
- Sends disposal reminder
- Logs anomaly

## IoT Core Integration

### Subscribe Topic (Input)

- **Topic**: `pillbuddy/events/{device_id}`
- **Direction**: ESP32 → AWS
- **QoS**: 1

### Publish Topic (Output)

- **Topic**: `pillbuddy/cmd/{device_id}`
- **Direction**: AWS → ESP32
- **QoS**: 1
- **Payload**: `{"action": "turn_on|turn_off", "slot": 1|2|3}`

## IoT Rule Configuration

Create an IoT Rule to trigger this Lambda:

```sql
SELECT * FROM 'pillbuddy/events/+'
```

**Rule Action**: Lambda function (PillBuddy_IoTEventProcessor)

## Testing

### Test Event 1: Bottle Removal

```json
{
  "device_id": "esp32_001",
  "event_type": "slot_state_changed",
  "slot": 2,
  "state": "not_in_holder",
  "in_holder": false,
  "sensor_level": 0,
  "ts_ms": 1700000000000,
  "sequence": 120
}
```

**Expected Behavior**:

- Event logged to Events table
- Device slot 2 state updated to `in_holder: false`
- Pill count decremented by 1
- removal_timestamp set
- If count < 5: refill/disposal reminder sent

### Test Event 2: Bottle Return

```json
{
  "device_id": "esp32_001",
  "event_type": "slot_state_changed",
  "slot": 2,
  "state": "in_holder",
  "in_holder": true,
  "sensor_level": 1,
  "ts_ms": 1700000060000,
  "sequence": 121
}
```

**Expected Behavior**:

- Event logged to Events table
- Device slot 2 state updated to `in_holder: true`
- removal_timestamp cleared
- LED turn_off command published to IoT Core

### Test Event 3: Duplicate Event

```json
{
  "device_id": "esp32_001",
  "event_type": "slot_state_changed",
  "slot": 2,
  "state": "not_in_holder",
  "in_holder": false,
  "sensor_level": 0,
  "ts_ms": 1700000000000,
  "sequence": 120
}
```

**Expected Behavior** (if sequence 120 already processed):

- Returns status "duplicate"
- No database updates
- Event logged for monitoring

## Deployment

### Using AWS CLI

```bash
# Package the Lambda
cd infrastructure/lambda/iot_event_processor
zip -r function.zip lambda_function.py

# Create/update Lambda function
aws lambda create-function \
  --function-name PillBuddy_IoTEventProcessor \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/PillBuddyIoTProcessorRole \
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
  }"
```

### Using AWS CDK

See `infrastructure/pillbuddy_stack.py` for CDK deployment configuration.

## Monitoring

### CloudWatch Logs

All processing steps are logged to CloudWatch Logs:

- Event reception
- Deduplication checks
- Database operations
- LED command publishing
- Error conditions

### CloudWatch Metrics

Monitor these metrics:

- Lambda invocations
- Lambda errors
- Lambda duration
- DynamoDB read/write capacity
- IoT publish success/failure

## Troubleshooting

### Issue: Events not being processed

**Check**:

1. IoT Rule is active and SQL is correct
2. Lambda has permission to be invoked by IoT Core
3. CloudWatch Logs for error messages

### Issue: Pill count not updating

**Check**:

1. Prescription exists for the device/slot
2. Lambda has DynamoDB UpdateItem permission
3. Event contains valid slot number (1-3)

### Issue: LED commands not working

**Check**:

1. IoT endpoint is correct
2. Lambda has iot:Publish permission
3. ESP32 is subscribed to pillbuddy/cmd/{device_id}
4. Device is online and connected

## Related Components

- **Alexa Handler Lambda**: Handles voice commands and setup
- **Timeout Checker Lambda**: Monitors bottle return timeouts
- **ESP32 Firmware**: Publishes events and subscribes to commands
- **DynamoDB Tables**: Stores device state, prescriptions, and events

## References

- Design Document: Algorithm 2 (processSlotStateChanged)
- Design Document: Correctness Properties 2, 4, 5
- Design Document: Error Handling Scenarios 4, 6, 7
