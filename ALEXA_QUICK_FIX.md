# Alexa Skill "Not Supported" Error - Quick Fix

## Error Message

> "pill buddy is not supported on this device"

## Root Cause

**CRITICAL**: Alexa requires invocation names to be **two words** for custom skills. Single-word invocation names are only allowed for registered brand names.

Your skill was configured with "pillbuddy" (one word), which Alexa rejects.

## The Fix

Change the invocation name from "pillbuddy" to "pill buddy" (two words).

---

## Other Possible Causes & Solutions

### 1. Testing Not Enabled (Most Common)

**In Alexa Developer Console:**

1. Go to your skill: https://developer.amazon.com/alexa/console/ask
2. Click on "PillBuddy" skill
3. Go to **Test** tab
4. At the top, there's a dropdown that says "Off"
5. **Change it to "Development"**
6. Try again: "open pill buddy"

---

### 2. Skill Not Built

**In Alexa Developer Console:**

1. Go to **Build** tab
2. Click **"Build Model"** button (top right)
3. Wait for build to complete (usually 30-60 seconds)
4. Go back to **Test** tab
5. Try again

---

### 3. Wrong Locale

Your skill is configured for **en-US** only.

**Check your test console locale:**

1. In Test tab, look for language selector
2. Make sure it's set to **"English (US)"**
3. Not "English (UK)", "English (CA)", etc.

---

### 4. Endpoint Not Configured

**In Alexa Developer Console:**

1. Go to **Build** tab
2. Click **Endpoint** in left sidebar
3. Select **AWS Lambda ARN**
4. **Default Region**: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`
5. Click **Save Endpoints**
6. Click **Build Model**

---

### 5. Invocation Name Issue

**CRITICAL FIX**: Alexa requires two-word invocation names for custom skills.

**Update invocation name:**

1. Go to **Build** tab
2. Click **Invocations** in left sidebar
3. **Skill Invocation Name** should be: `pill buddy` (two words, lowercase)
4. If it says "pillbuddy" (one word), change it to "pill buddy"
5. Click **Save Model**
6. Click **Build Model**
7. Wait for build to complete
8. Go to Test tab and try: "open pill buddy"

---

## Step-by-Step Fix (Do This First)

### Step 1: Update Endpoint

```
1. Go to: https://developer.amazon.com/alexa/console/ask
2. Click your PillBuddy skill
3. Click "Build" tab
4. Click "Endpoint" in left menu
5. Select "AWS Lambda ARN"
6. Paste: arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler
7. Click "Save Endpoints"
```

### Step 2: Build Model

```
1. Still in Build tab
2. Click "Build Model" button (top right)
3. Wait for "Build Successful" message
```

### Step 3: Enable Testing

```
1. Click "Test" tab
2. Change dropdown from "Off" to "Development"
3. Type: "open pill buddy"
```

---

## Alternative: Use Alexa Simulator

Instead of typing, try the voice simulator:

1. In Test tab
2. Click the microphone icon
3. Say: "open pill buddy"
4. Or type it in the text box

---

## Verify Skill Configuration

Run this to make sure Lambda is accessible:

```bash
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --cli-binary-format raw-in-base64-out \
  --payload '{"request":{"type":"LaunchRequest"},"session":{"new":true}}' \
  --region us-east-1 \
  test-response.json && cat test-response.json
```

Should return an Alexa response (not an error).

---

## Still Not Working?

### Check Skill Status

1. In Alexa Developer Console
2. Go to **Build** tab
3. Look for any red error indicators
4. Check **Interaction Model** → **JSON Editor**
5. Make sure it matches: `infrastructure/alexa/interactionModel.json`

### Check Lambda Logs

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow --region us-east-1
```

Then try invoking the skill and watch for errors.

---

## What Should Happen

**You say**: "Alexa, open pill buddy"

**Alexa responds**:

> "Welcome to PillBuddy! Let's set up your pill bottles. I'll guide you through configuring each of the three slots..."

---

## Quick Test Without Device

To test without worrying about device status, you can temporarily modify the Lambda to skip the online check, but for now, just make sure the skill responds at all (even with "device offline" message).

---

## Need to Rebuild Skill?

If you need to start fresh:

### Upload Interaction Model

1. Go to **Build** tab
2. Click **JSON Editor** (under Interaction Model)
3. Copy contents of `infrastructure/alexa/interactionModel.json`
4. Paste into editor
5. Click **Save Model**
6. Click **Build Model**

### Configure Endpoint

1. Click **Endpoint**
2. AWS Lambda ARN: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`
3. Save

### Enable Testing

1. Go to **Test** tab
2. Enable "Development"
3. Test: "open pill buddy"
