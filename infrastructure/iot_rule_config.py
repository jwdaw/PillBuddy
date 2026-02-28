"""
IoT Rule Configuration for PillBuddy

This module contains the IoT Rule setup that forwards device events to Lambda.
The rule will be integrated into the main stack when the Lambda function is created in task 5.

IoT Rule Specification:
- Rule Name: PillBuddyEventRule
- SQL: SELECT * FROM 'pillbuddy/events/+'
- Action: Forward to IoT Event Processor Lambda
- Description: Forward ESP32 device events to Lambda for processing
"""

from aws_cdk import (
    aws_iot as iot,
    aws_lambda as lambda_,
    aws_iam as iam,
)
from constructs import Construct


def create_iot_event_rule(
    scope: Construct,
    iot_event_processor_lambda: lambda_.Function,
    iot_rule_role: iam.Role
) -> iot.CfnTopicRule:
    """
    Create IoT Rule to forward device events to Lambda
    
    This function should be called from the main stack after the
    IoT Event Processor Lambda is created (task 5).
    
    Args:
        scope: CDK construct scope
        iot_event_processor_lambda: Lambda function to invoke
        iot_rule_role: IAM role for IoT Rule
        
    Returns:
        IoT Topic Rule construct
    """
    
    # Grant IoT Rule permission to invoke Lambda
    iot_rule_role.add_to_policy(
        iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[iot_event_processor_lambda.function_arn]
        )
    )
    
    # Create IoT Rule
    iot_rule = iot.CfnTopicRule(
        scope,
        "PillBuddyEventRule",
        rule_name="PillBuddyEventRule",
        topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
            sql="SELECT * FROM 'pillbuddy/events/+'",
            description="Forward ESP32 device events to Lambda for processing",
            actions=[
                iot.CfnTopicRule.ActionProperty(
                    lambda_=iot.CfnTopicRule.LambdaActionProperty(
                        function_arn=iot_event_processor_lambda.function_arn
                    )
                )
            ],
            aws_iot_sql_version="2016-03-23",
            rule_disabled=False
        )
    )
    
    # Grant IoT service permission to invoke the Lambda
    iot_event_processor_lambda.add_permission(
        "AllowIoTInvoke",
        principal=iam.ServicePrincipal("iot.amazonaws.com"),
        source_arn=iot_rule.attr_arn
    )
    
    return iot_rule
