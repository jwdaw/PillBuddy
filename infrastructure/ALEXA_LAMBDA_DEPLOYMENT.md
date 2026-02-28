# Alexa Skill Handler Lambda Deployment Guide

This guide covers deploying the PillBuddy Alexa Skill Handler Lambda function.

## Prerequisites

1. AWS account with appropriate permissions
2. AWS CLI configured
3. DynamoDB tables deployed (PillBuddy_Devices, PillBuddy_Prescriptions)
4. AWS IoT Core endpoint URL

## Step 1: Get AWS IoT Core Endpoint

Before deploying, you need your IoT Core endpoint:

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

This will return something like: `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com`

Save this value - you'll need it for the Lambda environment variables.

## Step 2: Deploy Using AWS CDK (Recommended)

### Option A: Deploy with CDK Context

```bash
cd infrastructure

# Set IoT endpoint via context
cdk deploy --context iot_endpoint=YOUR_IOT_ENDPOINT_HERE

# Example:
# cdk deploy --context iot_endpoint=a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com
```

### Option B: Update cdk.json

Edit `infrastructure/cdk.json` and add the IoT endpoint:

```json
{
  "app": "python3 app.py",
  "context": {
    "iot_endpoint": "YOUR_IOT_ENDPOINT_HERE"
  }
}
```

Then deploy:

```bash
cd infrastructure
cdk deploy
```

### Option C: Manual Update After Deployment

If you deployed without setting the IoT endpoint, update it manually:

```bash
aws lambda update-function-configuration \
  --function-name PillBuddy_AlexaHandler \
  --environment Variables="{DEVICES_TABLE=PillBuddy_Devices,PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,IOT_ENDPOINT=YOUR_IOT_ENDPOINT,AWS_REGION=us-east-1}"
```

## Step 3: Verify Lambda Deployment

Check that the Lambda function was created:

```bash
aws lambda get-function --function-name PillBuddy_AlexaHandler
```

Verify environment variables:

```bash
aws lambda get-function-configuration --function-name PillBuddy_AlexaHandler --query 'Environment.Variables'
```

Expected output:

```json
{
  "DEVICES_TABLE": "PillBuddy_Devices",
  "PRESCRIPTIONS_TABLE": "PillBuddy_Prescriptions",
  "IOT_ENDPOINT": "a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com",
  "AWS_REGION": "us-east-1"
}
```

## Step 4: Get Lambda ARN

You'll need the Lambda ARN for Alexa Skill configuration:

```bash
aws lambda get-function --function-name PillBuddy_AlexaHandler --query 'Configuration.FunctionArn' --output text
```

Save this ARN - you'll use it as the endpoint in your Alexa Skill.

## Step 5: Create Alexa Skill

### Using Alexa Developer Console

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click "Create Skill"
3. Configure:
   - Skill name: "PillBuddy"
   - Primary locale: English (US)
   - Model: Custom
   - Hosting: Provision your own
4. Click "Create skill"

### Configure Invocation

1. In the left sidebar, click "Invocations" → "Skill Invocation Name"
2. Set invocation name: `pillbuddy`
3. Save

### Add Intents

#### SetupSlotIntent

1. Click "Interaction Model" → "Intents"
2. Click "Add Intent" → "Create custom intent"
3. Intent name: `SetupSlotIntent`
4. Add slots:
   - Slot name: `prescriptionName`, Slot type: `AMAZON.MedicationName` (or create custom)
   - Slot name: `pillCount`, Slot type: `AMAZON.NUMBER`
   - Slot name: `hasRefills`, Slot type: `AMAZON.YesNo`
5. Add sample utterances:
   ```
   The prescription is {prescriptionName} with {pillCount} pills
   {prescriptionName} has {pillCount} pills and {hasRefills} refills
   Set up {prescriptionName}
   {prescriptionName} with {pillCount} pills
   ```
6. Save

#### QueryStatusIntent

1. Click "Add Intent" → "Create custom intent"
2. Intent name: `QueryStatusIntent`
3. Add sample utterances:
   ```
   What's my status
   How many pills do I have
   Check my bottles
   What's in my PillBuddy
   Tell me my pill counts
   ```
4. Save

#### Built-in Intents

The following intents are already included:

- `AMAZON.HelpIntent`
- `AMAZON.StopIntent`
- `AMAZON.CancelIntent`

### Configure Endpoint

1. Click "Endpoint" in the left sidebar
2. Select "AWS Lambda ARN"
3. Default Region: Paste your Lambda ARN from Step 4
4. Copy the "Your Skill ID" - you'll need this for the next step
5. Save Endpoints

