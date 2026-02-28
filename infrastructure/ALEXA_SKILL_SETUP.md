# Alexa Skill Setup Guide for PillBuddy

This document provides complete instructions for creating and configuring the PillBuddy Alexa skill.

## Overview

The PillBuddy Alexa skill enables voice-controlled setup and monitoring of pill bottles. Users can configure prescriptions, check pill counts, and receive refill reminders through natural voice interactions.

## Prerequisites

1. [Amazon Developer Account](https://developer.amazon.com/) (free)
2. AWS account with Lambda function deployed (PillBuddy_AlexaHandler)
3. Lambda function ARN ready
4. Basic understanding of Alexa Skills Kit

## Quick Start

Choose one of these methods:

1. **[ASK CLI Method](#method-1-ask-cli-recommended)** - Fastest, uses provided configuration files
2. **[Developer Console Method](#method-2-developer-console)** - Visual interface, step-by-step
3. **[Manual JSON Method](#method-3-manual-json-upload)** - For advanced users

---

## Method 1: ASK CLI (Recommended)

### Step 1: Install ASK CLI

```bash
npm install -g ask-cli

# Configure ASK CLI with your Amazon Developer account
ask configure
```

Follow the prompts to link your Amazon Developer account and AWS account.

### Step 2: Prepare Skill Configuration

The skill configuration files are provided in `infrastructure/alexa/`:

- `skill.json` - Skill manifest
- `interactionModel.json` - Interaction model with intents and utterances

### Step 3: Update Lambda ARN

Edit `infrastructure/alexa/skill.json` and replace `ACCOUNT_ID` with your AWS account ID:

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function \
  --function-name PillBuddy_AlexaHandler \
  --query 'Configuration.FunctionArn' \
  --output text)

echo "Lambda ARN: $LAMBDA_ARN"

# Update skill.json
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" infrastructure/alexa/skill.json
```

### Step 4: Create Skill Package

Create the skill package structure:

```bash
cd infrastructure/alexa

# Create skill package directory
mkdir -p skill-package/interactionModels/custom

# Copy files
cp skill.json skill-package/
cp interactionModel.json skill-package/interactionModels/custom/en-US.json
```

### Step 5: Deploy Skill

```bash
# Create new skill
ask deploy

# Note the Skill ID from the output
```

### Step 6: Add Lambda Trigger

```bash
# Get Skill ID from previous step or from ask CLI
SKILL_ID=$(ask api get-skill-status -s YOUR_SKILL_ID --query 'skillId' -o text)

# Add Alexa trigger to Lambda
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token $SKILL_ID
```

### Step 7: Test Skill

```bash
# Enable skill for testing
ask dialog --locale en-US

# Try these commands:
# > open pillbuddy
# > the prescription is aspirin with 30 pills
# > what's my status
```

---

## Method 2: Developer Console

### Step 1: Create Skill

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click "Create Skill"
3. Configure:
   - **Skill name**: PillBuddy
   - **Primary locale**: English (US)
   - **Choose a model**: Custom
   - **Choose a method to host**: Provision your own
4. Click "Create skill"
5. Choose "Start from Scratch" template
6. Click "Continue with template"

### Step 2: Configure Invocation

1. In the left sidebar, click "Invocations" → "Skill Invocation Name"
2. Set invocation name: `pillbuddy`
3. Click "Save Model"

### Step 3: Create SetupSlotIntent

1. Click "Interaction Model" → "Intents" in left sidebar
2. Click "Add Intent" → "Create custom intent"
3. Intent name: `SetupSlotIntent`
4. Click "Create custom intent"

#### Add Slots

Click "Add" under Intent Slots and add these three slots:

**Slot 1: prescriptionName**

- Slot name: `prescriptionName`
- Slot type: `AMAZON.MedicationName`
- This slot is required: ✓ (checked)
- Alexa speech prompts: "What's the name of the prescription?"

**Slot 2: pillCount**

- Slot name: `pillCount`
- Slot type: `AMAZON.NUMBER`
- This slot is required: ✓ (checked)
- Alexa speech prompts: "How many pills are in the bottle?"
- Add validation rule:
  - Rule type: "is greater than"
  - Value: 0
  - Prompt: "The pill count must be greater than zero. How many pills are in the bottle?"

**Slot 3: hasRefills**

- Slot name: `hasRefills`
- Slot type: `AMAZON.YesNo`
- This slot is required: ✓ (checked)
- Alexa speech prompts: "Does this prescription have refills available?"

#### Add Sample Utterances

Add these sample utterances:

```
The prescription is {prescriptionName} with {pillCount} pills
{prescriptionName} has {pillCount} pills and {hasRefills} refills
Set up {prescriptionName}
{prescriptionName} with {pillCount} pills
I have {prescriptionName}
{prescriptionName} {pillCount} pills {hasRefills} refills
Add {prescriptionName}
Configure {prescriptionName}
My prescription is {prescriptionName}
It's {prescriptionName} with {pillCount} pills
{prescriptionName} bottle has {pillCount} pills
```

5. Click "Save Model"

### Step 4: Create QueryStatusIntent

1. Click "Add Intent" → "Create custom intent"
2. Intent name: `QueryStatusIntent`
3. Click "Create custom intent"

#### Add Sample Utterances

```
What's my status
How many pills do I have
Check my bottles
What's in my PillBuddy
Tell me my pill counts
Status
Check status
What pills do I have
Show my medications
List my prescriptions
What's my pill count
How many pills are left
Check my medication
What bottles do I have
```

4. Click "Save Model"

### Step 5: Configure Built-in Intents

The following intents are already included by default:

- `AMAZON.HelpIntent`
- `AMAZON.StopIntent`
- `AMAZON.CancelIntent`
- `AMAZON.NavigateHomeIntent`

No additional configuration needed for these.

### Step 6: Build Model

1. Click "Build Model" button at the top
2. Wait for build to complete (30-60 seconds)
3. Verify "Build Successful" message

### Step 7: Configure Endpoint

1. Click "Endpoint" in the left sidebar
2. Select "AWS Lambda ARN"
3. **Default Region**: Paste your Lambda ARN
   ```bash
   # Get Lambda ARN
   aws lambda get-function \
     --function-name PillBuddy_AlexaHandler \
     --query 'Configuration.FunctionArn' \
     --output text
   ```
4. Copy the "Your Skill ID" at the top (you'll need this next)
5. Click "Save Endpoints"

### Step 8: Add Lambda Trigger

```bash
# Use the Skill ID from Step 7
SKILL_ID="amzn1.ask.skill.xxxxx"

aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token $SKILL_ID
```

### Step 9: Enable Proactive Notifications

1. Click "Permissions" in the left sidebar
2. Enable "Alexa::Devices::All::Notifications::Write"
3. Click "Save Permissions"

### Step 10: Test Skill

1. Click "Test" tab at the top
2. Enable testing: Select "Development" from dropdown
3. Test with voice or text:

**Test Conversation 1: Launch**

```
You: Alexa, open pillbuddy
Alexa: Welcome to PillBuddy! Let's set up your pill bottles...
```

**Test Conversation 2: Setup**

```
You: The prescription is Aspirin with 30 pills
Alexa: What's the name of the prescription?
You: Aspirin
Alexa: How many pills are in the bottle?
You: 30
Alexa: Does this prescription have refills available?
You: Yes
Alexa: Great! I've saved Aspirin...
```

**Test Conversation 3: Status**

```
You: Alexa, ask pillbuddy what's my status
Alexa: Slot 1 has Aspirin with 30 pills remaining...
```

---

## Method 3: Manual JSON Upload

### Step 1: Prepare JSON Files

The configuration files are in `infrastructure/alexa/`:

1. **skill.json** - Skill manifest
2. **interactionModel.json** - Interaction model

Update `skill.json` with your Lambda ARN:

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" infrastructure/alexa/skill.json
```

### Step 2: Create Skill via API

```bash
# Install jq if not already installed
# sudo apt-get install jq  # Ubuntu/Debian
# brew install jq          # macOS

# Create skill
ask api create-skill \
  --manifest file://infrastructure/alexa/skill.json \
  --locale en-US

# Get Skill ID from response
SKILL_ID="amzn1.ask.skill.xxxxx"
```

### Step 3: Upload Interaction Model

```bash
ask api update-model \
  --skill-id $SKILL_ID \
  --locale en-US \
  --interaction-model file://infrastructure/alexa/interactionModel.json
```

### Step 4: Build Model

```bash
ask api build-model \
  --skill-id $SKILL_ID \
  --locale en-US
```

### Step 5: Add Lambda Trigger

```bash
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token $SKILL_ID
```

---

## Testing the Skill

### Test in Developer Console

1. Go to "Test" tab
2. Enable testing: "Development"
3. Use the simulator to test voice interactions

### Test with Physical Alexa Device

1. Ensure your Alexa device is registered to the same Amazon account as your developer account
2. Say: "Alexa, open pillbuddy"
3. The skill should respond (it's automatically available on your devices in development mode)

### Test with Lambda Console

Create a test event in Lambda console:

```json
{
  "version": "1.0",
  "session": {
    "new": true,
    "sessionId": "amzn1.echo-api.session.test",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "user": {
      "userId": "esp32_001"
    }
  },
  "request": {
    "type": "LaunchRequest",
    "requestId": "amzn1.echo-api.request.test",
    "timestamp": "2024-01-01T00:00:00Z",
    "locale": "en-US"
  }
}
```

### Sample Test Conversations

**Conversation 1: Full Setup Flow**

```
User: Alexa, open pillbuddy
Alexa: Welcome to PillBuddy! Let's set up your pill bottles. What's the name of the first prescription?

User: Aspirin
Alexa: How many pills are in the bottle?

User: 30
Alexa: Does this prescription have refills available?

User: Yes
Alexa: Great! I've saved Aspirin with 30 pills. The LED is on. Please place the bottle in slot 1. Would you like to set up another bottle?

User: Yes
Alexa: What's the name of the prescription?

User: Vitamin D
Alexa: How many pills are in the bottle?

User: 60
Alexa: Does this prescription have refills available?

User: No
Alexa: Great! I've saved Vitamin D with 60 pills. The LED is on. Please place the bottle in slot 2. Would you like to set up another bottle?

User: No
Alexa: Okay, your PillBuddy is ready to use!
```

**Conversation 2: Quick Setup**

```
User: Alexa, tell pillbuddy the prescription is Ibuprofen with 20 pills
Alexa: Does this prescription have refills available?

User: Yes
Alexa: Great! I've saved Ibuprofen with 20 pills...
```

**Conversation 3: Status Check**

```
User: Alexa, ask pillbuddy what's my status
Alexa: Here's your PillBuddy status. Slot 1 has Aspirin with 28 pills remaining. Slot 2 has Vitamin D with 58 pills remaining. Slot 3 is empty.
```

---

## Skill Configuration Reference

### Invocation Name

**Name**: `pillbuddy`

**Usage**:

- "Alexa, open pillbuddy"
- "Alexa, ask pillbuddy [question]"
- "Alexa, tell pillbuddy [command]"

### Intents

#### 1. SetupSlotIntent

**Purpose**: Configure a prescription for a specific slot

**Slots**:

- `prescriptionName` (AMAZON.MedicationName) - Name of the medication
- `pillCount` (AMAZON.NUMBER) - Number of pills in bottle
- `hasRefills` (AMAZON.YesNo) - Whether refills are available

**Sample Utterances**:

- "The prescription is {prescriptionName} with {pillCount} pills"
- "{prescriptionName} has {pillCount} pills and {hasRefills} refills"
- "Set up {prescriptionName}"

**Dialog Management**: Multi-turn conversation with slot elicitation

#### 2. QueryStatusIntent

**Purpose**: Get current status of all slots

**Slots**: None

**Sample Utterances**:

- "What's my status"
- "How many pills do I have"
- "Check my bottles"

**Response**: Lists each slot with prescription name and pill count

#### 3. AMAZON.HelpIntent

**Response**: "PillBuddy helps you track your pill bottles. You can set up bottles, check your pill counts, and get refill reminders. What would you like to do?"

#### 4. AMAZON.StopIntent

**Response**: "Goodbye!"

#### 5. AMAZON.CancelIntent

**Response**: "Okay, cancelled."

### Permissions

**Required Permission**: `alexa::devices:all:notifications:write`

**Purpose**: Enable proactive notifications for refill reminders

**User Action**: Users must grant this permission when enabling the skill

---

## Proactive Notifications Setup

### Enable in Skill Manifest

Already configured in `skill.json`:

```json
{
  "permissions": [
    {
      "name": "alexa::devices:all:notifications:write"
    }
  ],
  "events": {
    "subscriptions": [
      {
        "eventName": "SKILL_PROACTIVE_SUBSCRIPTION_CHANGED"
      }
    ]
  }
}
```

### Testing Notifications

For hackathon/development, notifications are logged but not actually sent. For production:

1. Skill must be certified and published
2. Users must grant notification permissions
3. Implement Alexa Events API in Lambda function

### Notification Types

1. **Refill Reminder** (pill count < 5, has refills)
   - "Your [prescription] is running low with [count] pills remaining. Please get a refill soon."

2. **Disposal Reminder** (pill count < 5, no refills)
   - "Your [prescription] is running low with [count] pills remaining. Please dispose of the empty bottle."

3. **Bottle Return Reminder** (bottle out > 10 minutes)
   - "Reminder: Please return your [prescription] bottle to slot [slot] of your PillBuddy."

---

## Troubleshooting

### Skill Can't Invoke Lambda

**Symptom**: "There was a problem with the requested skill's response"

**Solutions**:

1. Verify Lambda trigger is configured:
   ```bash
   aws lambda get-policy --function-name PillBuddy_AlexaHandler
   ```
2. Check Skill ID matches in Lambda permission
3. Verify Lambda ARN in skill endpoint configuration
4. Check CloudWatch Logs for Lambda errors:
   ```bash
   aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow
   ```

### Interaction Model Won't Build

**Symptom**: Build fails with validation errors

**Solutions**:

1. Check all required slots are defined
2. Verify slot types are valid (AMAZON.MedicationName, AMAZON.NUMBER, AMAZON.YesNo)
3. Ensure sample utterances include slot references: `{slotName}`
4. Check for duplicate utterances across intents

### Device Offline Error

**Symptom**: Alexa says "Your PillBuddy device appears to be offline"

**Solutions**:

1. Verify ESP32 is connected to AWS IoT Core
2. Check device record exists in DynamoDB:
   ```bash
   aws dynamodb get-item \
     --table-name PillBuddy_Devices \
     --key '{"device_id":{"S":"esp32_001"}}'
   ```
3. Ensure `last_seen` timestamp is recent (< 5 minutes)
4. Test IoT connectivity:
   ```bash
   aws iot-data publish \
     --topic pillbuddy/events/esp32_001 \
     --payload '{"event_type":"slot_state_changed","slot":1,"state":"in_holder","in_holder":true,"sensor_level":1,"ts_ms":1700000000000,"sequence":1}' \
     --cli-binary-format raw-in-base64-out
   ```

### Slot Values Not Captured

**Symptom**: Lambda receives null or undefined slot values

**Solutions**:

1. Check slot elicitation prompts are configured
2. Verify dialog management is enabled
3. Test with explicit slot values: "The prescription is Aspirin with 30 pills"
4. Check Lambda logs for received slot values

### Notifications Not Working

**Symptom**: No proactive notifications received

**Solutions**:

1. Verify permission is enabled in skill manifest
2. Check user has granted notification permission
3. For development: Notifications are logged but not sent (requires published skill)
4. Check CloudWatch Logs for notification attempts

---

## Deployment Checklist

Before deploying to production:

- [ ] Lambda function deployed and tested
- [ ] DynamoDB tables created
- [ ] IoT Core configured
- [ ] Skill created in Developer Console
- [ ] Interaction model built successfully
- [ ] Lambda endpoint configured
- [ ] Lambda trigger added
- [ ] Proactive notifications enabled
- [ ] Skill tested in Development mode
- [ ] Privacy policy and terms of use URLs updated
- [ ] Skill icons created (108x108 and 512x512)
- [ ] Testing instructions completed
- [ ] All sample utterances tested

---

## Publishing the Skill (Optional)

For hackathon, publishing is not required. The skill works in Development mode on your devices.

To publish for public use:

1. **Complete Skill Information**:
   - Add skill icons (108x108 and 512x512 PNG)
   - Update privacy policy URL
   - Update terms of use URL
   - Add detailed description

2. **Submit for Certification**:
   - Click "Distribution" → "Availability"
   - Complete all required fields
   - Submit for review

3. **Certification Process**:
   - Amazon reviews skill (typically 1-2 weeks)
   - Address any feedback
   - Skill published to Alexa Skills Store

---

## Monitoring and Analytics

### Skill Metrics

View skill usage in Developer Console:

1. Go to "Analytics" tab
2. Monitor:
   - Unique users
   - Sessions
   - Intent usage
   - Utterance conflicts

### Lambda Metrics

Monitor Lambda performance:

```bash
# Invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=PillBuddy_AlexaHandler \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Error rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=PillBuddy_AlexaHandler \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

---

## Cost Estimation

For hackathon usage:

- **Alexa Skill**: Free (no charges for skill hosting)
- **Lambda Invocations**: ~$0.20/month (1000 invocations)
- **Proactive Notifications**: Free in development mode

**Total: ~$0.20/month** (plus Lambda costs from other components)

---

## Security Best Practices

### For Production

1. **Account Linking**: Implement account linking to map Alexa users to devices
2. **User Authentication**: Add authentication for sensitive operations
3. **Data Encryption**: Encrypt sensitive data in DynamoDB
4. **Input Validation**: Validate all slot values in Lambda
5. **Rate Limiting**: Implement rate limiting for API calls
6. **Audit Logging**: Log all user interactions for compliance

---

## References

- [Alexa Skills Kit Documentation](https://developer.amazon.com/docs/ask-overviews/build-skills-with-the-alexa-skills-kit.html)
- [ASK CLI Documentation](https://developer.amazon.com/docs/smapi/ask-cli-intro.html)
- [Alexa Proactive Events API](https://developer.amazon.com/docs/smapi/proactive-events-api.html)
- [Dialog Management](https://developer.amazon.com/docs/custom-skills/dialog-interface-reference.html)
- [Slot Types Reference](https://developer.amazon.com/docs/custom-skills/slot-type-reference.html)
- [Skill Certification Requirements](https://developer.amazon.com/docs/custom-skills/certification-requirements-for-custom-skills.html)
