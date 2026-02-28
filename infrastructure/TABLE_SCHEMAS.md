# DynamoDB Table Schemas Reference

## Table 1: PillBuddy_Devices

**Purpose**: Stores device connection status and real-time slot states

### Primary Key

- **Partition Key**: `device_id` (String) - Unique ESP32 device identifier

### Attributes

| Attribute  | Type    | Description                    | Example       |
| ---------- | ------- | ------------------------------ | ------------- |
| device_id  | String  | Unique device identifier       | "esp32_001"   |
| online     | Boolean | Device connection status       | true          |
| last_seen  | Number  | Unix timestamp in milliseconds | 1700000000000 |
| created_at | Number  | Unix timestamp in milliseconds | 1699000000000 |
| slots      | Map     | Nested map of slot states      | See below     |

### Slots Structure

```json
{
  "slots": {
    "1": {
      "in_holder": true,
      "last_state_change": 1700000000000
    },
    "2": {
      "in_holder": false,
      "last_state_change": 1699999000000
    },
    "3": {
      "in_holder": true,
      "last_state_change": 1699998000000
    }
  }
}
```

### Example Item

```json
{
  "device_id": "esp32_001",
  "online": true,
  "last_seen": 1700000000000,
  "created_at": 1699000000000,
  "slots": {
    "1": {
      "in_holder": true,
      "last_state_change": 1700000000000
    },
    "2": {
      "in_holder": false,
      "last_state_change": 1699999000000
    },
    "3": {
      "in_holder": true,
      "last_state_change": 1699998000000
    }
  }
}
```

### Access Patterns

- Get device status: `GetItem` by device_id
- Update slot state: `UpdateItem` by device_id
- Check online status: Query last_seen timestamp

---

## Table 2: PillBuddy_Prescriptions

**Purpose**: Stores prescription data for each device slot

### Primary Key

- **Partition Key**: `device_id` (String) - Device identifier
- **Sort Key**: `slot` (Number) - Slot number (1, 2, or 3)

### Attributes

| Attribute         | Type    | Description                             | Example               |
| ----------------- | ------- | --------------------------------------- | --------------------- |
| device_id         | String  | Device identifier                       | "esp32_001"           |
| slot              | Number  | Slot number (1-3)                       | 2                     |
| prescription_name | String  | Medication name                         | "Aspirin"             |
| pill_count        | Number  | Current pill count                      | 25                    |
| initial_count     | Number  | Starting pill count                     | 30                    |
| has_refills       | Boolean | Refill availability                     | true                  |
| created_at        | Number  | Unix timestamp                          | 1699000000000         |
| updated_at        | Number  | Unix timestamp                          | 1700000000000         |
| removal_timestamp | Number  | When bottle removed (null if in holder) | 1699999000000 or null |

### Example Item

```json
{
  "device_id": "esp32_001",
  "slot": 2,
  "prescription_name": "Aspirin",
  "pill_count": 25,
  "initial_count": 30,
  "has_refills": true,
  "created_at": 1699000000000,
  "updated_at": 1700000000000,
  "removal_timestamp": null
}
```

### Access Patterns

- Get prescription for slot: `GetItem` by device_id + slot
- Get all prescriptions for device: `Query` by device_id
- Update pill count: `UpdateItem` by device_id + slot
- Set/clear removal timestamp: `UpdateItem` by device_id + slot

### Validation Rules

- slot must be 1, 2, or 3
- pill_count must be >= 0
- initial_count must be > 0
- removal_timestamp is null when bottle is in holder

---

## Table 3: PillBuddy_Events

**Purpose**: Stores time-series events from ESP32 devices with automatic cleanup

### Primary Key

- **Partition Key**: `device_id` (String) - Device identifier
- **Sort Key**: `timestamp` (Number) - Unix timestamp in milliseconds

### Attributes

| Attribute    | Type    | Description                    | Example              |
| ------------ | ------- | ------------------------------ | -------------------- |
| device_id    | String  | Device identifier              | "esp32_001"          |
| timestamp    | Number  | Unix timestamp in milliseconds | 1700000000000        |
| event_type   | String  | Event type                     | "slot_state_changed" |
| slot         | Number  | Slot number (1-3)              | 2                    |
| state        | String  | Slot state                     | "not_in_holder"      |
| in_holder    | Boolean | Boolean state                  | false                |
| sensor_level | Number  | Sensor reading (0 or 1)        | 0                    |
| sequence     | Number  | ESP32 sequence number          | 120                  |
| ttl          | Number  | DynamoDB TTL for auto-deletion | 1702592000000        |

