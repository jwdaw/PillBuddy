# Alexa Handler Flow - High-Level Overview

This document explains how Alexa voice commands interact with your PillBuddy backend system.

---

## The Big Picture

```
User Voice → Alexa Device → Alexa Skills Kit → Lambda (Alexa Handler) → DynamoDB + IoT Core
                                                                              ↓
                                                                    ESP32 receives commands
```

---

## How Alexa Connects to Your System

### 1. Alexa Skill Configuration

Your Alexa skill is configured in the Amazon Developer Console with:

- **Skill ID**: `amzn1.ask.skill.7b43b770-5a10-48d0-bec3-c3b2e521a116`
- **Invocation Name**: "pill buddy" (two words)
- **Endpoint**: Your Lambda function ARN

When a user says "Alexa, open pill buddy", Amazon's Alexa service:

1. Recognizes the invocation name
2. Looks up your skill ID
3. Sends a request to your Lambda function

### 2. Lambda Permission

Your Lambda has a special permission that allows Alexa to invoke it:

```json
{
  "Principal": "alexa-appkit.amazon.com",
  "Condition": {
    "StringEquals": {
      "lambda:EventSourceToken": "amzn1.ask.skill.7b43b770-5a10-48d0-bec3-c3b2e521a116"
    }
  }
}
```

This ensures only YOUR Alexa skill can trigger this Lambda.

---

## Request Flow: User Says Something

### Step 1: User Speaks to Alexa

**User says**: "Alexa, open pill buddy"

### Step 2: Alexa Processes Speech

Alexa's cloud service:

1. Converts speech to text
2. Matches "pill buddy" to your skill
3. Determines this is a **LaunchRequest** (opening the skill)
4. Creates a JSON request

### Step 3: Alexa Sends JSON to Lambda

Alexa sends a JSON payload to your Lambda:

```json
{
  "version": "1.0",
  "session": {
    "new": true,
    "sessionId": "amzn1.echo-api.session...",
    "user": {
      "userId": "amzn1.ask.account..."
    }
  },
  "request": {
    "type": "LaunchRequest",
    "requestId": "amzn1.echo-api.request...",
    "timestamp": "2024-02-28T12:00:00Z"
  }
}
```

### Step 4: Lambda Processes Request

Your `lambda_handler` function:

```python
def lambda_handler(event, context):
    request_type = event['request']['type']  # "LaunchRequest"
    device_id = event.get('session', {}).get('user', {}).get('userId', 'esp32_001')

    if request_type == 'LaunchRequest':
        return handle_launch_request(device_id, event)
```

### Step 5: Lambda Starts Setup Flow

The `handle_launch_request` function:

1. **Checks if device exists in DynamoDB** (Devices table)
2. **Creates device record if needed**
3. **Starts setup flow immediately** (no online check - MQTT can be intermittent)

```python
# Start setup flow (no online check - MQTT can be intermittent)
session_attributes = {
    'device_id': device_id,
    'setup_state': {
        'slots_configured': 0,
        'current_slot': 1
    }
}

return "Welcome! Let's set up your bottles"
```

### Step 6: Lambda Returns Response to Alexa

Lambda returns a JSON response:

```json
{
  "version": "1.0",
  "sessionAttributes": {
    "device_id": "pillbuddy-esp32-1",
    "setup_state": {
      "slots_configured": 0,
      "current_slot": 1
    }
  },
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "Welcome to PillBuddy! Let's set up your pill bottles..."
    },
    "shouldEndSession": false
  }
}
```

### Step 7: Alexa Speaks to User

Alexa converts the text to speech and says:

> "Welcome to PillBuddy! Let's set up your pill bottles..."

---

## Complete Workflow: Setting Up a Prescription

### Conversation Flow

