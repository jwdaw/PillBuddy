#!/usr/bin/env python3
"""
PillBuddy Backend Infrastructure - AWS CDK App
"""
import aws_cdk as cdk
from pillbuddy_stack import PillBuddyStack

app = cdk.App()

PillBuddyStack(
    app,
    "PillBuddyStack",
    description="PillBuddy Backend Infrastructure - DynamoDB tables and AWS resources",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    )
)

app.synth()
