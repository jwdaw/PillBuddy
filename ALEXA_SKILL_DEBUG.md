# Alexa Skill "Not Supported" - Debug Steps

## The Problem

You updated the invocation name to "pill buddy" (two words) but still getting "not supported on this device".

---

## Debug Checklist

### 1. Verify Invocation Name Was Saved

In Alexa Developer Console:

1. Go to **Build** tab
2. Click **Invocations** (left sidebar)
3. **Confirm** it shows: `pill buddy` (two words, lowercase)
4. If not, change it and click **Save Model**

### 2. Build the Model (CRITICAL)

After changing the invocation name, you MUST build:

1. Click **"Build Model"** button (top right)
2. Wait for "Build Successful" (30-60 seconds)
3. **Don't skip this step!**

### 3. Check Build Status

Look for these indicators:

- ✅ Green checkmark next to "Build Model" button
- ✅ "Build Successful" message
- ❌ If you see "Build Failed", click to see errors

### 4. Enable Testing

1. Click **"Test"** tab
2. Dropdown at top should say **"Development"** (not "Off")
3. Locale should be **"English (US)"**

### 5. Test in Developer Console FIRST

Before trying on Echo Show:

1. In **Test** tab
2. Type: `open pill buddy`
3. Press Enter

**What should happen:**

- You see a response from Alexa
- Response says "Welcome to PillBuddy..."

**If you get an error:**

- Share the error message
- Check Lambda logs

### 6. Check Endpoint Configuration

1. Go to **Build** tab
2. Click **Endpoint** (left sidebar)
3. Verify:
   - Service Endpoint Type: **AWS Lambda ARN**
   - Default Region: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`
4. Click **Save Endpoints** if you made changes

### 7. Verify Lambda Permission

Run this command:

```bash
aws lambda get-policy --function-name PillBuddy_AlexaHandler --region us-east-1 | jq -r '.Policy' | jq '.Statement[] | select(.Principal.Service == "alexa-appkit.amazon.com")'
```

Should show permission for your skill ID.

---

## Common Mistakes

### Mistake 1: Didn't Build Model

Changing the invocation name doesn't take effect until you build the model.

**Fix**: Click "Build Model" and wait for success.

### Mistake 2: Testing is "Off"

If testing is disabled, the skill won't work on your devices.

**Fix**: Set to "Development" in Test tab.

### Mistake 3: Wrong Amazon Account

Your Echo Show must be registered to the SAME Amazon account as your Developer Console.

**Check**:

- Alexa app → Devices → Your Echo Show
- Verify the account email matches your developer account

### Mistake 4: Skill Not Enabled

Even in development, you might need to enable the skill.

**Fix**:

1. Open Alexa app on phone
2. Go to **Skills & Games**
3. Go to **Your Skills** → **Dev** tab
4. Find "PillBuddy"
5. Make sure it's enabled

### Mistake 5: Cache Issue

Alexa might have cached the old invocation name.

**Fix**:

1. Disable the skill in Alexa app
2. Wait 30 seconds
3. Re-enable the skill
4. Try again

---

## Step-by-Step Verification

### Step 1: Test in Developer Console

```
1. Go to Test tab
2. Type: open pill buddy
3. Press Enter
```

**Expected**: Welcome message  
**If this works**: Problem is with Echo Show, not the skill  
**If this fails**: Problem is with skill configuration

### Step 2: Check Lambda Logs

After testing in console:

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --since 2m --region us-east-1
```

**Expected**: See "START RequestId" and "Received event"  
**If no logs**: Lambda not being invoked (endpoint issue)  
**If error logs**: Lambda has a bug

### Step 3: Test on Echo Show

Say: **"Alexa, open pill buddy"** (emphasize TWO words)

**If still "not supported"**:

- Echo Show might be on wrong account
- Skill might not be enabled on that device
- Need to restart Echo Show

---

## Alternative Test Phrases

Try these variations:

1. "Alexa, launch pill buddy"
2. "Alexa, start pill buddy"
3. "Alexa, ask pill buddy for help"

If ANY of these work, the invocation name is correct.

---

## Nuclear Option: Restart Echo Show

Sometimes Echo Show needs a restart:

1. Unplug Echo Show
2. Wait 30 seconds
3. Plug back in
4. Wait for full boot (2-3 minutes)
5. Try: "Alexa, open pill buddy"

---

## Check Skill ID Match

Verify the skill ID in Developer Console matches the Lambda permission:

**In Developer Console:**

1. Click "View Skill ID" (top of page)
2. Copy the skill ID

**In Lambda:**

```bash
aws lambda get-policy --function-name PillBuddy_AlexaHandler --region us-east-1 | jq -r '.Policy' | jq '.Statement[0].Condition.StringEquals'
```

Should show: `"lambda:EventSourceToken": "amzn1.ask.skill.YOUR_SKILL_ID"`

If they don't match, update Lambda permission:

```bash
aws lambda remove-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --region us-east-1

aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token YOUR_ACTUAL_SKILL_ID \
  --region us-east-1
```

---

## What to Share for Help

If still not working, share:

1. **Screenshot** of Invocations page (showing "pill buddy")
2. **Screenshot** of Test tab after typing "open pill buddy"
3. **Output** of Lambda logs command
4. **Exact phrase** you're saying to Echo Show
5. **Exact error** Echo Show is saying

---

## Expected Working Flow

When everything is correct:

1. You say: "Alexa, open pill buddy"
2. Echo Show: "Welcome to PillBuddy! Let's set up your pill bottles..."
3. Lambda logs show invocation
4. You can have a conversation with the skill

---

## Quick Diagnostic

Run these commands and share the output:

```bash
# 1. Check if model is built (look for "lastUpdateDate")
echo "Skill info:"
# (Need to check in Developer Console)

# 2. Check Lambda permission
echo "Lambda permission:"
aws lambda get-policy --function-name PillBuddy_AlexaHandler --region us-east-1 | jq -r '.Policy' | jq .

# 3. Test Lambda directly
echo "Testing Lambda:"
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --payload file://test-alexa-launch.json \
  --region us-east-1 \
  test-response.json && cat test-response.json | jq .

# 4. Check recent Lambda invocations
echo "Recent Lambda logs:"
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --since 30m --region us-east-1 | grep "START RequestId" | tail -5
```

If Lambda test works but Echo Show doesn't, the issue is with:

- Echo Show account
- Skill enablement
- Invocation name not propagated to device