```
User: "Alexa, open pill buddy"
  ↓
Alexa → Lambda (LaunchRequest)
  ↓
Lambda checks if device exists in DynamoDB
  ↓
Lambda creates device record if needed
  ↓
Alexa ← Lambda (Welcome message)
  ↓
Alexa: "Welcome! Let's set up your bottles. Tell me the prescription name..."

User: "Aspirin with 30 pills and yes for refills"
  ↓
Alexa → Lambda (SetupSlotIntent with slots filled)
  ↓
Lambda writes prescription to DynamoDB
  ↓
Lambda publishes LED command to IoT Core
  ↓
ESP32 ← IoT Core (turn_on LED for slot 1)
  ↓
Alexa ← Lambda (Confirmation message)
  ↓
Alexa: "Great! I've saved Aspirin with 30 pills. The LED is on..."
```

### Detailed Step-by-Step

#### 1. User Provides Prescription Details

**User says**: "Aspirin with 30 pills and yes for refills"

#### 2. Alexa Parses Intent and Slots

Alexa sends:

```json
{
  "request": {
    "type": "IntentRequest",
    "intent": {
      "name": "SetupSlotIntent",
      "slots": {
        "prescriptionName": {
          "name": "prescriptionName",
          "value": "Aspirin"
        },
        "pillCount": {
          "name": "pillCount",
          "value": "30"
        },
        "hasRefills": {
          "name": "hasRefills",
          "value": "yes"
        }
      }
    }
  }
}
```

#### 3. Lambda Extracts Slot Values

```python
prescription_name = slots.get('prescriptionName', {}).get('value')  # "Aspirin"
pill_count = int(slots.get('pillCount', {}).get('value'))           # 30
has_refills = slots.get('hasRefills', {}).get('value') == 'yes'     # True
```

#### 4. Lambda Writes to DynamoDB

```python
prescription_item = {
    'device_id': 'pillbuddy-esp32-1',
    'slot': 1,
    'prescription_name': 'Aspirin',
    'pill_count': 30,
    'initial_count': 30,
    'has_refills': True,
    'created_at': 1709121600000,
    'updated_at': 1709121600000,
    'removal_timestamp': None
}

prescriptions_table.put_item(Item=prescription_item)
```

**DynamoDB Prescriptions Table Now Contains**:

| device_id         | slot | prescription_name | pill_count | has_refills |
| ----------------- | ---- | ----------------- | ---------- | ----------- |
| pillbuddy-esp32-1 | 1    | Aspirin           | 30         | true        |

#### 5. Lambda Publishes LED Command to IoT Core

```python
topic = "pillbuddy/cmd/pillbuddy-esp32-1"
payload = {
    'action': 'turn_on',
    'slot': 1
}

iot_client.publish(topic=topic, qos=1, payload=json.dumps(payload))
```

**IoT Core forwards this to ESP32**:

- ESP32 is subscribed to `pillbuddy/cmd/pillbuddy-esp32-1`
- ESP32 receives: `{"action": "turn_on", "slot": 1}`
- ESP32 turns on LED for slot 1

#### 6. Lambda Returns Success Response

```json
{
  "response": {
    "outputSpeech": {
      "text": "Great! I've saved Aspirin with refills with 30 pills for slot 1. The LED is on. Please place the bottle in slot 1. Would you like to set up slot 2?"
    },
    "shouldEndSession": false
  },
  "sessionAttributes": {
    "setup_state": {
      "slots_configured": 1,
      "current_slot": 2
    }
  }
}
```

#### 7. Alexa Speaks Confirmation

Alexa says the confirmation message to the user.

---

## Query Status Flow

### User Asks for Status

**User says**: "Alexa, ask pill buddy what's my status"

### Lambda Queries DynamoDB

```python
# Query all prescriptions for device
response = prescriptions_table.query(
    KeyConditionExpression='device_id = :device_id',
    ExpressionAttributeValues={
        ':device_id': 'pillbuddy-esp32-1'
    }
)

prescriptions = response.get('Items', [])
```

**DynamoDB Returns**:

```json
[
  {
    "device_id": "pillbuddy-esp32-1",
    "slot": 1,
    "prescription_name": "Aspirin",
    "pill_count": 28
  },
  {
    "device_id": "pillbuddy-esp32-1",
    "slot": 2,
    "prescription_name": "Vitamin D",
    "pill_count": 15
  }
]
```

