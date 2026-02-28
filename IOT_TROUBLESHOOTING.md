# IoT Event Processing Troubleshooting Guide

## Issue: Button presses visible in MQTT Test Client but Lambda not triggered

### What We Know

✅ **IoT Rule is configured correctly**:

- Rule Name: `PillBuddyEventRule`
- Topic Pattern: `pillbuddy/events/+`
- Target: `PillBuddy_IoTEventProcessor` Lambda
- Status: Enabled

✅ **Lambda was triggered on power-on** (3 events at 14:19:01 UTC)

❌ **Lambda not triggered by subsequent button presses**

---

## Root Cause Analysis

The most likely causes:

### 1. ESP32 Publishing to Wrong Topic

**Expected topic**: `pillbuddy/events/pillbuddy-esp32-1`  
**IoT Rule pattern**: `pillbuddy/events/+`

If your ESP32 is publishing to a different topic (e.g., `pillbuddy/pillbuddy-esp32-1` or `events/pillbuddy-esp32-1`), the IoT Rule won't match.

### 2. Message Format Issue

The IoT Rule SQL expects certain fields:

```sql
SELECT *,
  topic(3) as device_id,
  timestamp() as ts_ms,
  0 as sequence,
  case in_holder when true then 'in_holder' else 'not_in_holder' end as state,
  case in_holder when true then 1 else 0 end as sensor_level
FROM 'pillbuddy/events/+'
```

If the message doesn't have the `in_holder` field, the SQL transformation might fail.

### 3. MQTT Test Client Subscription

You might be subscribed to a different topic in the MQTT Test Client than what the IoT Rule is listening to.

---

## Diagnostic Steps

### Step 1: Check What Topic ESP32 is Publishing To

In the AWS IoT Core MQTT Test Client:

1. Subscribe to `#` (wildcard - all topics)
2. Press a button on your ESP32
3. Note the EXACT topic shown in the test client

**Expected**: `pillbuddy/events/pillbuddy-esp32-1`

### Step 2: Check Message Format

Look at the message payload in the MQTT Test Client. It should be:

```json
{
  "event_type": "slot_state_changed",
  "slot": 2,
  "in_holder": false
}
```

**Required fields**:

- `event_type`
- `slot`
- `in_holder`

### Step 3: Test IoT Rule Directly

Publish a test message from the MQTT Test Client:

**Topic**: `pillbuddy/events/pillbuddy-esp32-1`

**Payload**:

```json
{
  "event_type": "slot_state_changed",
  "slot": 2,
  "in_holder": false
}
```

Then check Lambda logs:

```bash
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --since 1m --region us-east-1
```

If this works, the issue is with your ESP32 code.

### Step 4: Check IoT Core Metrics

```bash
aws iot get-statistics --region us-east-1
```

This shows if messages are being received by IoT Core.

---

## Common Issues & Fixes

### Issue 1: Topic Mismatch

**Symptom**: MQTT Test Client shows messages, but Lambda not triggered

**Fix**: Update ESP32 code to publish to correct topic:

```cpp
// Correct topic format
const char* EVENT_TOPIC = "pillbuddy/events/pillbuddy-esp32-1";
```

### Issue 2: Missing `in_holder` Field

**Symptom**: Lambda triggered but errors in logs

**Fix**: Ensure ESP32 publishes all required fields:

```cpp
{
  "event_type": "slot_state_changed",
  "slot": 2,
  "in_holder": false  // REQUIRED
}
```

### Issue 3: QoS Level

**Symptom**: Intermittent message delivery

**Fix**: Use QoS 1 for guaranteed delivery:

```cpp
client.publish(EVENT_TOPIC, payload, 1);  // QoS 1
```

### Issue 4: MQTT Connection Dropped

**Symptom**: First few messages work, then stop

**Fix**: Check ESP32 MQTT connection status and implement reconnection logic.

---

## Quick Test Commands

### 1. Check Recent Lambda Invocations

```bash
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --since 5m --region us-east-1 | grep "Received event"
```

### 2. Publish Test Event via CLI

```bash
aws iot-data publish \
  --topic "pillbuddy/events/pillbuddy-esp32-1" \
  --payload '{"event_type":"slot_state_changed","slot":2,"in_holder":false}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1
```

### 3. Check IoT Rule Status

```bash
aws iot get-topic-rule --rule-name PillBuddyEventRule --region us-east-1 | jq '.rule.ruleDisabled'
```

Should return `false` (rule is enabled).

### 4. Check Lambda Permissions

```bash
aws lambda get-policy --function-name PillBuddy_IoTEventProcessor --region us-east-1 | jq -r '.Policy' | jq .
```

Should show IoT Core has permission to invoke the Lambda.

---

## Verification Checklist

Use this checklist to verify your setup:

- [ ] ESP32 publishes to `pillbuddy/events/pillbuddy-esp32-1`
- [ ] Message includes `event_type`, `slot`, and `in_holder` fields
- [ ] IoT Rule `PillBuddyEventRule` is enabled
- [ ] IoT Rule topic pattern is `pillbuddy/events/+`
- [ ] Lambda `PillBuddy_IoTEventProcessor` exists and is active
- [ ] Lambda has permission for IoT Core to invoke it
- [ ] Test message from MQTT Test Client triggers Lambda
- [ ] ESP32 MQTT connection is stable

---

## Expected Behavior

When everything is working correctly:

1. **ESP32 publishes** to `pillbuddy/events/pillbuddy-esp32-1`
2. **IoT Rule matches** the topic pattern `pillbuddy/events/+`
3. **IoT Rule transforms** the message (adds device_id, ts_ms, etc.)
4. **Lambda is invoked** with transformed message
5. **Lambda logs** show "Received event: {...}"
6. **DynamoDB updated** with event and device state
7. **Pill count decremented** (if bottle removed)

---

## Next Steps

1. **Check the exact topic** your ESP32 is publishing to
2. **Verify message format** has all required fields
3. **Test with MQTT Test Client** to isolate ESP32 vs AWS issue
4. **Check Lambda logs** after each test

If the test from MQTT Test Client works but ESP32 doesn't, the issue is in your ESP32 code (topic or message format).

If neither works, there's an issue with the IoT Rule or Lambda configuration.

---

## Contact Information

If you need help:

1. Share the exact topic shown in MQTT Test Client
2. Share the exact message payload
3. Share Lambda logs from the last 5 minutes
