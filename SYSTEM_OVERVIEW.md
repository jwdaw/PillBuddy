# PillBuddy System Overview - The Simple Truth

## Is This Overengineered?

**Short answer**: For a hackathon MVP, yes, somewhat. But it's designed to be production-ready.

**What you actually NEED for a hackathon**:

- 1 DynamoDB table (could store everything)
- 2 Lambda functions (Alexa handler + IoT processor)
- Basic IoT Core setup

**What we built**:

- 3 DynamoDB tables (normalized data)
- 4 Lambda functions (separation of concerns)
- Full event logging with TTL
- Timeout checking system
- Optional REST API

The extra complexity gives you:

- Better data organization
- Audit trail of all events
- Automatic cleanup (TTL)
- Scalability if you continue the project

---

## The Core Flow (What Actually Matters)

```
┌─────────────┐
│   ESP32     │  Publishes: {"event_type":"slot_state_changed","slot":2,"in_holder":false}
│  (3 slots)  │  Topic: pillbuddy/events/pillbuddy-esp32-1
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS IoT Core                                               │
│  - Receives MQTT messages                                   │
│  - IoT Rule adds: device_id, timestamp, sequence, etc.     │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Lambda: IoT Event Processor                                │
│  - Logs event to Events table                               │
│  - Updates device last_seen                                 │
│  - Decrements pill count when bottle removed                │
│  - Publishes LED commands back to ESP32                     │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  DynamoDB Tables                                            │
│  - Devices: Device status, last seen                        │
│  - Prescriptions: Pill counts, prescription info            │
│  - Events: History log (auto-deletes after 30 days)        │
└─────────────────────────────────────────────────────────────┘

       ▲
       │
┌──────┴──────┐
│    Alexa    │  "Alexa, ask PillBuddy to set up slot 1"
│   (Voice)   │  Lambda: Alexa Handler responds
└─────────────┘
```

---

## The 3 DynamoDB Tables Explained

### 1. **Devices Table** (ESSENTIAL)

**What it stores**: Device info, online status, slot states  
**Why you need it**:

- Alexa needs to know if device is online
- Track which slots have bottles in them
- Store last_seen timestamp

**Could you skip it?** No - Alexa needs this to respond intelligently

---

### 2. **Prescriptions Table** (ESSENTIAL)

**What it stores**: Prescription name, pill count, refill status per slot  
**Why you need it**:

- Track how many pills are left
- Know when to remind about refills
- Store prescription details Alexa told you

**Could you skip it?** No - this is your core data

---

### 3. **Events Table** (NICE TO HAVE)

**What it stores**: Every bottle removal/return event with timestamp  
**Why you need it**:

- Audit trail (when did user take pills?)
- Debugging (see what ESP32 is sending)
- Could build analytics later

**Could you skip it?** YES - for a hackathon MVP, you could skip this entirely. The system would still work, you just wouldn't have history.

**Verdict**: Events table is the "overengineered" part. But it's useful for debugging and only costs ~$0.50/month.

---

## The 4 Lambda Functions Explained

### 1. **Alexa Handler** (ESSENTIAL)

**What it does**:

- Responds to Alexa voice commands
- "Set up slot 1 with Aspirin, 30 pills, has refills"
- "What's my status?" → reads pill counts

**Triggers**: Alexa Skill invocations  
**Cost**: Only runs when you talk to Alexa  
**Could you skip it?** No - this is how Alexa works

---

### 2. **IoT Event Processor** (ESSENTIAL)

**What it does**:

- Receives events from ESP32 (via IoT Rule)
- Decrements pill count when bottle removed
- Clears removal timestamp when bottle returned
- Sends LED commands back to ESP32

**Triggers**: Every time ESP32 publishes an event  
**Cost**: Runs constantly as ESP32 sends events  
**Could you skip it?** No - this is your core business logic

---

### 3. **Timeout Checker** (NICE TO HAVE)

**What it does**:

- Runs every 5 minutes
- Checks if any bottles have been out for >10 minutes
- Sends Alexa notification: "Please return the bottle"

**Triggers**: EventBridge schedule (every 5 minutes)  
**Cost**: ~8,640 invocations/month = $0.01  
**Could you skip it?** YES - for a hackathon, you could skip this. It's a nice feature but not essential.

