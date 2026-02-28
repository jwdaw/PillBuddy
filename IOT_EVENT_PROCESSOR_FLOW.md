# IoT Event Processor - Data Flow

## What Your ESP32 Sends

```json
{
  "event_type": "slot_state_changed",
  "slot": 2,
  "in_holder": false
}
```

Published to: `pillbuddy/events/pillbuddy-esp32-1`

---

## What the Lambda Receives (After IoT Rule Transformation)

```json
{
  "event_type": "slot_state_changed",
  "slot": 2,
  "in_holder": false,
  "device_id": "pillbuddy-esp32-1", // Added by IoT Rule from topic
  "ts_ms": 1772269798992, // Added by IoT Rule (current time)
  "sequence": 0, // Added by IoT Rule (always 0)
  "state": "not_in_holder", // Added by IoT Rule (derived from in_holder)
  "sensor_level": 0 // Added by IoT Rule (derived from in_holder)
}
```

---

## Processing Flow in Lambda

### Step 1: Extract Data

```python
device_id = event['device_id']           # "pillbuddy-esp32-1"
slot = int(event['slot'])                # 2
in_holder = event['in_holder']          # false
timestamp = event.get('ts_ms')           # 1772269798992
sequence = event.get('sequence', 0)      # 0
state = event.get('state')               # "not_in_holder"
sensor_level = event.get('sensor_level') # 0
```

### Step 2: Validate Slot Number

```python
if slot not in [1, 2, 3]:
    return error
```

### Step 3: Skip Deduplication (sequence = 0)

```python
# Since sequence is always 0, deduplication is skipped
if sequence > 0 and is_duplicate_event(device_id, sequence):
    return duplicate
```

### Step 4: Log Event to Events Table

```python
events_table.put_item({
    'device_id': 'pillbuddy-esp32-1',
    'timestamp': 1772269798992,
    'event_type': 'slot_state_changed',
    'slot': 2,
    'state': 'not_in_holder',
    'in_holder': false,
    'sensor_level': 0,
    'sequence': 0,
    'ttl': 1774861798  # Auto-delete after 30 days
})
```

### Step 5: Update Device State

```python
devices_table.update_item({
    Key: {'device_id': 'pillbuddy-esp32-1'},
    UpdateExpression: 'SET slots.2.in_holder = false,
                           slots.2.last_state_change = 1772269798992,
                           last_seen = 1772269798992'
})
```

### Step 6: Get Prescription for This Slot

```python
prescription = prescriptions_table.get_item({
    Key: {
        'device_id': 'pillbuddy-esp32-1',
        'slot': 2
    }
})
```

If no prescription exists → Done (return success)

### Step 7A: If Bottle REMOVED (in_holder = false)

**Decrement Pill Count:**

```python
current_count = prescription['pill_count']  # e.g., 10
new_count = max(0, current_count - 1)       # 9 (never goes below 0)

prescriptions_table.update_item({
    Key: {'device_id': 'pillbuddy-esp32-1', 'slot': 2},
    UpdateExpression: 'SET pill_count = 9,
                           removal_timestamp = 1772269798992,
                           updated_at = 1772269798992'
})
```

**Check Refill Reminder:**

```python
if new_count < 5:  # Refill threshold
    if prescription['has_refills']:
        message = "Your Aspirin is running low with 4 pills remaining. Please get a refill soon."
    else:
        message = "Your Aspirin is running low with 4 pills remaining. Please dispose of the empty bottle."

    # Log message (Alexa notifications require additional setup)
    print(f"Refill reminder: {message}")
```

### Step 7B: If Bottle RETURNED (in_holder = true)

**Clear Removal Timestamp:**

```python
prescriptions_table.update_item({
    Key: {'device_id': 'pillbuddy-esp32-1', 'slot': 2},
    UpdateExpression: 'SET removal_timestamp = null,
                           updated_at = 1772269798992'
})
```

**Send LED Turn Off Command:**

```python
iot_client.publish(
    topic='pillbuddy/cmd/pillbuddy-esp32-1',
    payload={
        'action': 'turn_off',
        'slot': 2
    }
)
```

Your ESP32 receives on `pillbuddy/cmd/pillbuddy-esp32-1`:

```json
{
  "action": "turn_off",
  "slot": 2
}
```

---

## Summary: What Happens to Your Data

| Your ESP32 Field | How It's Used                                                                                |
| ---------------- | -------------------------------------------------------------------------------------------- |
| `event_type`     | Determines which handler function to call                                                    |
| `slot`           | Identifies which slot (1, 2, or 3)                                                           |
| `in_holder`      | **false** = decrement pills, set removal time<br>**true** = clear removal time, turn off LED |

| IoT Rule Added Field | How It's Used                              |
| -------------------- | ------------------------------------------ |
| `device_id`          | Identifies which device in DynamoDB        |
| `ts_ms`              | Timestamp for all database updates         |
| `sequence`           | Skipped (always 0, deduplication disabled) |
| `state`              | Stored in Events table for history         |
| `sensor_level`       | Stored in Events table for history         |

---

## Database Changes Per Event

### When Bottle Removed (in_holder: false)

**Devices Table:**

- `last_seen` = current timestamp
- `slots.2.in_holder` = false
- `slots.2.last_state_change` = current timestamp

**Prescriptions Table:**

- `pill_count` = decremented by 1 (min 0)
- `removal_timestamp` = current timestamp
- `updated_at` = current timestamp

**Events Table:**

- New event record (auto-deletes after 30 days)

### When Bottle Returned (in_holder: true)

**Devices Table:**

- `last_seen` = current timestamp
- `slots.2.in_holder` = true
- `slots.2.last_state_change` = current timestamp

**Prescriptions Table:**

- `removal_timestamp` = null
- `updated_at` = current timestamp

**Events Table:**

- New event record (auto-deletes after 30 days)

**IoT Core:**

- Publishes LED command to `pillbuddy/cmd/pillbuddy-esp32-1`

---

## Key Points

1. **Your ESP32 only sends 3 fields** - AWS adds the rest
2. **Pill count only decrements on removal** - never on return
3. **Pill count never goes below 0** - uses `max(0, count - 1)`
4. **Refill reminder triggers at < 5 pills** - logged to CloudWatch
5. **LED turn_off command sent on bottle return** - your ESP32 receives this
6. **All events logged with 30-day TTL** - automatic cleanup
7. **Deduplication disabled** - every event processes (sequence always 0)

---

## Testing Your ESP32

**Test 1: Remove bottle from slot 2**

```
ESP32 publishes: {"event_type":"slot_state_changed","slot":2,"in_holder":false}
Result: Pill count decrements, removal timestamp set
```

**Test 2: Return bottle to slot 2**

```
ESP32 publishes: {"event_type":"slot_state_changed","slot":2,"in_holder":true}
Result: Removal timestamp cleared, LED turn_off command sent
```

**Check Results:**

```bash
# View Lambda logs
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --follow --region us-east-1

# Check prescription
aws dynamodb get-item \
  --table-name PillBuddy_Prescriptions \
  --key '{"device_id":{"S":"pillbuddy-esp32-1"},"slot":{"N":"2"}}' \
  --region us-east-1
```