### Lambda Formats Response

```python
status_parts = [
    "Slot 1 has Aspirin with 28 pills remaining",
    "Slot 2 has Vitamin D with 15 pills remaining"
]

speech_text = "Slot 1 has Aspirin with 28 pills remaining, and Slot 2 has Vitamin D with 15 pills remaining."
```

### Alexa Speaks Status

Alexa says the formatted status to the user.

---

## How Alexa and IoT Event Processor Work Together

### They Don't Directly Communicate!

**Important**: The Alexa Handler and IoT Event Processor are **separate Lambda functions** that don't call each other. They communicate through **DynamoDB** as shared state.

### Shared State via DynamoDB

```
Alexa Handler                    DynamoDB                    IoT Event Processor
     |                              |                              |
     |------ Write Prescription --->|                              |
     |                              |                              |
     |------ Publish LED cmd ------>|---> IoT Core ---> ESP32      |
     |                              |                              |
     |                              |<---- ESP32 publishes event --|
     |                              |                              |
     |                              |<---- Update pill count ------|
     |                              |                              |
     |------ Query Status --------->|                              |
     |<----- Return updated data ---|                              |
```

### Example: Complete Bottle Removal Flow

1. **Alexa Handler** writes prescription to DynamoDB (pill_count = 30)
2. **Alexa Handler** publishes LED command to IoT Core
3. User removes bottle from ESP32
4. **ESP32** publishes event to IoT Core
5. **IoT Event Processor** receives event (triggered by IoT Rule)
6. **IoT Event Processor** decrements pill_count in DynamoDB (30 → 29)
7. User asks Alexa for status
8. **Alexa Handler** queries DynamoDB
9. **Alexa Handler** sees pill_count = 29
10. Alexa speaks: "Slot 1 has Aspirin with 29 pills remaining"

---

## Session Management

### What is a Session?

A session is a conversation between the user and Alexa. It starts when the user invokes the skill and ends when:

- User says "stop" or "cancel"
- Lambda sets `shouldEndSession: true`
- User doesn't respond for ~8 seconds

### Session Attributes

Lambda can store data in `sessionAttributes` to maintain state across turns:

```json
{
  "sessionAttributes": {
    "device_id": "pillbuddy-esp32-1",
    "setup_state": {
      "slots_configured": 1,
      "current_slot": 2
    }
  }
}
```

This allows multi-turn conversations:

- Turn 1: Set up slot 1
- Turn 2: Set up slot 2
- Turn 3: Set up slot 3

Each turn, Lambda receives the previous `sessionAttributes` and can update them.

---

## Device ID Mapping

### How Lambda Knows Which ESP32

In your current implementation:

```python
device_id = event.get('session', {}).get('user', {}).get('userId', 'esp32_001')
```

**For hackathon**: This defaults to 'esp32_001' or uses Alexa's user ID.

**For production**: You would implement **account linking**:

1. User logs into your app/website
2. User links their Alexa account
3. User registers their ESP32 device ID
4. Lambda looks up device_id based on Alexa user ID

---

## Error Handling

### DynamoDB Write Failure

If prescription can't be saved:

```python
try:
    prescriptions_table.put_item(Item=prescription_item)
except Exception as e:
    return "Sorry, I couldn't save that prescription. Please try again."
```

### IoT Publish Failure

If LED command fails, Lambda continues anyway (non-critical):

```python
try:
    publish_iot_command(device_id, 'turn_on', current_slot)
except Exception as e:
    print(f"IoT publish error: {str(e)}")
    # Continue - LED is optional
```

**Note**: Device online checks have been removed because MQTT connections can be intermittent. Users can set up prescriptions even if the ESP32 is temporarily offline.

---

## Data Flow Summary

### Alexa → Lambda → DynamoDB

