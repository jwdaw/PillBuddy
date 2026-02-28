# AWS IoT Core Configuration for PillBuddy

This document provides complete setup instructions for AWS IoT Core resources required by the PillBuddy system.

## Overview

The PillBuddy system uses AWS IoT Core for bidirectional MQTT communication between ESP32 devices and the AWS backend. Devices publish events to AWS and subscribe to command topics to receive LED control instructions.

## Prerequisites

Before setting up IoT Core:

1. AWS account with appropriate permissions
2. AWS CLI installed and configured
3. DynamoDB tables deployed (PillBuddy_Devices, PillBuddy_Prescriptions, PillBuddy_Events)
4. Lambda functions deployed (especially IoT Event Processor)

## Quick Start

For rapid deployment, follow these steps in order:

1. [Create IoT Thing Type](#step-1-create-iot-thing-type)
2. [Create IoT Policy](#step-2-create-iot-policy)
3. [Create IoT Rule](#step-3-create-iot-rule)
4. [Register ESP32 Device](#step-4-register-esp32-device)
5. [Test MQTT Communication](#step-5-test-mqtt-communication)

## Step-by-Step Setup

### Step 1: Create IoT Thing Type

**Thing Type Name**: `PillBuddyDevice`

**Purpose**: Defines the type for all PillBuddy IoT Things. Each physical ESP32 device will be registered as a Thing of this type.

#### Using AWS CLI

```bash
aws iot create-thing-type \
  --thing-type-name PillBuddyDevice \
  --thing-type-properties "thingTypeDescription=PillBuddy ESP32 smart pill bottle holder device"
```

#### Using AWS Console

1. Go to [AWS IoT Core Console](https://console.aws.amazon.com/iot/)
2. In the left sidebar, click "Manage" → "Types"
3. Click "Create"
4. Thing type name: `PillBuddyDevice`
5. Description: "PillBuddy ESP32 smart pill bottle holder device"
6. Click "Create thing type"

#### Verification

```bash
aws iot describe-thing-type --thing-type-name PillBuddyDevice
```

Expected output:

```json
{
  "thingTypeName": "PillBuddyDevice",
  "thingTypeProperties": {
    "thingTypeDescription": "PillBuddy ESP32 smart pill bottle holder device"
  }
}
```

---

### Step 2: Create IoT Policy

**Policy Name**: `PillBuddyDevicePolicy`

**Purpose**: Defines permissions for PillBuddy devices to connect and communicate via MQTT

#### Permissions Summary

| Action          | Resource                      | Description                                                         |
| --------------- | ----------------------------- | ------------------------------------------------------------------- |
| `iot:Connect`   | `client/pillbuddy_*`          | Allow devices with client ID starting with "pillbuddy\_" to connect |
| `iot:Publish`   | `topic/pillbuddy/events/*`    | Allow publishing to device event topics                             |
| `iot:Subscribe` | `topicfilter/pillbuddy/cmd/*` | Allow subscribing to device command topics                          |
| `iot:Receive`   | `topic/pillbuddy/cmd/*`       | Allow receiving messages on command topics                          |

#### Using AWS CLI

First, create a policy document file `pillbuddy-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:*:*:client/pillbuddy_*"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:*:*:topic/pillbuddy/events/*"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Subscribe",
      "Resource": "arn:aws:iot:*:*:topicfilter/pillbuddy/cmd/*"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Receive",
      "Resource": "arn:aws:iot:*:*:topic/pillbuddy/cmd/*"
    }
  ]
}
```

Then create the policy:

```bash
aws iot create-policy \
  --policy-name PillBuddyDevicePolicy \
  --policy-document file://pillbuddy-policy.json
```

#### Using AWS Console

1. Go to [AWS IoT Core Console](https://console.aws.amazon.com/iot/)
2. In the left sidebar, click "Secure" → "Policies"
3. Click "Create policy"
4. Policy name: `PillBuddyDevicePolicy`
5. Add the following policy statements:

**Statement 1 - Connect**:

- Policy effect: Allow
- Policy action: `iot:Connect`
- Policy resource: `arn:aws:iot:*:*:client/pillbuddy_*`

**Statement 2 - Publish**:

- Policy effect: Allow
- Policy action: `iot:Publish`
- Policy resource: `arn:aws:iot:*:*:topic/pillbuddy/events/*`

**Statement 3 - Subscribe**:

- Policy effect: Allow
- Policy action: `iot:Subscribe`
- Policy resource: `arn:aws:iot:*:*:topicfilter/pillbuddy/cmd/*`

**Statement 4 - Receive**:

- Policy effect: Allow
- Policy action: `iot:Receive`
- Policy resource: `arn:aws:iot:*:*:topic/pillbuddy/cmd/*`

6. Click "Create"

#### Verification

```bash
aws iot get-policy --policy-name PillBuddyDevicePolicy
```

---

### Step 3: Create IoT Rule

**Rule Name**: `PillBuddyEventRule`

**Purpose**: Forward all messages from device event topics to the IoT Event Processor Lambda function

**SQL Statement**: `SELECT * FROM 'pillbuddy/events/+'`

#### Prerequisites

Ensure the IoT Event Processor Lambda function exists:

```bash
aws lambda get-function --function-name PillBuddy_IoTEventProcessor
```

#### Using AWS CLI

First, get your Lambda function ARN:

```bash
LAMBDA_ARN=$(aws lambda get-function \
  --function-name PillBuddy_IoTEventProcessor \
  --query 'Configuration.FunctionArn' \
  --output text)

echo "Lambda ARN: $LAMBDA_ARN"
```

Create a rule payload file `iot-rule.json`:

```json
{
  "sql": "SELECT * FROM 'pillbuddy/events/+'",
  "description": "Forward PillBuddy device events to Lambda processor",
  "actions": [
    {
      "lambda": {
        "functionArn": "REPLACE_WITH_LAMBDA_ARN"
      }
    }
  ],
  "ruleDisabled": false,
  "awsIotSqlVersion": "2016-03-23"
}
```

Replace the Lambda ARN and create the rule:

```bash
# Replace ARN in the file
sed -i "s|REPLACE_WITH_LAMBDA_ARN|$LAMBDA_ARN|g" iot-rule.json

# Create the rule
aws iot create-topic-rule \
  --rule-name PillBuddyEventRule \
  --topic-rule-payload file://iot-rule.json
```

Grant IoT Core permission to invoke the Lambda:

```bash
aws lambda add-permission \
  --function-name PillBuddy_IoTEventProcessor \
  --statement-id AllowIoTCoreInvoke \
  --action lambda:InvokeFunction \
  --principal iot.amazonaws.com \
  --source-arn arn:aws:iot:$(aws configure get region):$(aws sts get-caller-identity --query Account --output text):rule/PillBuddyEventRule
```

#### Using AWS Console

1. Go to [AWS IoT Core Console](https://console.aws.amazon.com/iot/)
2. In the left sidebar, click "Act" → "Rules"
3. Click "Create"
4. Rule name: `PillBuddyEventRule`
5. Description: "Forward PillBuddy device events to Lambda processor"
6. Rule query statement: `SELECT * FROM 'pillbuddy/events/+'`
7. Click "Add action"
8. Select "Send a message to a Lambda function"
9. Click "Configure action"
10. Select function: `PillBuddy_IoTEventProcessor`
11. Click "Add action"
12. Click "Create rule"

#### Verification

```bash
# Check rule exists
aws iot get-topic-rule --rule-name PillBuddyEventRule

# Verify Lambda permission
aws lambda get-policy --function-name PillBuddy_IoTEventProcessor
```

---

### Step 4: Register ESP32 Device

This section shows how to register a new ESP32 device with AWS IoT Core.

#### 4.1: Create IoT Thing

Replace `{device_id}` with your device identifier (e.g., `esp32_001`):

```bash
DEVICE_ID="esp32_001"

aws iot create-thing \
  --thing-name pillbuddy_${DEVICE_ID} \
  --thing-type-name PillBuddyDevice \
  --attribute-payload "{\"attributes\":{\"device_id\":\"${DEVICE_ID}\",\"firmware_version\":\"1.0.0\",\"hardware_version\":\"1.0\"}}"
```

#### 4.2: Create Device Certificates

```bash
# Create certificates and keys
aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile ${DEVICE_ID}.cert.pem \
  --public-key-outfile ${DEVICE_ID}.public.key \
  --private-key-outfile ${DEVICE_ID}.private.key \
  --output json > ${DEVICE_ID}-cert-output.json

# Extract certificate ARN
CERT_ARN=$(cat ${DEVICE_ID}-cert-output.json | jq -r '.certificateArn')
echo "Certificate ARN: $CERT_ARN"
```

**Important**: Save the certificate ARN - you'll need it for the next steps.

#### 4.3: Attach Policy to Certificate

```bash
aws iot attach-policy \
  --policy-name PillBuddyDevicePolicy \
  --target $CERT_ARN
```

#### 4.4: Attach Certificate to Thing

```bash
aws iot attach-thing-principal \
  --thing-name pillbuddy_${DEVICE_ID} \
  --principal $CERT_ARN
```

#### 4.5: Download Root CA Certificate

```bash
curl https://www.amazontrust.com/repository/AmazonRootCA1.pem -o AmazonRootCA1.pem
```

#### 4.6: Get IoT Endpoint

```bash
IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)
echo "IoT Endpoint: $IOT_ENDPOINT"
```

#### 4.7: Files for ESP32

You should now have these files to flash to your ESP32:

- `{device_id}.cert.pem` - Device certificate
- `{device_id}.private.key` - Private key
- `AmazonRootCA1.pem` - Root CA certificate
- IoT Endpoint URL (from step 4.6)

#### 4.8: ESP32 Configuration

Configure your ESP32 with:

- **Client ID**: `pillbuddy_{device_id}` (e.g., `pillbuddy_esp32_001`)
- **IoT Endpoint**: From step 4.6
- **Publish Topic**: `pillbuddy/events/{device_id}`
- **Subscribe Topic**: `pillbuddy/cmd/{device_id}`
- **Certificates**: Files from step 4.7

#### 4.9: Initialize Device in DynamoDB

Create the device record in DynamoDB:

```bash
aws dynamodb put-item \
  --table-name PillBuddy_Devices \
  --item "{
    \"device_id\": {\"S\": \"${DEVICE_ID}\"},
    \"online\": {\"BOOL\": false},
    \"last_seen\": {\"N\": \"0\"},
    \"created_at\": {\"N\": \"$(date +%s)000\"},
    \"slots\": {\"M\": {
      \"1\": {\"M\": {\"in_holder\": {\"BOOL\": false}, \"last_state_change\": {\"N\": \"0\"}}},
      \"2\": {\"M\": {\"in_holder\": {\"BOOL\": false}, \"last_state_change\": {\"N\": \"0\"}}},
      \"3\": {\"M\": {\"in_holder\": {\"BOOL\": false}, \"last_state_change\": {\"N\": \"0\"}}}
    }}
  }"
```

---

### Step 5: Test MQTT Communication

#### 5.1: Test Device Publishing (Simulate ESP32 Event)

```bash
DEVICE_ID="esp32_001"

aws iot-data publish \
  --topic pillbuddy/events/${DEVICE_ID} \
  --payload "{\"event_type\":\"slot_state_changed\",\"slot\":1,\"state\":\"not_in_holder\",\"in_holder\":false,\"sensor_level\":0,\"ts_ms\":$(date +%s)000,\"sequence\":1}" \
  --cli-binary-format raw-in-base64-out
```

Check Lambda logs to verify event was processed:

```bash
aws logs tail /aws/lambda/PillBuddy_IoTEventProcessor --follow
```

#### 5.2: Test Command Publishing (Simulate Lambda)

```bash
aws iot-data publish \
  --topic pillbuddy/cmd/${DEVICE_ID} \
  --payload '{"action":"turn_on","slot":1}' \
  --cli-binary-format raw-in-base64-out
```

#### 5.3: Monitor MQTT Topics

Use the AWS IoT Core Test client:

1. Go to [AWS IoT Core Console](https://console.aws.amazon.com/iot/)
2. Click "Test" in the left sidebar
3. Subscribe to topic: `pillbuddy/events/+`
4. Subscribe to topic: `pillbuddy/cmd/+`
5. Publish test messages to verify bidirectional communication

---

## MQTT Topics Reference

### Device Events Topic (ESP32 → AWS)

**Topic Pattern**: `pillbuddy/events/{device_id}`

**Direction**: Device publishes, AWS subscribes (via IoT Rule)

**Message Format**:

```json
{
  "event_type": "slot_state_changed",
  "slot": 2,
  "state": "not_in_holder",
  "in_holder": false,
  "sensor_level": 0,
  "ts_ms": 1700000000000,
  "sequence": 120
}
```

**Field Descriptions**:

- `event_type`: Always "slot_state_changed" for this version
- `slot`: Slot number (1, 2, or 3)
- `state`: "in_holder" or "not_in_holder"
- `in_holder`: Boolean state (true/false)
- `sensor_level`: Raw sensor reading (0=LOW, 1=HIGH)
- `ts_ms`: Unix timestamp in milliseconds
- `sequence`: Monotonically increasing sequence number for deduplication

### Device Commands Topic (AWS → ESP32)

**Topic Pattern**: `pillbuddy/cmd/{device_id}`

**Direction**: AWS publishes, device subscribes

**Message Format**:

```json
{
  "action": "turn_on",
  "slot": 2
}
```

**Field Descriptions**:

- `action`: Command action ("turn_on" or "turn_off")
- `slot`: Target slot number (1, 2, or 3)

**Actions**:

- `turn_on`: Turn on LED for the specified slot
- `turn_off`: Turn off LED for the specified slot

---

## Automation Script

For convenience, here's a complete script to set up a new device:

```bash
#!/bin/bash

# PillBuddy IoT Device Setup Script

set -e

# Configuration
DEVICE_ID=${1:-"esp32_001"}
REGION=$(aws configure get region)
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo "Setting up PillBuddy device: $DEVICE_ID"
echo "Region: $REGION"
echo "Account: $ACCOUNT"

# 1. Create Thing
echo "Creating IoT Thing..."
aws iot create-thing \
  --thing-name pillbuddy_${DEVICE_ID} \
  --thing-type-name PillBuddyDevice \
  --attribute-payload "{\"attributes\":{\"device_id\":\"${DEVICE_ID}\",\"firmware_version\":\"1.0.0\",\"hardware_version\":\"1.0\"}}"

# 2. Create Certificates
echo "Creating certificates..."
aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile ${DEVICE_ID}.cert.pem \
  --public-key-outfile ${DEVICE_ID}.public.key \
  --private-key-outfile ${DEVICE_ID}.private.key \
  --output json > ${DEVICE_ID}-cert-output.json

CERT_ARN=$(cat ${DEVICE_ID}-cert-output.json | jq -r '.certificateArn')
echo "Certificate ARN: $CERT_ARN"

# 3. Attach Policy
echo "Attaching policy to certificate..."
aws iot attach-policy \
  --policy-name PillBuddyDevicePolicy \
  --target $CERT_ARN

# 4. Attach Certificate to Thing
echo "Attaching certificate to thing..."
aws iot attach-thing-principal \
  --thing-name pillbuddy_${DEVICE_ID} \
  --principal $CERT_ARN

# 5. Download Root CA
echo "Downloading Root CA certificate..."
curl -s https://www.amazontrust.com/repository/AmazonRootCA1.pem -o AmazonRootCA1.pem

# 6. Get IoT Endpoint
IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)

# 7. Initialize DynamoDB
echo "Creating device record in DynamoDB..."
aws dynamodb put-item \
  --table-name PillBuddy_Devices \
  --item "{
    \"device_id\": {\"S\": \"${DEVICE_ID}\"},
    \"online\": {\"BOOL\": false},
    \"last_seen\": {\"N\": \"0\"},
    \"created_at\": {\"N\": \"$(date +%s)000\"},
    \"slots\": {\"M\": {
      \"1\": {\"M\": {\"in_holder\": {\"BOOL\": false}, \"last_state_change\": {\"N\": \"0\"}}},
      \"2\": {\"M\": {\"in_holder\": {\"BOOL\": false}, \"last_state_change\": {\"N\": \"0\"}}},
      \"3\": {\"M\": {\"in_holder\": {\"BOOL\": false}, \"last_state_change\": {\"N\": \"0\"}}}
    }}
  }"

# 8. Create ESP32 config file
echo "Creating ESP32 configuration file..."
cat > ${DEVICE_ID}-config.txt <<EOF
PillBuddy ESP32 Configuration
=============================

Device ID: ${DEVICE_ID}
Client ID: pillbuddy_${DEVICE_ID}
IoT Endpoint: ${IOT_ENDPOINT}

MQTT Topics:
- Publish to: pillbuddy/events/${DEVICE_ID}
- Subscribe to: pillbuddy/cmd/${DEVICE_ID}

Certificate Files:
- Device Certificate: ${DEVICE_ID}.cert.pem
- Private Key: ${DEVICE_ID}.private.key
- Root CA: AmazonRootCA1.pem

Flash these files to your ESP32 and configure the MQTT client accordingly.
EOF

echo ""
echo "✓ Setup complete!"
echo ""
echo "Files created:"
echo "  - ${DEVICE_ID}.cert.pem"
echo "  - ${DEVICE_ID}.private.key"
echo "  - ${DEVICE_ID}.public.key"
echo "  - AmazonRootCA1.pem"
echo "  - ${DEVICE_ID}-config.txt"
echo ""
echo "Next steps:"
echo "  1. Flash the certificate files to your ESP32"
echo "  2. Configure ESP32 with settings from ${DEVICE_ID}-config.txt"
echo "  3. Test MQTT communication"
```

Save this as `setup-device.sh` and run:

```bash
chmod +x setup-device.sh
./setup-device.sh esp32_001
```

---

## Troubleshooting

### Device Cannot Connect

**Symptoms**: ESP32 cannot establish MQTT connection

**Checks**:

1. Verify certificates are correctly installed on ESP32
2. Check that certificate is attached to the policy:
   ```bash
   aws iot list-attached-policies --target CERT_ARN
   ```
3. Verify client ID matches pattern `pillbuddy_*`
4. Check IoT endpoint URL is correct (no `https://` prefix)
5. Ensure device time is synchronized (certificates have validity periods)

### Messages Not Received by Lambda

**Symptoms**: Events published but Lambda not triggered

**Checks**:

1. Verify IoT Rule is enabled:
   ```bash
   aws iot get-topic-rule --rule-name PillBuddyEventRule
   ```
2. Check CloudWatch Logs for IoT Rule errors:
   ```bash
   aws logs tail /aws/iot/rules/PillBuddyEventRule --follow
   ```
3. Verify Lambda function has correct permissions
4. Test rule with AWS IoT Core test client

### Commands Not Received by Device

**Symptoms**: Lambda publishes commands but ESP32 doesn't receive them

**Checks**:

1. Verify device is subscribed to correct topic: `pillbuddy/cmd/{device_id}`
2. Check device connection status in AWS IoT console
3. Test publishing to topic using AWS CLI
4. Verify QoS settings (recommend QoS 1 for commands)
5. Check ESP32 logs for subscription confirmation

### Certificate Errors

**Symptoms**: Authentication failures, certificate validation errors

**Checks**:

1. Verify certificate is active:
   ```bash
   aws iot describe-certificate --certificate-id CERT_ID
   ```
2. Check certificate is attached to thing:
   ```bash
   aws iot list-thing-principals --thing-name pillbuddy_DEVICE_ID
   ```
3. Ensure Root CA certificate is correct version (AmazonRootCA1)
4. Verify certificate hasn't expired

---

## Security Considerations

### For Hackathon (Current Setup)

- Single shared policy for all devices
- Devices can publish to any event topic
- Devices can subscribe to any command topic
- No device-specific restrictions

### For Production (Recommended Improvements)

1. **Device-Specific Policies**: Create individual policies per device

2. **Topic Restrictions**: Limit each device to its own topics only

   ```json
   {
     "Effect": "Allow",
     "Action": "iot:Publish",
     "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/pillbuddy/events/${iot:Connection.Thing.ThingName}"
   }
   ```

3. **Certificate Rotation**: Implement automatic certificate rotation

4. **Device Provisioning**: Use AWS IoT Fleet Provisioning for automated setup

5. **Monitoring**: Enable CloudWatch metrics and alarms for device connectivity

6. **Just-in-Time Registration (JITR)**: Automate device registration on first connection

---

## Monitoring and Maintenance

### CloudWatch Metrics

Monitor these IoT Core metrics:

```bash
# Connection attempts
aws cloudwatch get-metric-statistics \
  --namespace AWS/IoT \
  --metric-name Connect.Success \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Message publish count
aws cloudwatch get-metric-statistics \
  --namespace AWS/IoT \
  --metric-name PublishIn.Success \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Device Status

Check device connection status:

```bash
# List all things
aws iot list-things --thing-type-name PillBuddyDevice

# Get thing details
aws iot describe-thing --thing-name pillbuddy_esp32_001

# Check device connectivity
aws iot-data get-thing-shadow --thing-name pillbuddy_esp32_001
```

### Certificate Management

List and manage certificates:

```bash
# List all certificates
aws iot list-certificates

# Deactivate a certificate
aws iot update-certificate --certificate-id CERT_ID --new-status INACTIVE

# Delete a certificate (must be inactive and detached first)
aws iot delete-certificate --certificate-id CERT_ID
```

---

## Cost Estimation

For hackathon usage with 1-3 devices:

- **Connectivity**: $0.08 per million minutes = ~$0.01/month per device
- **Messaging**: $1.00 per million messages = ~$0.10/month (assuming 100k messages)
- **Rules Engine**: $0.15 per million rules triggered = ~$0.02/month

**Total: ~$0.13/month** for hackathon scale

---

## References

- [AWS IoT Core Documentation](https://docs.aws.amazon.com/iot/)
- [MQTT Protocol Specification](https://mqtt.org/)
- [AWS IoT Device SDK for Embedded C](https://github.com/aws/aws-iot-device-sdk-embedded-C)
- [AWS IoT Core Limits](https://docs.aws.amazon.com/general/latest/gr/iot-core.html)
- [IoT Core Security Best Practices](https://docs.aws.amazon.com/iot/latest/developerguide/security-best-practices.html)