## Step 6: Add Alexa Trigger to Lambda

Now that you have your Skill ID, add the Alexa trigger:

```bash
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token YOUR_SKILL_ID_HERE
```

Replace `YOUR_SKILL_ID_HERE` with the Skill ID from the Alexa Developer Console.

## Step 7: Build and Test

### Build the Interaction Model

1. In Alexa Developer Console, click "Build Model" (top right)
2. Wait for the build to complete (usually 30-60 seconds)

### Test the Skill

1. Click "Test" tab at the top
2. Enable testing: "Development" mode
3. Test with voice or text:

**Test 1: Launch**

```
User: Alexa, open pillbuddy
Alexa: Welcome to PillBuddy! Let's set up your pill bottles...
```

**Test 2: Setup Slot**

```
User: The prescription is Aspirin with 30 pills
Alexa: Great! I've saved Aspirin...
```

**Test 3: Query Status**

```
User: Alexa, ask pillbuddy what's my status
Alexa: Slot 1 has Aspirin with 30 pills remaining...
```

## Step 8: Test with Lambda Console

You can also test the Lambda function directly:

1. Go to AWS Lambda Console
2. Open `PillBuddy_AlexaHandler`
3. Click "Test" tab
4. Create test event with this JSON:

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

5. Click "Test"
6. Verify response contains appropriate speech output

## Troubleshooting

### Lambda Function Not Found

If CDK deployment fails with Lambda not found:

```bash
# Verify the lambda directory exists
ls -la infrastructure/lambda/alexa_handler/

# Ensure lambda_function.py exists
cat infrastructure/lambda/alexa_handler/lambda_function.py
```

### IoT Endpoint Not Set

If you see `REPLACE_WITH_IOT_ENDPOINT` in environment variables:

```bash
# Get your IoT endpoint
IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)

# Update Lambda environment
aws lambda update-function-configuration \
  --function-name PillBuddy_AlexaHandler \
  --environment Variables="{DEVICES_TABLE=PillBuddy_Devices,PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,IOT_ENDPOINT=$IOT_ENDPOINT,AWS_REGION=us-east-1}"
```

### DynamoDB Permission Errors

If you see permission denied errors:

```bash
# Check Lambda execution role
aws lambda get-function-configuration --function-name PillBuddy_AlexaHandler --query 'Role'

# Verify role has DynamoDB permissions
aws iam get-role-policy --role-name ROLE_NAME --policy-name POLICY_NAME
```

### Alexa Skill Can't Invoke Lambda

If Alexa returns "There was a problem with the requested skill's response":

1. Verify Lambda trigger is configured:

   ```bash
   aws lambda get-policy --function-name PillBuddy_AlexaHandler
   ```

2. Check CloudWatch Logs:

   ```bash
   aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow
   ```

3. Verify Skill ID matches:
   - Check Alexa Developer Console → Endpoint → Your Skill ID
   - Compare with Lambda trigger event source token

## Monitoring

### CloudWatch Logs

View Lambda logs:

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow
```

### CloudWatch Metrics

Monitor Lambda metrics:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=PillBuddy_AlexaHandler \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Next Steps

After deploying the Alexa Lambda:

1. **Test with Real Device**: Ensure your ESP32 device is online and publishing to IoT Core
2. **Test Full Workflow**: Try the complete setup flow with voice commands
3. **Deploy IoT Event Processor**: Continue with Task 5 to handle device events
4. **Monitor Usage**: Check CloudWatch logs and metrics regularly

## Cost Estimation

For hackathon usage:

- Lambda invocations: ~1000/month = $0.20
- Lambda duration: ~2 seconds average = $0.03
- CloudWatch Logs: ~100 MB = $0.50

**Total: ~$0.73/month** (plus DynamoDB costs from main infrastructure)

## Security Notes

- For hackathon: Device ID defaults to `esp32_001` (hardcoded)
- For production: Implement Alexa account linking to map users to devices
- Store device mappings in DynamoDB with user authentication
- Use AWS Secrets Manager for sensitive configuration
- Enable CloudWatch Logs encryption
- Restrict IAM permissions to minimum required

## References

- [Alexa Skills Kit Documentation](https://developer.amazon.com/docs/ask-overviews/build-skills-with-the-alexa-skills-kit.html)
- [AWS Lambda Python Documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [AWS IoT Core Documentation](https://docs.aws.amazon.com/iot/latest/developerguide/what-is-aws-iot.html)
- [DynamoDB Python SDK](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)
