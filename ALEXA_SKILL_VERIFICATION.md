# Alexa Skill Verification Checklist

## Current Status

✅ **Lambda Permission**: Correctly configured for skill ID `amzn1.ask.skill.7b43b770-5a10-48d0-bec3-c3b2e521a116`  
✅ **Lambda Function**: Working and responding correctly  
✅ **Device Check**: Removed - MQTT connections can be intermittent

---

## Quick Test

Test the skill without worrying about device status:

```bash
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-alexa-launch.json \
  --region us-east-1 \
  alexa-response.json && cat alexa-response.json | jq .
```

---

## Alexa Skill Setup Checklist

### 1. ✅ Lambda Configuration

**Function**: `PillBuddy_AlexaHandler`  
**ARN**: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`

**Trigger Permission**:

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

✅ **Status**: Configured correctly

---

### 2. Alexa Developer Console Configuration

Go to: https://developer.amazon.com/alexa/console/ask

#### A. Skill Information

- **Skill Name**: PillBuddy
- **Invocation Name**: `pill buddy` (two words required by Alexa)
- **Skill ID**: `amzn1.ask.skill.7b43b770-5a10-48d0-bec3-c3b2e521a116`

#### B. Interaction Model

**File**: `infrastructure/alexa/interactionModel.json`

**Custom Intents**:

1. `SetupSlotIntent` - Set up a prescription slot
2. `QueryStatusIntent` - Ask for status

**Custom Slot Types**:

1. `PrescriptionNameType` - Medication names
2. `HasRefillsType` - Yes/no for refills

**Sample Utterances**:

- "ask pillbuddy to set up slot one"
- "ask pillbuddy what's my status"

#### C. Endpoint Configuration

**Type**: AWS Lambda ARN  
**Default Region**: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`

**SSL Certificate**: My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority

---

### 3. Testing the Skill

#### Option A: Alexa Developer Console Test

1. Go to **Test** tab in Alexa Developer Console
2. Enable testing: "Development"
3. Type or say: "open pill buddy"

**Expected Response**:

> "Welcome to PillBuddy! Let's set up your pill bottles. I'll guide you through configuring each of the three slots. For the first slot, please tell me the prescription name, number of pills, and whether you have refills."

#### Option B: Test with Lambda Directly

```bash
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-alexa-launch.json \
  --region us-east-1 \
  alexa-response.json && cat alexa-response.json | jq .
```

---

## Device Online Check

**Note**: Device online checks have been removed from the Alexa Handler. MQTT connections can be intermittent, so users can set up prescriptions even if the ESP32 is temporarily offline.

The `last_seen` timestamp is still updated by the IoT Event Processor when events are received, but it's not used to block Alexa interactions.

---

## Common Issues & Solutions

### Issue 1: "I don't understand that command"

**Cause**: Intent not recognized or model not built

**Solution**:

1. Go to Alexa Developer Console
2. Click "Build Model" button
3. Wait for build to complete
4. Try again

### Issue 2: Lambda not being triggered

**Cause**: Permission not set or wrong skill ID

**Solution**:

```bash
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token amzn1.ask.skill.7b43b770-5a10-48d0-bec3-c3b2e521a116 \
  --region us-east-1
```

### Issue 3: "There was a problem with the requested skill's response"

**Cause**: Lambda error or timeout

**Solution**:

1. Check Lambda logs:

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow --region us-east-1
```

2. Look for errors in CloudWatch
3. Test Lambda directly to see error details

---

## Voice Commands to Test

Once device is online, try these:

### 1. Launch Skill

**Say**: "Alexa, open pill buddy"  
**Expected**: Welcome message asking which slot to configure

### 2. Set Up Slot

**Say**: "Alexa, ask pill buddy to set up slot one"  
**Expected**: "What's the prescription name?"  
**Say**: "Aspirin"  
**Expected**: "How many pills?"  
**Say**: "Thirty"  
**Expected**: "Does it have refills?"  
**Say**: "Yes"  
**Expected**: Confirmation and LED turn on command sent

### 3. Query Status

**Say**: "Alexa, ask pill buddy what's my status"  
**Expected**: Status of all configured slots with pill counts

### 4. Help

**Say**: "Alexa, ask pill buddy for help"  
**Expected**: Help message with available commands

---

## Verification Steps

Run these commands to verify everything:

### 1. Check Lambda Permission

```bash
aws lambda get-policy --function-name PillBuddy_AlexaHandler --region us-east-1 | jq -r '.Policy' | jq .
```

✅ Should show Alexa trigger with your skill ID

### 2. Check Device Status

```bash
aws dynamodb get-item \
  --table-name PillBuddy_Devices \
  --key '{"device_id":{"S":"pillbuddy-esp32-1"}}' \
  --region us-east-1 | jq -r '.Item.last_seen.N'
```

Compare timestamp to current time (should be < 5 minutes old)

### 3. Test Lambda

```bash
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-alexa-launch.json \
  --region us-east-1 \
  response.json && cat response.json | jq .
```

✅ Should return Alexa response (not error)

### 4. Check Lambda Logs

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --since 10m --region us-east-1
```

Look for any errors or issues

---

## Next Steps

1. **Make device online**: Publish an event from ESP32 or use test command
2. **Test in Alexa Console**: Go to Test tab and try "open pillbuddy"
3. **Check logs**: Monitor Lambda logs while testing
4. **Try voice commands**: Test the full flow with your Alexa device

---

## Files Reference

- Interaction Model: `infrastructure/alexa/interactionModel.json`
- Skill Manifest: `infrastructure/alexa/skill.json`
- Lambda Code: `infrastructure/lambda/alexa_handler/lambda_function.py`
- Test Events: `infrastructure/lambda/alexa_handler/test_events.json`