### Example Item

```json
{
  "device_id": "esp32_001",
  "timestamp": 1700000000000,
  "event_type": "slot_state_changed",
  "slot": 2,
  "state": "not_in_holder",
  "in_holder": false,
  "sensor_level": 0,
  "sequence": 120,
  "ttl": 1702592000000
}
```

### Access Patterns

- Get recent events: `Query` by device_id with timestamp range
- Get events for specific slot: `Query` by device_id, filter by slot
- Log new event: `PutItem`

### TTL Configuration

- **Attribute**: `ttl`
- **Calculation**: `timestamp + (30 * 24 * 60 * 60 * 1000)` (30 days)
- **Behavior**: DynamoDB automatically deletes items when current time > ttl value

### Validation Rules

- event_type must be "slot_state_changed"
- slot must be 1, 2, or 3
- state must be "in_holder" or "not_in_holder"
- sensor_level must be 0 or 1
- sequence must be >= 0

---

## Capacity Planning

### Provisioned Capacity (Hackathon)

| Table         | Read Capacity Units | Write Capacity Units | Monthly Cost (est.) |
| ------------- | ------------------- | -------------------- | ------------------- |
| Devices       | 5 RCU               | 5 WCU                | $0.65               |
| Prescriptions | 5 RCU               | 5 WCU                | $0.65               |
| Events        | 5 RCU               | 10 WCU               | $0.98               |
| **Total**     |                     |                      | **$2.28**           |

### Scaling Considerations

For production use:

- Consider on-demand billing for unpredictable traffic
- Add GSI for querying events by slot across devices
- Increase Events table write capacity for high-frequency logging
- Enable point-in-time recovery for data protection
- Add DynamoDB Streams for real-time processing

---

## Python Code Examples

### Create Device

```python
import boto3
import time

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('PillBuddy_Devices')

table.put_item(
    Item={
        'device_id': 'esp32_001',
        'online': True,
        'last_seen': int(time.time() * 1000),
        'created_at': int(time.time() * 1000),
        'slots': {
            '1': {'in_holder': False, 'last_state_change': 0},
            '2': {'in_holder': False, 'last_state_change': 0},
            '3': {'in_holder': False, 'last_state_change': 0}
        }
    }
)
```

### Create Prescription

```python
table = dynamodb.Table('PillBuddy_Prescriptions')

table.put_item(
    Item={
        'device_id': 'esp32_001',
        'slot': 1,
        'prescription_name': 'Aspirin',
        'pill_count': 30,
        'initial_count': 30,
        'has_refills': True,
        'created_at': int(time.time() * 1000),
        'updated_at': int(time.time() * 1000),
        'removal_timestamp': None
    }
)
```

### Log Event

```python
table = dynamodb.Table('PillBuddy_Events')

timestamp = int(time.time() * 1000)
ttl = timestamp + (30 * 24 * 60 * 60 * 1000)  # 30 days

table.put_item(
    Item={
        'device_id': 'esp32_001',
        'timestamp': timestamp,
        'event_type': 'slot_state_changed',
        'slot': 1,
        'state': 'not_in_holder',
        'in_holder': False,
        'sensor_level': 0,
        'sequence': 1,
        'ttl': ttl
    }
)
```

### Query Events

```python
from boto3.dynamodb.conditions import Key

table = dynamodb.Table('PillBuddy_Events')

# Get last 24 hours of events
start_time = int((time.time() - 86400) * 1000)
end_time = int(time.time() * 1000)

response = table.query(
    KeyConditionExpression=Key('device_id').eq('esp32_001') &
                          Key('timestamp').between(start_time, end_time),
    ScanIndexForward=False,  # Descending order (newest first)
    Limit=50
)

events = response['Items']
```

### Update Pill Count

```python
table = dynamodb.Table('PillBuddy_Prescriptions')

table.update_item(
    Key={
        'device_id': 'esp32_001',
        'slot': 1
    },
    UpdateExpression='SET pill_count = pill_count - :dec, updated_at = :now',
    ExpressionAttributeValues={
        ':dec': 1,
        ':now': int(time.time() * 1000)
    }
)
```
