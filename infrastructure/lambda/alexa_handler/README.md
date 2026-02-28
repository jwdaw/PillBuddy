# PillBuddy Alexa Skill Handler Lambda Function

This Lambda function processes Alexa voice commands for the PillBuddy smart pill bottle holder system.

## Features

- **LaunchRequest Handler**: Checks device online status and initiates setup flow
- **SetupSlotIntent Handler**: Configures prescriptions for each of the 3 slots with multi-turn conversation
- **QueryStatusIntent Handler**: Reports current pill counts for all configured slots
- **APL Visual Display**: Shows pill status on Echo Show devices with visual indicators
- **Built-in Intent Handlers**: Help, Stop, and Cancel intents
- **Error Handling**: Device offline detection, DynamoDB failures, IoT publish failures

## APL Visual Display Support

This skill supports visual display on Echo Show devices using Alexa Presentation Language (APL 1.6).

### Requirements

**IMPORTANT**: The APL interface must be enabled in the Alexa Developer Console for visual display to work.

To enable APL interface:

1. Go to Alexa Developer Console
2. Navigate to: Build > Interfaces
3. Find "Alexa Presentation Language"
4. Toggle the switch to ON
5. Click "Save Interfaces"

Without APL enabled, Echo Show devices will only receive voice responses.

### Visual Display Features

When APL is enabled and the user has an Echo Show device:

- Visual representation of all three pill bottle slots
- Prescription names displayed for each slot
- Pill counts with "pills remaining" labels
- Visual indicators for missing bottles (empty slots)
- Low pill warnings (red/amber) when count ≤ 7 pills
- Responsive layout for Echo Show 5, 8, and 10

### Backward Compatibility

The skill maintains full backward compatibility:

- Voice-only devices (Echo, Echo Dot) receive voice responses only
- APL rendering errors do not break voice responses
- Device capability detection is automatic

## Environment Variables

The Lambda function requires the following environment variables:

| Variable              | Description                           | Example Value                                |
| --------------------- | ------------------------------------- | -------------------------------------------- |
| `DEVICES_TABLE`       | DynamoDB table name for devices       | `PillBuddy_Devices`                          |
| `PRESCRIPTIONS_TABLE` | DynamoDB table name for prescriptions | `PillBuddy_Prescriptions`                    |
| `IOT_ENDPOINT`        | AWS IoT Core endpoint URL             | `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com` |
| `AWS_REGION`          | AWS region                            | `us-east-1`                                  |

## IAM Permissions Required

The Lambda execution role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Devices",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/PillBuddy_Prescriptions"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/pillbuddy/cmd/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Lambda Configuration

- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 10 seconds
- **Handler**: `lambda_function.lambda_handler`

## Deployment

### Option 1: AWS Console

1. Navigate to AWS Lambda console
2. Create a new function:
   - Name: `PillBuddy_AlexaHandler`
   - Runtime: Python 3.11
   - Architecture: x86_64
3. Upload the `lambda_function.py` file
4. Configure environment variables (see table above)
5. Attach IAM role with required permissions
6. Add Alexa Skills Kit trigger:
   - Skill ID: Your Alexa skill ID
   - Enable skill ID verification

### Option 2: AWS CLI

```bash
# Create deployment package
cd infrastructure/lambda/alexa_handler
zip function.zip lambda_function.py

# Create Lambda function
aws lambda create-function \
  --function-name PillBuddy_AlexaHandler \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/PillBuddyLambdaRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 10 \
  --memory-size 256 \
  --environment Variables="{DEVICES_TABLE=PillBuddy_Devices,PRESCRIPTIONS_TABLE=PillBuddy_Prescriptions,IOT_ENDPOINT=YOUR_IOT_ENDPOINT,AWS_REGION=us-east-1}"

# Add Alexa Skills Kit trigger
aws lambda add-permission \
  --function-name PillBuddy_AlexaHandler \
  --statement-id alexa-skill-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token YOUR_SKILL_ID
```

### Option 3: AWS CDK (Recommended)

Add to `infrastructure/pillbuddy_stack.py`:

