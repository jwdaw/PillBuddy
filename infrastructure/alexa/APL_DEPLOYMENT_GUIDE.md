# APL Visual Display Deployment Guide

## Status

✅ **Lambda Function**: Deployed with APL support (February 28, 2026)
⏳ **Alexa Skill Configuration**: Needs manual update in Developer Console

## What Was Deployed

The Lambda function now includes:

- APL document template (`apl_templates/pill_status_display.json`)
- Device capability detection (`supports_apl()` function)
- APL response builder (`build_apl_datasources()`, `load_apl_document()`)
- Updated `handle_query_status_intent()` with APL integration

## Next Step: Enable APL Interface

You need to enable the APL interface in the Alexa Developer Console. This is a simple toggle that takes 2 minutes.

### Instructions

1. **Open Alexa Developer Console**
   - Go to: https://developer.amazon.com/alexa/console/ask
   - Sign in with your Amazon Developer account

2. **Find Your Skill**
   - Look for **PillBuddy** in the skill list
   - Click on it to open

3. **Enable APL Interface**
   - Click the **Build** tab (top navigation)
   - In the left sidebar, scroll down and click **Interfaces**
   - Find **Alexa Presentation Language** in the list
   - Toggle the switch to **ON** (it will turn blue/green)
   - Click **Save Interfaces** button at the top

4. **Rebuild the Model**
   - Click **Build Model** button (top right)
   - Wait 30-60 seconds for the build to complete
   - You should see a green "Build Successful" message

5. **Test It!**
   - Click the **Test** tab at the top
   - Make sure testing is enabled (set to "Development")
   - Type: `open pill buddy`
   - Then type: `what's my status`
   - You should see the visual display preview on the right side!

## Your Skill Details

- **Skill Name**: PillBuddy
- **Skill ID**: `amzn1.ask.skill.74757f0a-fe9f-4daa-b11b-31832cf97e17`
- **Invocation Name**: `pill buddy`
- **Lambda Function**: `PillBuddy_AlexaHandler`
- **Region**: us-east-1

## What the Visual Display Shows

When users with Echo Show devices ask "what's my status", they'll see:

- **Title**: "PillBuddy Status"
- **Three pill bottle slots** displayed horizontally
- **For each slot**:
  - Prescription name (if bottle is present)
  - Pill count with "pills remaining" label
  - Visual indicator if bottle is missing
  - Red/amber warning if pills are low (≤7 pills)

## Testing on Different Devices

### Echo Show (Visual + Voice)

- Say: "Alexa, ask pill buddy what's my status"
- You'll see the visual display AND hear the voice response

### Echo/Echo Dot (Voice Only)

- Say: "Alexa, ask pill buddy what's my status"
- You'll only hear the voice response (no visual)
- Everything works exactly as before

## Troubleshooting

### Visual display doesn't appear on Echo Show

1. **Check APL is enabled**
   - Go back to Build > Interfaces
   - Verify "Alexa Presentation Language" toggle is ON

2. **Rebuild the model**
   - Sometimes you need to rebuild after enabling interfaces
   - Click "Build Model" again

3. **Check device compatibility**
   - Only Echo Show 5, 8, 10, and 15 support APL
   - Echo Spot and older Echo Show devices may have limited support

4. **View Lambda logs**
   ```bash
   aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow --region us-east-1
   ```

   - Look for "APL supported: True" or "APL supported: False" messages

### Lambda errors

If you see errors in testing:

```bash
# Check Lambda function status
aws lambda get-function --function-name PillBuddy_AlexaHandler --region us-east-1

# View recent logs
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --since 5m --region us-east-1
```

## Verification Checklist

After enabling APL, verify:

- [ ] APL interface is enabled in Developer Console (Build > Interfaces)
- [ ] Model is rebuilt successfully
- [ ] Test in console shows visual display preview
- [ ] Echo Show device shows visual display when asking for status
- [ ] Echo/Echo Dot devices still work with voice-only response

## Files Modified

- `infrastructure/lambda/alexa_handler/lambda_function.py` - Added APL support
- `infrastructure/lambda/alexa_handler/apl_templates/pill_status_display.json` - APL template
- `infrastructure/alexa/skill.json` - Added APL interface declaration

## Deployment Date

Lambda deployed: February 28, 2026 at 16:38 UTC

## Next Steps

Once APL is enabled and tested:

1. Test with real Echo Show device
2. Test with different pill counts to see low-pill warnings
3. Test with missing bottles to see empty slot indicators
4. Document any issues or improvements needed

---

**Need help?** Check the logs or reach out with any questions!
