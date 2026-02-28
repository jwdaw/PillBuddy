# IoT Event Processor Lambda - Implementation Summary

## Overview

Successfully implemented the PillBuddy IoT Event Processor Lambda function that processes real-time events from ESP32 devices via AWS IoT Core. This Lambda is the core of the pill tracking system, managing device state, pill counts, and user notifications.

## Implementation Status

✅ **Task 5.1**: Lambda function structure and environment setup
✅ **Task 5.2**: Event logging and device state update
✅ **Task 5.3**: Bottle removal logic
✅ **Task 5.4**: Refill reminder logic
✅ **Task 5.5**: Bottle return logic
✅ **Task 5.6**: Event deduplication

## Files Created

1. **lambda_function.py** (520 lines)
   - Main Lambda handler
   - Event processing logic
   - DynamoDB operations
   - IoT Core integration
   - Alexa notification placeholders

2. **requirements.txt**
   - boto3 dependency specification
   - Uses built-in Python libraries

3. **README.md**
   - Comprehensive documentation
   - Architecture overview
   - API reference
   - Testing guide

4. **test_events.json**
   - Sample test events
   - Various scenarios (removal, return, duplicate, invalid)

5. **DEPLOYMENT_GUIDE.md**
   - Step-by-step deployment instructions
   - IAM role setup
   - IoT Rule configuration
   - Testing procedures
   - Troubleshooting guide

## Key Features Implemented

### 1. Event Processing Pipeline

```
IoT Core Event → Deduplication → Event Logging → Device Update → Prescription Logic
```

- Validates event structure
- Checks sequence numbers for duplicates
- Logs all events with 30-day TTL
- Updates device state atomically

### 2. Bottle Removal Logic (Task 5.3)

**Implements Algorithm 2 from design document:**

- Decrements pill count when bottle removed (`in_holder = false`)
- Sets `removal_timestamp` in Prescriptions table
- Floors pill count at 0 (Property 2: Pill Count Non-Negativity)
- Handles negative count scenarios gracefully

**Code Location**: `process_bottle_removal()` function

### 3. Refill Reminder Logic (Task 5.4)

**Implements Property 5: Refill Reminder Threshold**

- Checks if pill count < 5 after decrement
- Sends different messages based on `has_refills` flag:
  - **With refills**: "Please get a refill soon"
  - **No refills**: "Please dispose of the empty bottle"
- Logs notification for monitoring

**Code Location**: `send_refill_reminder()` function

### 4. Bottle Return Logic (Task 5.5)

**Implements Property 4: Removal Timestamp Invariant**

- Clears `removal_timestamp` when bottle returned (`in_holder = true`)
- Publishes LED `turn_off` command to IoT Core
- Maintains state consistency

**Code Location**: `process_bottle_return()` function

### 5. Event Deduplication (Task 5.6)

**Implements Error Scenario 4: Duplicate Event Processing**

- Tracks `last_sequence` per device in Devices table
- Skips processing if `sequence <= last_sequence`
- Prevents duplicate pill count decrements
- Logs duplicate detection for monitoring

**Code Location**: `is_duplicate_event()` and `update_last_sequence()` functions

### 6. Error Handling

Implements multiple error scenarios from design document:

- **Scenario 4**: Duplicate event processing (sequence numbers)
- **Scenario 6**: Prescription not found (graceful skip)
- **Scenario 7**: Negative pill count (floor at 0)
- **Invalid slot**: Validation and rejection

## Correctness Properties Maintained

### Property 2: Pill Count Non-Negativity

```python
new_count = max(0, current_count - 1)  # Floor at 0
```

### Property 4: Removal Timestamp Invariant

- Set only when `in_holder = false`
- Cleared when `in_holder = true`

### Property 5: Refill Reminder Threshold

```python
if new_count < REFILL_THRESHOLD:  # REFILL_THRESHOLD = 5
    send_refill_reminder(...)
```

### Property 7: Event TTL Expiration

```python
ttl = int(timestamp / 1000) + (TTL_DAYS * 24 * 60 * 60)  # 30 days
```

## Lambda Configuration

| Setting | Value                          |
| ------- | ------------------------------ |
| Runtime | Python 3.11                    |
| Memory  | 256 MB                         |
| Timeout | 30 seconds                     |
| Handler | lambda_function.lambda_handler |

## Environment Variables

- `DEVICES_TABLE`: PillBuddy_Devices
- `PRESCRIPTIONS_TABLE`: PillBuddy_Prescriptions
- `EVENTS_TABLE`: PillBuddy_Events
- `IOT_ENDPOINT`: AWS IoT Core endpoint
- `ALEXA_SKILL_ID`: Alexa skill ID
- `AWS_REGION`: us-east-1

## IAM Permissions Required

- **DynamoDB**: GetItem, PutItem, UpdateItem on all 3 tables
- **IoT Core**: Publish to `pillbuddy/cmd/*` topics
- **EventBridge**: PutRule, PutTargets (for timeout scheduling)
- **CloudWatch Logs**: CreateLogGroup, CreateLogStream, PutLogEvents

## Integration Points

### Input: IoT Core Events

**Topic**: `pillbuddy/events/{device_id}`

**Message Format**:

```json
{
  "device_id": "esp32_001",
  "event_type": "slot_state_changed",
  "slot": 2,
  "in_holder": false,
  "sensor_level": 0,
  "ts_ms": 1700000000000,
  "sequence": 120
}
```

### Output: IoT Core Commands

**Topic**: `pillbuddy/cmd/{device_id}`

**Message Format**:

