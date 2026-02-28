"""
PillBuddy Backend Stack - DynamoDB Tables and Infrastructure
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_iot as iot,
    aws_iam as iam,
    aws_lambda as lambda_,
)
from constructs import Construct


class PillBuddyStack(Stack):
    """
    CDK Stack for PillBuddy Backend Infrastructure
    
    Creates three DynamoDB tables:
    1. Devices - Stores device connection status and slot states
    2. Prescriptions - Stores prescription data for each device slot
    3. Events - Stores time-series events from ESP32 devices
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Table 1: Devices Table
        self.devices_table = dynamodb.Table(
            self,
            "DevicesTable",
            table_name="PillBuddy_Devices",
            partition_key=dynamodb.Attribute(
                name="device_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY,  # For hackathon - use RETAIN in production
        )

        # Table 2: Prescriptions Table
        self.prescriptions_table = dynamodb.Table(
            self,
            "PrescriptionsTable",
            table_name="PillBuddy_Prescriptions",
            partition_key=dynamodb.Attribute(
                name="device_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="slot",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY,  # For hackathon - use RETAIN in production
        )

        # Table 3: Events Table with TTL
        self.events_table = dynamodb.Table(
            self,
            "EventsTable",
            table_name="PillBuddy_Events",
            partition_key=dynamodb.Attribute(
                name="device_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=10,  # Higher write capacity for event logging
            time_to_live_attribute="ttl",  # Enable TTL for auto-deletion after 30 days
            removal_policy=RemovalPolicy.DESTROY,  # For hackathon - use RETAIN in production
        )

        # Export table names for use by Lambda functions
        self.export_value(
            self.devices_table.table_name,
            name="PillBuddyDevicesTableName"
        )
        self.export_value(
            self.prescriptions_table.table_name,
            name="PillBuddyPrescriptionsTableName"
        )
        self.export_value(
            self.events_table.table_name,
            name="PillBuddyEventsTableName"
        )

        # IoT Thing Type for PillBuddy devices
        # Note: CDK L2 constructs for IoT Thing Types are limited, using CfnThingType
        self.thing_type = iot.CfnThingType(
            self,
            "PillBuddyDeviceThingType",
            thing_type_name="PillBuddyDevice",
            thing_type_properties=iot.CfnThingType.ThingTypePropertiesProperty(
                thing_type_description="PillBuddy ESP32 smart pill bottle holder device"
            )
        )

        # IoT Policy for PillBuddy devices
        self.iot_policy = iot.CfnPolicy(
            self,
            "PillBuddyDevicePolicy",
            policy_name="PillBuddyDevicePolicy",
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iot:Connect",
                        "Resource": f"arn:aws:iot:{self.region}:{self.account}:client/pillbuddy_*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Publish",
                        "Resource": f"arn:aws:iot:{self.region}:{self.account}:topic/pillbuddy/events/*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Subscribe",
                        "Resource": f"arn:aws:iot:{self.region}:{self.account}:topicfilter/pillbuddy/cmd/*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Receive",
                        "Resource": f"arn:aws:iot:{self.region}:{self.account}:topic/pillbuddy/cmd/*"
                    }
                ]
            }
        )

        # IoT Rule IAM Role - allows IoT to invoke Lambda
        self.iot_rule_role = iam.Role(
            self,
            "IoTRuleRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description="Role for IoT Rule to invoke Lambda function"
        )

        # Alexa Skill Handler Lambda Function
        # Create Lambda execution role
        alexa_lambda_role = iam.Role(
            self,
            "AlexaHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            description="Execution role for Alexa Skill Handler Lambda"
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

        # Get IoT endpoint (will be set via environment variable or parameter)
        # To get your IoT endpoint, run: aws iot describe-endpoint --endpoint-type iot:Data-ATS
        iot_endpoint = self.node.try_get_context("iot_endpoint") or "REPLACE_WITH_IOT_ENDPOINT"

        # Create Alexa Handler Lambda function
        self.alexa_handler = lambda_.Function(
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
                "IOT_ENDPOINT": iot_endpoint
            },
            role=alexa_lambda_role,
            description="Alexa Skill Handler for PillBuddy voice commands"
        )

        # Export Lambda ARN for Alexa Skill configuration
        self.export_value(
            self.alexa_handler.function_arn,
            name="PillBuddyAlexaHandlerArn"
        )

        # Note: Alexa Skills Kit trigger must be added manually or via Alexa Developer Console
        # The trigger requires your Alexa Skill ID which is created separately
        # To add the trigger via CLI after creating your skill:
        # aws lambda add-permission \
        #   --function-name PillBuddy_AlexaHandler \
        #   --statement-id alexa-skill-trigger \
        #   --action lambda:InvokeFunction \
        #   --principal alexa-appkit.amazon.com \
        #   --event-source-token YOUR_SKILL_ID

        # IoT Rule will be created when Lambda function is added in task 5
        # See infrastructure/iot_rule_config.py for the rule configuration
        # The rule forwards messages from 'pillbuddy/events/+' to the IoT Event Processor Lambda
        # 
        # To complete in task 5:
        # from infrastructure.iot_rule_config import create_iot_event_rule
        # self.iot_rule = create_iot_event_rule(self, iot_event_processor_lambda, self.iot_rule_role)
        
        # Export IoT resources for use by Lambda functions and documentation
        self.export_value(
            self.iot_policy.policy_name,
            name="PillBuddyIoTPolicyName"
        )
        self.export_value(
            self.thing_type.thing_type_name,
            name="PillBuddyThingTypeName"
        )