---

### 4. **API Handler** (OPTIONAL)

**What it does**:

- REST API to query device status, prescriptions, events
- GET /devices/{id}/status
- GET /devices/{id}/prescriptions

**Triggers**: HTTP requests (if you set up API Gateway)  
**Cost**: Only if you use it  
**Could you skip it?** YES - we marked this as optional in the spec. You don't need it unless you want a web dashboard.

---

## What You Actually Use (Simplified)

### For Your Hackathon Demo:

**MUST HAVE** (2 Lambdas, 2 Tables):

1. Alexa Handler Lambda
2. IoT Event Processor Lambda
3. Devices Table
4. Prescriptions Table

**NICE TO HAVE** (1 Lambda, 1 Table): 5. Events Table (for debugging/history) 6. Timeout Checker Lambda (for "return bottle" reminders)

**SKIP FOR HACKATHON**: 7. API Handler Lambda (unless you want a web UI)

---

## How ESP32 Connects (The Simple Version)

### What Your ESP32 Needs to Do:

**1. Connect to AWS IoT Core**

- Endpoint: `agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com`
- Use certificates (already set up in IoT Core)
- Client ID: `pillbuddy-esp32-1`

**2. Publish Events (When Bottle Removed/Returned)**

```cpp
// Topic: pillbuddy/events/pillbuddy-esp32-1
// Payload (JSON):
{
  "event_type": "slot_state_changed",
  "slot": 1,              // or 2, or 3
  "in_holder": false      // false = removed, true = returned
}
```

**3. Subscribe to Commands (For LED Control)**

```cpp
// Topic: pillbuddy/cmd/pillbuddy-esp32-1
// Receives (JSON):
{
  "action": "turn_on",    // or "turn_off"
  "slot": 1               // which LED to control
}
```

That's it! Your ESP32 just publishes 3 fields, AWS does the rest.

---

## Cost Breakdown (Reality Check)

For 1 device, moderate usage:

| Component                               | Monthly Cost     |
| --------------------------------------- | ---------------- |
| DynamoDB (3 tables)                     | $2.28            |
| Lambda (4 functions, ~100K invocations) | $0.20            |
| IoT Core (~100K messages)               | $0.13            |
| EventBridge (timeout checker)           | $0.01            |
| CloudWatch Logs                         | $0.50            |
| **TOTAL**                               | **~$3.12/month** |

For a hackathon weekend: **~$0.25**

---

## Simplification Options

### If You Want to Simplify:

**Option 1: Minimal Viable (Keep 2 Lambdas, 2 Tables)**

- Delete Events table
- Delete Timeout Checker Lambda
- Delete API Handler Lambda
- **Saves**: ~$0.50/month, reduces complexity
- **Loses**: Event history, timeout reminders, REST API

**Option 2: Ultra-Minimal (Merge Tables)**

- Combine Devices + Prescriptions into 1 table
- Keep 2 Lambdas
- **Saves**: ~$0.76/month
- **Loses**: Clean data separation, harder to query

**My Recommendation**: Keep what we have. It's only $3/month and gives you a complete system. The "overengineering" is minimal and makes debugging easier.

---

## The Bottom Line

**Is it overengineered?** Slightly, but not egregiously.

**What's essential?**

- 2 Lambda functions (Alexa + IoT processor)
- 2 DynamoDB tables (Devices + Prescriptions)
- IoT Core setup

**What's nice-to-have?**

- Events table (debugging/history)
- Timeout Checker (reminders)

**What's optional?**

- API Handler (web dashboard)

**Total cost**: $3/month for full system, $2.50/month for minimal

For a hackathon that might turn into a real product, this is a solid foundation. You're not wasting resources, and everything serves a purpose.

---

## Quick Reference: What Talks to What

```
ESP32 → IoT Core → IoT Event Processor Lambda → DynamoDB
                                              ↓
                                         IoT Core → ESP32 (LED commands)

Alexa → Alexa Handler Lambda → DynamoDB
                             ↓
                        IoT Core → ESP32 (LED commands)

EventBridge (every 5 min) → Timeout Checker Lambda → DynamoDB
                                                   ↓
                                              Alexa (notifications)
```

Simple, right? The complexity is in the details, but the flow is straightforward.