```json
{
  "action": "turn_off",
  "slot": 2
}
```

### Output: DynamoDB Tables

1. **Events Table**: All events logged with TTL
2. **Devices Table**: Slot states and last_seen updated
3. **Prescriptions Table**: Pill counts and removal timestamps updated

### Output: Alexa Notifications (Placeholder)

Currently logs notification messages. Full implementation requires:

- Alexa Proactive Events API integration
- User consent for notifications
- Skill certification

## Testing

### Test Events Provided

1. **bottle_removal_event**: Normal bottle removal
2. **bottle_return_event**: Normal bottle return
3. **duplicate_event**: Duplicate sequence number
4. **slot_1_removal**: Test slot 1
5. **slot_3_return**: Test slot 3
6. **invalid_slot**: Invalid slot number (5)
7. **low_pill_count_with_refills**: Trigger refill reminder
8. **low_pill_count_no_refills**: Trigger disposal reminder

### Testing Approach

1. **Unit Testing**: Test individual functions with mock data
2. **Integration Testing**: Test with actual DynamoDB tables
3. **End-to-End Testing**: Test with IoT Core and ESP32 device

## Known Limitations

### 1. Alexa Notifications

Currently implemented as logging only. Full implementation requires:

- Alexa Proactive Events API setup
- User permission grants
- Skill certification for production

**Workaround**: Use CloudWatch Logs to monitor notifications

### 2. Timeout Scheduling

Timeout checking (10-minute bottle return reminder) is handled by a separate Lambda (Task 6) that runs every 5 minutes via EventBridge.

**Note**: This is by design for the hackathon approach

### 3. No Authentication

As per hackathon requirements, no authentication or authorization is implemented.

**Production Note**: Add device authentication and user authorization

## Performance Characteristics

### Expected Latency

- Event processing: 100-500ms
- DynamoDB operations: 10-50ms each
- IoT publish: 50-100ms
- Total: ~200-700ms per event

### Scalability

- Handles concurrent events from multiple devices
- DynamoDB auto-scales with provisioned capacity
- Lambda auto-scales up to account limits
- IoT Core handles 1000s of messages/second

### Cost Estimate (Hackathon Scale)

Assuming 3 devices, 10 events/day each:

- Lambda: ~900 invocations/month (free tier)
- DynamoDB: ~2700 writes/month (free tier)
- IoT Core: ~900 messages/month (free tier)

**Total**: $0/month (within free tier)

## Monitoring and Observability

### CloudWatch Logs

All operations logged:

- Event reception
- Deduplication checks
- Database operations
- LED commands
- Errors and exceptions

### CloudWatch Metrics

- Lambda invocations
- Lambda errors
- Lambda duration
- DynamoDB read/write capacity
- IoT publish success/failure

### Recommended Alarms

1. Lambda error rate > 5%
2. Lambda duration > 25 seconds
3. DynamoDB throttling events
4. IoT publish failures

## Code Quality

### Best Practices Followed

- ✅ Comprehensive error handling
- ✅ Detailed logging for debugging
- ✅ Input validation
- ✅ Idempotent operations (deduplication)
- ✅ Atomic database updates
- ✅ Clear function separation
- ✅ Extensive documentation

### Code Structure

```
lambda_function.py
├── lambda_handler()              # Entry point
├── handle_slot_state_changed()   # Main processing logic
├── is_duplicate_event()          # Deduplication
├── update_last_sequence()        # Sequence tracking
├── log_event()                   # Event logging
├── update_device_state()         # Device state update
├── get_prescription()            # Prescription lookup
├── process_bottle_removal()      # Removal logic
├── process_bottle_return()       # Return logic
├── send_refill_reminder()        # Notification logic
└── publish_led_command()         # IoT command publishing
```

## Next Steps

### Immediate (Task 6)

1. Implement Timeout Checker Lambda
2. Set up EventBridge scheduled rule (every 5 minutes)
3. Test timeout notifications

### Integration Testing

1. Deploy Lambda to AWS
2. Create IoT Rule to trigger Lambda
3. Test with ESP32 device
4. Verify end-to-end flow

### Production Readiness

1. Implement Alexa Proactive Events API
2. Add authentication/authorization
3. Set up monitoring dashboards
4. Configure CloudWatch alarms
5. Enable DynamoDB encryption
6. Add comprehensive error recovery

## Design Document Compliance

### Algorithms Implemented

- ✅ **Algorithm 2**: processSlotStateChanged (complete)
- ✅ All steps from design document implemented
- ✅ All error scenarios handled

### Properties Maintained

- ✅ **Property 2**: Pill Count Non-Negativity
- ✅ **Property 4**: Removal Timestamp Invariant
- ✅ **Property 5**: Refill Reminder Threshold
- ✅ **Property 7**: Event TTL Expiration

### Error Scenarios Handled

- ✅ **Scenario 4**: Duplicate Event Processing
- ✅ **Scenario 6**: Prescription Not Found
- ✅ **Scenario 7**: Negative Pill Count
- ✅ **Invalid Slot**: Validation and rejection

## Conclusion

The IoT Event Processor Lambda is fully implemented according to the design specification. All required functionality is in place, including event processing, state management, pill tracking, and notification logic. The implementation maintains all correctness properties and handles error scenarios gracefully.

The Lambda is ready for deployment and testing with the ESP32 hardware and AWS IoT Core infrastructure.

## Related Documentation

- [README.md](README.md) - Function overview and API reference
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
- [test_events.json](test_events.json) - Test event samples
- [Design Document](../../../.kiro/specs/pillbuddy-backend-alexa-integration/design.md) - System design
