# Fix "PillBuddy is not supported on this device" on Echo Show

## The Issue

You're getting: **"PillBuddy is not supported on this device"**

This is because Alexa requires **two-word invocation names** for custom skills. Your skill currently has "pillbuddy" (one word) in the Developer Console.

---

## The Fix (5 Steps)

### Step 1: Go to Alexa Developer Console

https://developer.amazon.com/alexa/console/ask

### Step 2: Click on Your PillBuddy Skill

Find your skill in the list and click on it.

### Step 3: Update Invocation Name

1. Click the **"Build"** tab
2. In the left sidebar, click **"Invocations"** (under "Interaction Model")
3. Change **"Skill Invocation Name"** from `pillbuddy` to `pill buddy` (two words, lowercase)
4. Click **"Save Model"**

### Step 4: Build the Model

1. Click the **"Build Model"** button (top right corner)
2. Wait for "Build Successful" message (30-60 seconds)

### Step 5: Enable Testing

1. Click the **"Test"** tab
2. At the top, change dropdown from "Off" to **"Development"**
3. Make sure locale is set to **"English (US)"**

---

## Test It

Now say to your Echo Show:

**"Alexa, open pill buddy"** (two words)

NOT "Alexa, open pillbuddy" (one word)

---

## Expected Response

Alexa should say:

> "Welcome to PillBuddy! Let's set up your pill bottles. I'll guide you through configuring each of the three slots. For the first slot, please tell me the prescription name, number of pills, and whether you have refills."

---

## Why Two Words?

Alexa's policy requires custom skills to use two-word invocation names to:

- Avoid conflicts with registered brand names
- Make invocation more natural
- Reduce confusion with built-in Alexa features

Single-word names are only allowed for registered trademarks.

---

## Alternative: Upload Interaction Model

If you prefer, you can upload the corrected interaction model:

1. Go to **Build** tab
2. Click **"JSON Editor"** (under Interaction Model in left sidebar)
3. Copy the contents of `infrastructure/alexa/interactionModel.json` from your repo
4. Paste into the editor
5. Click **"Save Model"**
6. Click **"Build Model"**

The file already has the correct two-word invocation name: `"invocationName": "pill buddy"`

---

## Troubleshooting

### Still Getting "Not Supported"?

1. **Check you said "pill buddy" (two words)** - not "pillbuddy"
2. **Verify testing is enabled** - Should say "Development" in Test tab
3. **Check locale** - Must be "English (US)"
4. **Wait 30 seconds** after building - Model needs to propagate
5. **Try in Test tab first** - Type "open pill buddy" in the Alexa Simulator

### Check Lambda Logs

After trying to invoke the skill, check if Lambda was called:

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --since 2m --region us-east-1
```

If you see logs, the skill is working but might have an error.  
If you see NO logs, the skill isn't reaching your Lambda (invocation name issue).

---

## Quick Verification Checklist

Before testing on Echo Show:

- [ ] Invocation name changed to "pill buddy" (two words)
- [ ] Model built successfully
- [ ] Testing enabled (set to "Development")
- [ ] Locale set to "English (US)"
- [ ] Endpoint configured with Lambda ARN
- [ ] Lambda permission allows Alexa Skills Kit

---

## Test in Developer Console First

Before trying on your Echo Show, test in the Developer Console:

1. Go to **Test** tab
2. Enable testing: "Development"
3. Type: `open pill buddy`
4. You should see the welcome message

If this works in the console but not on your Echo Show, the issue is with your Echo Show's account or registration.

---

## Echo Show Specific Issues

### Issue 1: Wrong Amazon Account

Make sure your Echo Show is registered to the SAME Amazon account as your Alexa Developer Console.

**Check**: Alexa app → Devices → Your Echo Show → Check registered account

### Issue 2: Skill Not Enabled

Even in development mode, you might need to enable the skill:

1. Open Alexa app on your phone
2. Go to **Skills & Games**
3. Go to **Your Skills** → **Dev**
4. Find "PillBuddy" and make sure it's enabled

### Issue 3: Echo Show Needs Restart

Sometimes Echo Show needs a restart after enabling a dev skill:

1. Unplug Echo Show
2. Wait 10 seconds
3. Plug back in
4. Wait for it to fully boot
5. Try again: "Alexa, open pill buddy"

---

## Success Indicators

You'll know it's working when:

1. ✅ Echo Show responds with the welcome message
2. ✅ Lambda logs show invocation
3. ✅ You can have a conversation with the skill

---

## Next Steps After It Works

Once you get the welcome message:

1. **Set up a prescription**: "Aspirin with 30 pills and yes for refills"
2. **Check status**: "Alexa, ask pill buddy what's my status"
3. **Test with ESP32**: Remove a bottle and see pill count decrement

---

## Need More Help?

If it still doesn't work after these steps:

1. Share a screenshot of your Invocations page (showing the invocation name)
2. Share what you see in the Test tab when you type "open pill buddy"
3. Share Lambda logs after trying to invoke the skill
