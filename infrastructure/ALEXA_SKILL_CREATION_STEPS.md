# PillBuddy Alexa Skill - Step-by-Step Creation Guide

Follow these steps to create your PillBuddy Alexa skill in the Developer Console.

## Prerequisites

✅ Lambda ARN: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`  
✅ AWS Account: `339712753637`  
✅ Region: `us-east-1`

---

## Step 1: Create the Skill

1. Go to: https://developer.amazon.com/alexa/console/ask
2. Click **"Create Skill"** button (top right)
3. Fill in the form:
   - **Skill name**: `PillBuddy`
   - **Primary locale**: `English (US)`
   - **Choose a type of experience**: Select `Other`
   - **Choose a model**: Select `Custom`
   - **Hosting services**: Select `Provision your own`
4. Click **"Next"** button (top right)
5. On the template page, select **"Start from Scratch"**
6. Click **"Next"** button
7. Review and click **"Create skill"** button

⏱️ Wait 10-15 seconds for skill creation to complete.

---

## Step 2: Set Invocation Name

1. In the left sidebar, click **"Invocations"** → **"Skill Invocation Name"**
2. Change the invocation name to: `pillbuddy` (all lowercase, one word)
3. Click **"Save Model"** button at the top

---

## Step 3: Create Custom Slot Types

Before creating intents, we need to create a custom slot type for yes/no responses.

### 3.1: Create HasRefillsType Slot Type

1. In the left sidebar, click **"Slot Types"**
2. Click **"+ Add Slot Type"**
3. Select **"Create custom slot type"**
4. Slot type name: `HasRefillsType`
5. Add these slot values (click "+ Add slot value" for each):

**Value 1:**

- Slot value: `yes`
- Synonyms: `yeah, yep, sure, of course, definitely`

**Value 2:**

- Slot value: `no`
- Synonyms: `nope, nah, negative, not really`

6. Click **"Save"**

---

## Step 4: Create SetupSlotIntent

### 4.1: Create the Intent

1. In the left sidebar, click **"Interaction Model"** → **"Intents"**
2. Click **"+ Add Intent"** button
3. Select **"Create custom intent"**
4. Intent name: `SetupSlotIntent`
5. Click **"Create custom intent"** button

### 4.2: Add Slot 1 - prescriptionName

1. Under "Intent Slots", click **"+ Add"** button
2. Fill in:
   - **Slot name**: `prescriptionName`
   - **Slot type**: `PrescriptionNameType` (the custom type you just created)
3. Check the box: **"This slot is required to fulfill the intent"**
4. Under "Alexa speech prompts", click **"+ Add"**
5. Enter prompt: `What's the name of the prescription?`
6. Click **"+"** to add it

### 4.3: Add Slot 2 - pillCount

1. Click **"+ Add"** button again (under Intent Slots)
2. Fill in:
   - **Slot name**: `pillCount`
   - **Slot type**: `AMAZON.NUMBER`
3. Check the box: **"This slot is required to fulfill the intent"**
4. Under "Alexa speech prompts", click **"+ Add"**
5. Enter prompt: `How many pills are in the bottle?`
6. Click **"+"** to add it
7. Scroll down to **"Slot Validation"**
8. Click **"+ Add validation rule"**
9. Select rule type: **"is greater than"**
10. Enter value: `0`
11. Enter prompt: `The pill count must be greater than zero. How many pills are in the bottle?`
12. Click **"+"** to add the validation

### 4.4: Add Slot 3 - hasRefills

1. Click **"+ Add"** button again (under Intent Slots)
2. Fill in:
   - **Slot name**: `hasRefills`
   - **Slot type**: `HasRefillsType` (the custom type you just created)
3. Check the box: **"This slot is required to fulfill the intent"**
4. Under "Alexa speech prompts", click **"+ Add"**
5. Enter prompt: `Does this prescription have refills available?`
6. Click **"+"** to add it

### 4.5: Add Sample Utterances

Scroll up to the "Sample Utterances" section and add these (one at a time):

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

**How to add**: Type each utterance in the box and press Enter or click the "+" button.

7. Click **"Save Model"** button at the top

---

## Step 5: Create QueryStatusIntent

### 5.1: Create the Intent

1. Click **"+ Add Intent"** button
2. Select **"Create custom intent"**
3. Intent name: `QueryStatusIntent`
4. Click **"Create custom intent"** button

### 5.2: Add Sample Utterances

Add these sample utterances (no slots needed for this intent):

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

5. Click **"Save Model"** button at the top

---

## Step 6: Build the Model

1. Click the **"Build Model"** button at the top of the page
2. ⏱️ Wait 30-60 seconds for the build to complete
3. You should see a green success message: **"Build Successful"**

---

## Step 7: Configure Lambda Endpoint

1. In the left sidebar, click **"Endpoint"**
2. Select **"AWS Lambda ARN"** (should be selected by default)
3. In the **"Default Region"** field, paste your Lambda ARN:
   ```
   arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler
   ```