```python
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
)

# Create Lambda execution role
alexa_lambda_role = iam.Role(
    self,
    "AlexaHandlerRole",
    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSLambdaBasicExecutionRole"
        )
    ]
)

# Grant DynamoDB permissions
self.devices_table.grant_read_write_data(alexa_lambda_role)
self.prescriptions_table.grant_read_write_data(alexa_lambda_role)

# Grant IoT publish permissions
alexa_lambda_role.add_to_policy(
    iam.PolicyStatement(
        actions=["iot:Publish"],
        resources=[f"arn:aws:iot:{self.region}:{self.account}:topic/pillbuddy/cmd/*"]
    )
)

# Create Lambda function
alexa_handler = lambda_.Function(
    self,
    "AlexaHandler",
    function_name="PillBuddy_AlexaHandler",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="lambda_function.lambda_handler",
    code=lambda_.Code.from_asset("lambda/alexa_handler"),
    timeout=Duration.seconds(10),
    memory_size=256,
    environment={
        "DEVICES_TABLE": self.devices_table.table_name,
        "PRESCRIPTIONS_TABLE": self.prescriptions_table.table_name,
        "IOT_ENDPOINT": "YOUR_IOT_ENDPOINT",  # Replace with actual endpoint
        "AWS_REGION": self.region
    },
    role=alexa_lambda_role
)

# Add Alexa Skills Kit trigger
alexa_handler.add_permission(
    "AlexaSkillPermission",
    principal=iam.ServicePrincipal("alexa-appkit.amazon.com"),
    action="lambda:InvokeFunction",
    event_source_token="YOUR_SKILL_ID"  # Replace with actual skill ID
)
```

## Getting IoT Endpoint

To get your AWS IoT Core endpoint:

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

This will return something like: `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com`

## Testing

### Test Event for LaunchRequest

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

### Test Event for SetupSlotIntent

```json
{
  "version": "1.0",
  "session": {
    "new": false,
    "sessionId": "amzn1.echo-api.session.test",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "user": {
      "userId": "esp32_001"
    },
    "attributes": {
      "device_id": "esp32_001",
      "setup_state": {
        "slots_configured": 0,
        "current_slot": 1
      }
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.test",
    "timestamp": "2024-01-01T00:00:00Z",
    "locale": "en-US",
    "intent": {
      "name": "SetupSlotIntent",
      "slots": {
        "prescriptionName": {
          "name": "prescriptionName",
          "value": "Aspirin"
        },
        "pillCount": {
          "name": "pillCount",
          "value": "30"
        },
        "hasRefills": {
          "name": "hasRefills",
          "value": "yes"
        }
      }
    }
  }
}
```

### Test Event for QueryStatusIntent

```json
{
  "version": "1.0",
  "session": {
    "new": false,
    "sessionId": "amzn1.echo-api.session.test",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "user": {
      "userId": "esp32_001"
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.test",
    "timestamp": "2024-01-01T00:00:00Z",
    "locale": "en-US",
    "intent": {
      "name": "QueryStatusIntent",
      "slots": {}
    }
  }
}
```

## Alexa Skill Configuration

After deploying the Lambda function, configure your Alexa skill:

1. **Invocation Name**: `pillbuddy`

2. **Interfaces** (REQUIRED for visual display):
   - Enable "Alexa Presentation Language" in Build > Interfaces
   - This allows Echo Show devices to display visual content

3. **Intents**:
   - `SetupSlotIntent` with slots:
     - `prescriptionName` (AMAZON.MedicationName or custom)
     - `pillCount` (AMAZON.NUMBER)
     - `hasRefills` (AMAZON.YesNo)
   - `QueryStatusIntent` (no slots)
   - `AMAZON.HelpIntent`
   - `AMAZON.StopIntent`
   - `AMAZON.CancelIntent`

4. **Sample Utterances**:
   - SetupSlotIntent:
     - "The prescription is {prescriptionName} with {pillCount} pills"
     - "{prescriptionName} has {pillCount} pills and {hasRefills} refills"
     - "Set up {prescriptionName}"
   - QueryStatusIntent:
     - "What's my status"
     - "How many pills do I have"
     - "Check my bottles"

5. **Endpoint**: Lambda ARN of this function

## Algorithm Implementation

This Lambda function implements **Algorithm 1 (processSetupSlotIntent)** from the design document:

1. Validates prescription details (name, count, refills)
2. Stores prescription in DynamoDB Prescriptions table
3. Publishes LED turn_on command to IoT Core
4. Manages multi-turn conversation state for 3 slots
5. Returns appropriate Alexa response with session management

## Error Handling

The function handles the following error scenarios:

1. **Device Offline**: Checks `last_seen` timestamp (> 5 minutes = offline)
2. **DynamoDB Write Failure**: Returns user-friendly error message
3. **IoT Publish Failure**: Logs error but continues (LED is non-critical)
4. **Invalid Slot Values**: Prompts user to provide valid input
5. **Missing Prescription**: Handles gracefully in status queries

## Monitoring

Monitor the function using CloudWatch Logs:

```bash
aws logs tail /aws/lambda/PillBuddy_AlexaHandler --follow
```

Key metrics to monitor:

- Invocation count
- Error rate
- Duration
- DynamoDB throttling
- IoT publish failures

## Notes

- Device ID is extracted from Alexa user ID (for hackathon, defaults to `esp32_001`)
- In production, implement proper account linking to map Alexa users to devices
- Session attributes maintain state across multi-turn conversations
- LED commands are published with QoS 1 for reliable delivery
- All timestamps use Unix milliseconds for consistency with IoT events