```
User voice command
  ↓
Alexa Skills Kit (speech-to-text, intent recognition)
  ↓
Lambda (PillBuddy_AlexaHandler)
  ↓
DynamoDB (read/write Devices, Prescriptions tables)
  ↓
Lambda (format response)
  ↓
Alexa Skills Kit (text-to-speech)
  ↓
User hears response
```

### Alexa → Lambda → IoT Core → ESP32

```
User voice command
  ↓
Alexa Skills Kit
  ↓
Lambda (PillBuddy_AlexaHandler)
  ↓
IoT Core (publish to pillbuddy/cmd/{device_id})
  ↓
ESP32 (subscribed to topic, receives command)
  ↓
ESP32 turns on/off LED
```

### ESP32 → IoT Core → Lambda → DynamoDB

```
User removes bottle
  ↓
ESP32 (publishes to pillbuddy/events/{device_id})
  ↓
IoT Core (IoT Rule triggers Lambda)
  ↓
Lambda (PillBuddy_IoTEventProcessor)
  ↓
DynamoDB (update pill count, device state)
```

### Alexa Queries Updated Data

```
User asks for status
  ↓
Alexa Skills Kit
  ↓
Lambda (PillBuddy_AlexaHandler)
  ↓
DynamoDB (query Prescriptions table)
  ↓
Lambda (sees updated pill count from IoT Event Processor)
  ↓
Alexa speaks current status
```

---

## Key Takeaways

1. **Alexa doesn't talk directly to ESP32** - it goes through Lambda and IoT Core
2. **Lambda functions don't call each other** - they share state via DynamoDB
3. **Alexa Handler writes prescriptions** - IoT Event Processor updates them
4. **Device online check** uses `last_seen` timestamp updated by IoT events
5. **Session attributes** maintain conversation state across multiple turns
6. **IoT Core** is the bridge between Lambda and ESP32

---

## Testing the Flow

### Test Alexa Handler Directly

```bash
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --payload file://test-alexa-launch.json \
  response.json
```

### Test Complete Flow

1. Say "Alexa, open pill buddy" (triggers LaunchRequest)
2. Lambda checks device online status
3. Say prescription details (triggers SetupSlotIntent)
4. Lambda writes to DynamoDB and publishes LED command
5. ESP32 receives LED command
6. Remove bottle from ESP32
7. IoT Event Processor updates pill count
8. Say "Alexa, ask pill buddy what's my status"
9. Lambda queries DynamoDB and sees updated count

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Alexa Device    │
                    │  (Echo, etc.)    │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ALEXA SKILLS KIT                            │
│  - Speech-to-text                                                │
│  - Intent recognition                                            │
│  - Text-to-speech                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Lambda:         │
                    │  AlexaHandler    │
                    └──────────────────┘
                         │         │
                         │         └──────────────┐
                         ▼                        ▼
              ┌──────────────────┐    ┌──────────────────┐
              │   DynamoDB       │    │   IoT Core       │
              │   - Devices      │    │   (MQTT)         │
              │   - Prescriptions│    └──────────────────┘
              └──────────────────┘              │
                         ▲                      ▼
                         │            ┌──────────────────┐
                         │            │   ESP32 Device   │
                         │            │   - Subscribes   │
                         │            │   - Publishes    │
                         │            └──────────────────┘
                         │                      │
                         │                      ▼
                         │            ┌──────────────────┐
                         │            │   IoT Rule       │
                         │            │   (forwards)     │
                         │            └──────────────────┘
                         │                      │
                         │                      ▼
                         │            ┌──────────────────┐
                         └────────────│  Lambda:         │
                                      │  IoTEventProc    │
                                      └──────────────────┘
```

---

## Related Documents

- **IOT_EVENT_PROCESSOR_FLOW.md** - How ESP32 events are processed
- **SYSTEM_OVERVIEW.md** - High-level system architecture
- **ALEXA_SKILL_VERIFICATION.md** - Testing and troubleshooting Alexa
- **infrastructure/lambda/alexa_handler/lambda_function.py** - Full Lambda code
