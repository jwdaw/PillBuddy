"""
PillBuddy Timeout Checker Lambda Function

Periodically checks for bottles that have been removed from the holder
for more than 10 minutes and sends Alexa reminder notifications.

Triggered by EventBridge scheduled rule (every 5 minutes).

Environment Variables:
    PRESCRIPTIONS_TABLE: DynamoDB table name for prescriptions
    ALEXA_SKILL_ID: Alexa skill ID for notifications
"""

import json
import os
import time
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
PRESCRIPTIONS_TABLE = os.environ['PRESCRIPTIONS_TABLE']
ALEXA_SKILL_ID = os.environ.get('ALEXA_SKILL_ID', '')

# DynamoDB table
prescriptions_table = dynamodb.Table(PRESCRIPTIONS_TABLE)

# Constants
TIMEOUT_THRESHOLD_MS = 10 * 60 * 1000  # 10 minutes in milliseconds


def lambda_handler(event, context):
    """
    Main entry point for EventBridge scheduled trigger
    
    Scans all prescriptions for non-null removal_timestamp and checks
    if timeout threshold (10 minutes) has been exceeded.
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context object
        
    Returns:
        dict: Processing status with counts
    """
    try:
        print("Starting timeout check...")
        
        # Get current timestamp
        current_time = int(time.time() * 1000)
        
        # Scan prescriptions table for bottles that are out
        prescriptions = scan_removed_prescriptions()
        
        print(f"Found {len(prescriptions)} prescriptions with bottles removed")
        
        # Check each prescription for timeout
        notifications_sent = 0
        within_timeout = 0
        
        for prescription in prescriptions:
            result = check_bottle_return_timeout(prescription, current_time)
            
            if result['status'] == 'notification_sent':
                notifications_sent += 1
            elif result['status'] == 'within_timeout':
                within_timeout += 1
        
        print(f"Timeout check complete: {notifications_sent} notifications sent, "
              f"{within_timeout} within timeout")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'prescriptions_checked': len(prescriptions),
                'notifications_sent': notifications_sent,
                'within_timeout': within_timeout
            })
        }
        
    except Exception as e:
        print(f"Error in timeout checker: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def scan_removed_prescriptions():
    """
    Scan Prescriptions table for all entries with non-null removal_timestamp
    
    Returns:
        list: List of prescription items with bottles currently removed
    """
    try:
        # Scan table with filter for non-null removal_timestamp
        response = prescriptions_table.scan(
            FilterExpression='attribute_exists(removal_timestamp) AND removal_timestamp <> :null',
            ExpressionAttributeValues={
                ':null': None
            }
        )
        
        prescriptions = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = prescriptions_table.scan(
                FilterExpression='attribute_exists(removal_timestamp) AND removal_timestamp <> :null',
                ExpressionAttributeValues={
                    ':null': None
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            prescriptions.extend(response.get('Items', []))
        
        return prescriptions
        
    except ClientError as e:
        print(f"Error scanning prescriptions: {str(e)}")
        return []


def check_bottle_return_timeout(prescription, current_time):
    """
    Check if bottle return timeout has been exceeded for a prescription
    
    Implements Algorithm 3 from design document:
    1. Get current prescription state
    2. Check if bottle is still out (removal_timestamp not null)
    3. Calculate elapsed time
    4. If elapsed >= 10 minutes, send Alexa notification
    
    Args:
        prescription: Prescription item from DynamoDB
        current_time: Current Unix timestamp in milliseconds
        
    Returns:
        dict: Status with elapsed time
    """
    try:
        device_id = prescription['device_id']
        slot = int(prescription['slot'])
        removal_timestamp = prescription.get('removal_timestamp')
        prescription_name = prescription.get('prescription_name', 'medication')
        
        # Check if bottle is still out
        if removal_timestamp is None:
            return {
                'status': 'bottle_returned',
                'device_id': device_id,
                'slot': slot
            }
        
        # Calculate elapsed time
        elapsed_time = current_time - int(removal_timestamp)
        
        # Check if timeout threshold exceeded
        if elapsed_time >= TIMEOUT_THRESHOLD_MS:
            # Send Alexa notification
            message = (f"Reminder: Please return your {prescription_name} "
                      f"bottle to slot {slot} of your PillBuddy.")
            
            send_alexa_notification(device_id, message)
            
            print(f"Timeout notification sent for device {device_id}, slot {slot}, "
                  f"elapsed: {elapsed_time}ms")
            
            return {
                'status': 'notification_sent',
                'device_id': device_id,
                'slot': slot,
                'elapsed': elapsed_time
            }
        else:
            print(f"Within timeout for device {device_id}, slot {slot}, "
                  f"elapsed: {elapsed_time}ms")
            
            return {
                'status': 'within_timeout',
                'device_id': device_id,
                'slot': slot,
                'elapsed': elapsed_time
            }
        
    except Exception as e:
        print(f"Error checking timeout for prescription: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def send_alexa_notification(device_id, message):
    """
    Send proactive notification to user's Alexa device
    
    Note: Alexa proactive notifications require:
    1. Skill to have proactive events enabled
    2. User to grant notification permissions
    3. Proper authentication with Alexa Events API
    
    For hackathon, this is a placeholder that logs the notification.
    Full implementation would use Alexa Proactive Events API.
    
    Args:
        device_id: Device identifier
        message: Notification message text
    """
    try:
        print(f"Alexa notification for device {device_id}: {message}")
        
        # Placeholder for Alexa Proactive Events API
        # In production, this would:
        # 1. Get user's Alexa device ID from device_id mapping
        # 2. Obtain OAuth token for Alexa Events API
        # 3. POST to https://api.amazonalexa.com/v1/proactiveEvents
        # 4. Include skill ID, timestamp, event payload
        
        # Example production code:
        # alexa_client = boto3.client('alexa-for-business')
        # or use requests library to call Alexa Events API directly
        
    except Exception as e:
        print(f"Error sending Alexa notification: {str(e)}")
        # Non-critical error, don't raise
