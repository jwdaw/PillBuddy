# PillBuddy Deployment Status

**Deployment Date**: February 28, 2026  
**AWS Account**: 339712753637  
**Region**: us-east-1

## ✅ Deployed Resources

### DynamoDB Tables

| Table Name              | Partition Key | Sort Key  | Capacity       | TTL       | Status    |
| ----------------------- | ------------- | --------- | -------------- | --------- | --------- |
| PillBuddy_Devices       | device_id     | -         | 5 RCU / 5 WCU  | No        | ✅ Active |
| PillBuddy_Prescriptions | device_id     | slot      | 5 RCU / 5 WCU  | No        | ✅ Active |
| PillBuddy_Events        | device_id     | timestamp | 5 RCU / 10 WCU | Yes (ttl) | ✅ Active |

### Lambda Functions

| Function Name               | Runtime     | Memory | Timeout | Status    |
| --------------------------- | ----------- | ------ | ------- | --------- |
| PillBuddy_AlexaHandler      | Python 3.11 | 256 MB | 10s     | ✅ Active |
| PillBuddy_IoTEventProcessor | Python 3.11 | 256 MB | 30s     | ✅ Active |
| PillBuddy_TimeoutChecker    | Python 3.11 | 128 MB | 10s     | ✅ Active |

### AWS IoT Core

| Resource     | Name/Value                                    | Status     |
| ------------ | --------------------------------------------- | ---------- |
| Thing Type   | PillBuddyDevice                               | ✅ Created |
| IoT Policy   | PillBuddyDevicePolicy                         | ✅ Created |
| IoT Endpoint | agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com | ✅ Active  |
| IoT Rule     | PillBuddyEventRule                            | ✅ Active  |

### EventBridge

| Rule Name                   | Schedule        | Target                   | Status    |
| --------------------------- | --------------- | ------------------------ | --------- |
| PillBuddyTimeoutCheckerRule | rate(5 minutes) | PillBuddy_TimeoutChecker | ✅ Active |

## 📋 Environment Variables

### PillBuddy_AlexaHandler

```
DEVICES_TABLE=PillBuddy_Devices
PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions
IOT_ENDPOINT=agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com
```

### PillBuddy_IoTEventProcessor

```
DEVICES_TABLE=PillBuddy_Devices
PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions
EVENTS_TABLE=PillBuddy_Events
IOT_ENDPOINT=agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com
ALEXA_SKILL_ID=placeholder
```

### PillBuddy_TimeoutChecker

```
PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions
ALEXA_SKILL_ID=placeholder
```

## 🔗 Resource ARNs

```
Alexa Handler Lambda: arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler
IoT Event Processor: arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_IoTEventProcessor
Timeout Checker: arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_TimeoutChecker

IoT Rule: arn:aws:iot:us-east-1:339712753637:rule/PillBuddyEventRule
EventBridge Rule: arn:aws:events:us-east-1:339712753637:rule/PillBuddyTimeoutCheckerRule
```

## 📝 Next Steps

### 1. Configure Alexa Skill

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Create a new skill:
   - Skill name: "PillBuddy"
   - Default language: English (US)
   - Model: Custom
   - Hosting: Provision your own
3. Upload interaction model from `infrastructure/alexa/interactionModel.json`
4. Upload skill manifest from `infrastructure/alexa/skill.json`
5. Set Lambda endpoint: `arn:aws:lambda:us-east-1:339712753637:function:PillBuddy_AlexaHandler`
6. Add Lambda trigger permission:
   ```bash
   aws lambda add-permission \
     --function-name PillBuddy_AlexaHandler \
     --statement-id alexa-skill-trigger \
     --action lambda:InvokeFunction \
     --principal alexa-appkit.amazon.com \
     --event-source-token YOUR_SKILL_ID \
     --region us-east-1
   ```
7. Update ALEXA_SKILL_ID in Lambda environment variables

### 2. Register ESP32 Device

Use the setup script from `infrastructure/IOT_CORE_SETUP.md`:

```bash
cd infrastructure
# Make sure you have the setup script or follow manual steps
./setup-device.sh esp32_001
```

Or manually:

1. Create IoT Thing: `pillbuddy_esp32_001`
2. Generate certificates
3. Attach policy: `PillBuddyDevicePolicy`
4. Flash certificates to ESP32
5. Configure MQTT client with:
   - Endpoint: `agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com`
   - Client ID: `pillbuddy_esp32_001`
   - Publish topic: `pillbuddy/events/esp32_001`
   - Subscribe topic: `pillbuddy/cmd/esp32_001`

### 3. Test the System

#### Test Alexa Handler

```bash
aws lambda invoke \
  --function-name PillBuddy_AlexaHandler \
  --payload file://lambda/alexa_handler/test_events.json \
  --region us-east-1 \
  response.json
```

#### Test IoT Event Flow

```bash
aws iot-data publish \
  --topic pillbuddy/events/esp32_001 \
  --payload '{"event_type":"slot_state_changed","slot":1,"state":"not_in_holder","in_holder":false,"sensor_level":0,"ts_ms":1709096400000,"sequence":1}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1
```

#### Check Lambda Logs

```bash
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --follow --region us-east-1
```

## 🔍 Monitoring

### CloudWatch Logs

- Alexa Handler: `/aws/lambda/PillBuddy_AlexaHandler`
- IoT Event Processor: `/aws/lambda/PillBuddy_IoTEventProcessor`
- Timeout Checker: `/aws/lambda/PillBuddy_TimeoutChecker`

### View Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow --region us-east-1

# View recent logs
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --since 1h --region us-east-1
```

### DynamoDB Monitoring

```bash
# Check table status
aws dynamodb describe-table --table-name PillBuddy_Devices --region us-east-1

# Scan devices table
aws dynamodb scan --table-name PillBuddy_Devices --region us-east-1

# Query prescriptions
aws dynamodb query \
  --table-name PillBuddy_Prescriptions \
  --key-condition-expression "device_id = :id" \
  --expression-attribute-values '{":id":{"S":"esp32_001"}}' \
  --region us-east-1
```

## 💰 Cost Estimate

Based on hackathon usage (1-3 devices, moderate traffic):

| Service         | Usage                           | Monthly Cost     |
| --------------- | ------------------------------- | ---------------- |
| DynamoDB        | 3 tables, provisioned capacity  | ~$2.28           |
| Lambda          | 3 functions, ~100K invocations  | $0.17            |
| IoT Core        | 3 devices, ~100K messages       | ~$0.13           |
| EventBridge     | 1 rule, 8,640 invocations/month | ~$0.01           |
| CloudWatch Logs | ~1 GB logs                      | ~$0.50           |
| **Total**       |                                 | **~$3.09/month** |

## 🧹 Cleanup

To delete all resources:

```bash
# Delete Lambda functions
aws lambda delete-function --function-name PillBuddy_AlexaHandler --region us-east-1
aws lambda delete-function --function-name PillBuddy_IoTEventProcessor --region us-east-1
aws lambda delete-function --function-name PillBuddy_TimeoutChecker --region us-east-1

# Delete EventBridge rule
aws events remove-targets --rule PillBuddyTimeoutCheckerRule --ids 1 --region us-east-1
aws events delete-rule --name PillBuddyTimeoutCheckerRule --region us-east-1

# Delete IoT Rule
aws iot delete-topic-rule --rule-name PillBuddyEventRule --region us-east-1

# Delete CDK stack (includes DynamoDB tables, IoT resources)
cd infrastructure
cdk destroy
```

## 📚 Documentation

- [Table Schemas](TABLE_SCHEMAS.md)
- [IoT Core Setup](IOT_CORE_SETUP.md)
- [Lambda Configuration](LAMBDA_CONFIGURATION.md)
- [API Gateway Setup](API_GATEWAY_SETUP.md)
- [Alexa Lambda Deployment](ALEXA_LAMBDA_DEPLOYMENT.md)
- [EventBridge Setup](EVENTBRIDGE_SETUP.md)

## ✅ Deployment Checklist

- [x] DynamoDB tables created
- [x] IoT Thing Type created
- [x] IoT Policy created
- [x] IoT Rule created
- [x] Alexa Handler Lambda deployed
- [x] IoT Event Processor Lambda deployed
- [x] Timeout Checker Lambda deployed
- [x] EventBridge rule configured
- [ ] Alexa Skill configured (manual step)
- [ ] ESP32 device registered (manual step)
- [ ] System tested end-to-end

## 🎉 Success!

Your PillBuddy backend infrastructure is now deployed and ready for integration with ESP32 devices and Alexa!