4. **IMPORTANT**: At the top of the page, you'll see **"Your Skill ID"**
   - Copy this Skill ID (it looks like: `amzn1.ask.skill.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
   - Save it somewhere - you'll need it in the next step!
5. Click **"Save Endpoints"** button

---

## Step 8: Add Lambda Trigger Permission

Now we need to give the Alexa skill permission to invoke your Lambda function.

**Open your terminal** and run this command (replace `YOUR_SKILL_ID` with the Skill ID you copied in Step 6):

```bash
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token YOUR_SKILL_ID \
  --region us-east-1
```

**Example** (if your Skill ID is `amzn1.ask.skill.12345678-1234-1234-1234-123456789abc`):

```bash
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token amzn1.ask.skill.12345678-1234-1234-1234-123456789abc \
  --region us-east-1
```

You should see output like:

```json
{
  "Statement": "{\"Sid\":\"alexa-skill-trigger\",\"Effect\":\"Allow\",...}"
}
```

---

## Step 9: Enable APL Interface (for Echo Show Visual Display)

To enable visual display support on Echo Show devices, you need to enable the APL (Alexa Presentation Language) interface:

1. In the left sidebar, click **"Interfaces"**
2. Find **"Alexa Presentation Language"** in the list
3. Toggle the switch to **ON**
4. Click **"Save Interfaces"** button at the top

**What this enables:**

- Visual display on Echo Show devices when users ask for pill status
- Shows pill bottle slots, prescription names, pill counts, and low-pill warnings
- Voice-only devices (Echo, Echo Dot) continue to work normally without visual display

**Note**: This interface must be enabled for the APL visual display feature to work. Without it, Echo Show devices will only receive voice responses.

---

## Step 10: Enable Testing

1. Click the **"Test"** tab at the top of the page
2. In the dropdown that says "Off", select **"Development"**
3. You should see: **"Test is enabled for this skill"**

---

## Step 11: Test Your Skill!

### Test in the Console

In the test simulator on the left side:

**Test 1: Launch the skill**

- Type or say: `open pillbuddy`
- Expected response: "Welcome to PillBuddy! Let's set up your pill bottles..."

**Test 2: Setup a prescription**

- Type: `the prescription is aspirin with 30 pills`
- Alexa will ask: "Does this prescription have refills available?"
- Type: `yes`
- Expected response: "Great! I've saved Aspirin with refills with 30 pills..."

**Test 3: Check status**

- Type: `what's my status`
- Expected response: Should list your configured prescriptions

### Test with Your Alexa Device

If you have an Alexa device (Echo, Echo Dot, etc.) registered to the same Amazon account:

1. Just say: **"Alexa, open pillbuddy"**
2. The skill is automatically available on your devices in Development mode!

---

## Step 12: Enable Proactive Notifications (Optional)

For refill reminders to work:

1. In the left sidebar, click **"Permissions"**
2. Find **"Alexa::Devices::All::Notifications::Write"**
3. Toggle it **ON**
4. Click **"Save Permissions"**

**Note**: For hackathon, notifications are logged but not actually sent. Full notification support requires skill certification.

---

## Troubleshooting

### "There was a problem with the requested skill's response"

**Solution**: Check that you ran the Lambda permission command in Step 7.

Verify the permission exists:

```bash
aws lambda get-policy --function-name PillBuddy_AlexaHandler --region us-east-1
```

### "The device is offline"

**Solution**: This is expected if you haven't set up an ESP32 device yet. The Lambda function checks for device connectivity.

To test without a device, you can manually create a device record:

```bash
aws dynamodb put-item \
  --table-name PillBuddy_Devices \
  --item '{
    "device_id": {"S": "esp32_001"},
    "online": {"BOOL": true},
    "last_seen": {"N": "'$(date +%s)000'"},
    "created_at": {"N": "'$(date +%s)000'"},
    "slots": {"M": {
      "1": {"M": {"in_holder": {"BOOL": false}, "last_state_change": {"N": "0"}}},
      "2": {"M": {"in_holder": {"BOOL": false}, "last_state_change": {"N": "0"}}},
      "3": {"M": {"in_holder": {"BOOL": false}, "last_state_change": {"N": "0"}}}
    }}
  }' \
  --region us-east-1
```

### Build fails

**Solution**: Make sure all slots are properly configured with their types and prompts.

### Can't find the skill on my Alexa device

**Solution**:

- Make sure testing is enabled (Step 8)
- Ensure your Alexa device is registered to the same Amazon account as your Developer account
- Try saying the full invocation: "Alexa, open pillbuddy"

---

## View Lambda Logs

To see what's happening behind the scenes:

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow --region us-east-1
```

This will show you real-time logs as you test the skill.

---

## Next Steps

After your skill is working:

1. ✅ Test all intents (Launch, SetupSlot, QueryStatus, Help, Stop)
2. ✅ Register an ESP32 device (see `IOT_CORE_SETUP.md`)
3. ✅ Test end-to-end with physical hardware
4. ✅ Update ALEXA_SKILL_ID in Lambda environment variables

---

## Summary

You've successfully created:

- ✅ PillBuddy Alexa Skill
- ✅ Invocation name: "pillbuddy"
- ✅ SetupSlotIntent with 3 slots
- ✅ QueryStatusIntent
- ✅ Lambda endpoint configured
- ✅ Testing enabled

**Your skill is now ready to use!** 🎉

Try saying: **"Alexa, open pillbuddy"** on any Alexa device registered to your account.
