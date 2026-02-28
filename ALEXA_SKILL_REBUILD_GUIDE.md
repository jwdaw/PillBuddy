# Alexa Skill Rebuild Guide - PillBuddy

## Step 1: Create New Skill

1. Go to https://developer.amazon.com/alexa/console/ask
2. Click **"Create Skill"**
3. Fill in:
   - **Skill name**: `PillBuddy`
   - **Primary locale**: English (US)
   - **Choose a model**: Custom
   - **Choose a method to host your skill's backend resources**: Provision your own
4. Click **"Create skill"**
5. On the next page, choose **"Start from Scratch"** template
6. Click **"Continue with template"**

**IMPORTANT**: After creation, note down the new Skill ID (it will be different from the old one)

---

## Step 2: Configure Invocation Name

1. In the left sidebar, click **"Invocations"** (under Interaction Model)
2. Set **Skill Invocation Name**: `pill buddy` (two words, lowercase)
3. Click **"Save Model"**

---

## Step 3: Import Interaction Model

1. In the left sidebar, click **"JSON Editor"** (under Interaction Model)
2. Delete everything in the editor
3. Copy the ENTIRE contents from `infrastructure/alexa/interactionModel.json`
4. Paste into the editor
5. Click **"Save Model"**
6. Click **"Build Model"** (top right)
7. Wait for "Build Successful" message

---

## Step 4: Configure Endpoint

1. In the left sidebar, click **"Endpoint"** (near bottom)
2. Select **"AWS Lambda ARN"**
3. In **"Default Region"** field, enter:
   ```
   arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler
   ```
4. Click **"Save Endpoints"**

---

## Step 5: Update Lambda Permission

After creating the new skill, you'll have a NEW Skill ID. You need to update the Lambda permission.

**Get the new Skill ID:**

- At the top of the Alexa Developer Console page, click **"View Skill ID"**
- Copy the skill ID (format: `amzn1.ask.skill.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)

**Update Lambda permission:**

Run these commands (replace `NEW_SKILL_ID` with your actual new skill ID):

```bash
# Remove old permission
aws lambda remove-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --region us-east-1

# Add new permission with new skill ID
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token NEW_SKILL_ID \
  --region us-east-1
```

---

## Step 6: Enable Testing

1. Click the **"Test"** tab (top of page)
2. In the dropdown at the top, select **"Development"** (instead of "Off")
3. Make sure locale is **"English (US)"**

---

## Step 7: Test in Developer Console

1. In the Test tab, in the text box at the top, type:
   ```
   open pill buddy
   ```
2. Press Enter

**Expected response:**

```
Welcome to PillBuddy! Let's set up your pill bottles. I'll guide you through configuring each of the three slots. For the first slot, please tell me the prescription name, number of pills, and whether you have refills.
```

**If you get an error:**

- Check Lambda logs: `aws logs tail /aws/lambda/PillBuddy_AlexaHandler --since 2m --region us-east-1`
- Verify the endpoint is configured correctly
- Verify the Lambda permission was added with the correct skill ID

---

## Step 8: Test on Echo Show

Once the Developer Console test works:

1. Make sure your Echo Show is registered to the SAME Amazon account as your Developer Console
2. Say: **"Alexa, open pill buddy"**
3. You should hear the welcome message

---

## Troubleshooting

### If Lambda permission command fails:

The old permission might not exist. That's okay - just run the "add" command:

```bash
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token NEW_SKILL_ID \
  --region us-east-1
```

### If "open pill buddy" doesn't work in Test tab:

1. Verify invocation name is exactly: `pill buddy` (two words)
2. Verify model was built successfully (green checkmark)
3. Verify endpoint shows the Lambda ARN
4. Check Lambda logs to see if it's being invoked

### If it works in Test tab but not on Echo Show:

1. Verify Echo Show is on the same Amazon account
2. Open Alexa app → Skills & Games → Your Skills → Dev → Find "PillBuddy" → Enable it
3. Restart Echo Show (unplug, wait 30 seconds, plug back in)

---

## Quick Reference

**Lambda ARN:**

```
arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler
```

**Invocation Name:**

```
pill buddy
```

**Test Phrases:**

- "Alexa, open pill buddy"
- "Alexa, launch pill buddy"
- "Alexa, start pill buddy"

**Interaction Model File:**

```
infrastructure/alexa/interactionModel.json
```

---

## After Successful Creation

Once the skill works, update the Skill ID in your documentation:

**Old Skill ID:** `amzn1.ask.skill.7b43b770-5a10-48d0-bec3-c3b2e521a116`  
**New Skill ID:** `[YOUR_NEW_SKILL_ID_HERE]`

Update this in:

- Any documentation files
- Any test event files
- Any deployment scripts
