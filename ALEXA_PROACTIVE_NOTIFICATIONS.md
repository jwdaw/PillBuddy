# Alexa Proactive Notifications - Congratulations Feature

## What's Implemented

Your IoT Event Processor Lambda now sends **congratulations messages** when a user takes a pill (removes bottle from holder).

### Current Behavior

When a bottle is removed:

1. Pill count is decremented
2. **Congratulations message is generated** (varies for engagement)
3. Message is logged to CloudWatch
4. Refill reminder sent if pill count < 5

### Sample Messages

The system rotates through these messages:

- "Great job! You took your Aspirin. Keep up the good work!"
- "Well done! Your Aspirin has been taken. You have 5 pills remaining."
- "Excellent! You're staying on track with your Aspirin."
- "Nice work! You took your Aspirin. Stay healthy!"

---

## Current Status: Logging Only

Right now, the congratulations messages are **logged to CloudWatch** but **not spoken by Alexa**.

You can see them in the logs:

```bash
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --since 5m --region us-east-1 | grep "Congratulations"
```

Output:

```
Congratulations: Great job! You took your Aspirin. Keep up the good work!
```

---

## To Make Alexa Actually Speak

To have Alexa proactively speak these messages, you need to implement **Alexa Proactive Events API**. This requires:

### 1. Enable Proactive Events Permission

In Alexa Developer Console:

1. Go to your skill
2. Click **"Build"** tab
3. Click **"Permissions"** in left sidebar
4. Enable: `alexa::devices:all:notifications:write`
5. Save and build model

### 2. Get User Consent

Users must grant permission for proactive notifications:

- In the Alexa app, users need to enable notifications for your skill
- This happens automatically when they enable the skill in development mode

### 3. Implement Proactive Events API

Update the `send_congratulations` function to actually call Alexa:

```python
import requests

def send_congratulations(device_id, prescription):
    """Send Alexa proactive notification"""
    try:
        prescription_name = prescription.get('prescription_name', 'medication')
        pill_count = int(prescription.get('pill_count', 0))

        messages = [
            f"Great job! You took your {prescription_name}. Keep up the good work!",
            f"Well done! Your {prescription_name} has been taken. You have {pill_count} pills remaining.",
            f"Excellent! You're staying on track with your {prescription_name}.",
            f"Nice work! You took your {prescription_name}. Stay healthy!",
        ]

        message = messages[pill_count % len(messages)]

        # Get access token (requires OAuth setup)
        access_token = get_alexa_access_token()

        # Send proactive event
        url = "https://api.amazonalexa.com/v1/proactiveEvents/stages/development"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "referenceId": f"{device_id}-{int(time.time())}",
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
                        "urgency": "NORMAL"
                    }
                }
            },
            "localizedAttributes": [
                {
                    "locale": "en-US",
                    "message": message
                }
            ],
            "relevantAudience": {
                "type": "Unicast",
                "payload": {
                    "user": device_id  # User ID from Alexa
                }
            }
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 202:
            print(f"Congratulations sent: {message}")
        else:
            print(f"Failed to send: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error sending congratulations: {str(e)}")
```

### 4. OAuth Setup for Access Token

You need to set up OAuth to get an access token:

1. Create a security profile in Amazon Developer Console
2. Get Client ID and Client Secret
3. Implement OAuth flow to get access token
4. Store token in environment variable or Secrets Manager

---

## Simpler Alternative: Alexa Announcements

For a hackathon, you could use **Alexa Announcements** instead (simpler but requires Alexa for Business):

```python
import boto3

alexa_client = boto3.client('alexaforbusiness')

def send_congratulations(device_id, prescription):
    """Send Alexa announcement"""
    try:
        prescription_name = prescription.get('prescription_name', 'medication')
        message = f"Great job! You took your {prescription_name}."

        # Send announcement to all devices in the room
        alexa_client.send_announcement(
            RoomFilters=[{'Key': 'RoomName', 'Values': ['Living Room']}],
            Content={'TextList': [{'Locale': 'en-US', 'Value': message}]}
        )

        print(f"Announcement sent: {message}")

    except Exception as e:
        print(f"Error sending announcement: {str(e)}")
```

---

## For Your Hackathon

Since implementing full Alexa Proactive Events is complex, I recommend:

### Option 1: Keep Current Implementation (Logging)

- Messages are logged and visible in CloudWatch
- You can demo by showing the logs
- Explain that in production, these would be spoken by Alexa

### Option 2: Use Alexa Routines (Manual Setup)

- Create an Alexa Routine triggered by a smart home device
- When pill is taken, trigger the routine
- Routine speaks the congratulations message

### Option 3: Polling Approach

- User asks: "Alexa, ask pill buddy if I took my pill"
- Alexa checks the last event timestamp
- If recent (< 5 minutes), congratulates them
- If not recent, reminds them to take their pill

---

## Testing Current Implementation

### Test 1: Remove Bottle (Take Pill)

Press button on ESP32 to remove bottle.

Check logs:

```bash
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --since 1m --region us-east-1 | grep "Congratulations"
```

You should see:

```
Congratulations: Great job! You took your Aspirin. Keep up the good work!
```

### Test 2: Multiple Removals

Remove and return bottle multiple times. Each removal generates a different congratulations message (rotates through 4 messages).

### Test 3: Check DynamoDB

```bash
aws dynamodb get-item \
  --table-name PillBuddy_Prescriptions \
  --key '{"device_id":{"S":"pillbuddy-esp32-1"},"slot":{"N":"2"}}' \
  --region us-east-1 | jq '.Item.pill_count.N'
```

Pill count should decrement with each removal.

---

## Message Rotation Logic

Messages rotate based on pill count:

- Pill count 0: Message 0 ("Great job...")
- Pill count 1: Message 1 ("Well done...")
- Pill count 2: Message 2 ("Excellent...")
- Pill count 3: Message 3 ("Nice work...")
- Pill count 4: Message 0 (cycles back)

This provides variety and keeps users engaged.

---

## Future Enhancements

1. **Time-based messages**: "Good morning! Time for your Aspirin."
2. **Streak tracking**: "You've taken your pills 7 days in a row!"
3. **Personalization**: Use user's name in messages
4. **Medication-specific**: Different messages for different medications
5. **Reminder escalation**: Gentle → Firm → Urgent reminders

---

## Summary

✅ **Implemented**: Congratulations messages generated on pill removal  
✅ **Working**: Messages logged to CloudWatch  
✅ **Tested**: Verified with ESP32 button presses  
⏳ **Future**: Alexa Proactive Events API for actual speech

For your hackathon demo, you can:

1. Show the logs with congratulations messages
2. Explain the feature is implemented and working
3. Demonstrate that it triggers on every pill removal
4. Mention that production would use Alexa Proactive Events API

The hard part (detecting pill removal and generating appropriate messages) is done!
