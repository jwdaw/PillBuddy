"""
PillBuddy IoT Event Processor Lambda Function

Processes IoT Core events from ESP32 devices, updates device state,
manages pill counts, and sends Alexa notifications.

Environment Variables:
    DEVICES_TABLE: DynamoDB table name for devices
    PRESCRIPTIONS_TABLE: DynamoDB table name for prescriptions
    EVENTS_TABLE: DynamoDB table name for events
    IOT_ENDPOINT: AWS IoT Core endpoint URL
    ALEXA_SKILL_ID: Alexa skill ID for notifications
    AWS_REGION: AWS region
"""

import json
import os
import time
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
iot_client = boto3.client('iot-data')
events_client = boto3.client('events')

# Environment variables
DEVICES_TABLE = os.environ['DEVICES_TABLE']
PRESCRIPTIONS_TABLE = os.environ['PRESCRIPTIONS_TABLE']
EVENTS_TABLE = os.environ['EVENTS_TABLE']
IOT_ENDPOINT = os.environ['IOT_ENDPOINT']
ALEXA_SKILL_ID = os.environ.get('ALEXA_SKILL_ID', '')
# AWS_REGION is automatically available in Lambda environment

# DynamoDB tables
devices_table = dynamodb.Table(DEVICES_TABLE)
prescriptions_table = dynamodb.Table(PRESCRIPTIONS_TABLE)
events_table = dynamodb.Table(EVENTS_TABLE)

# Constants
REFILL_THRESHOLD = 5
TIMEOUT_MINUTES = 10
TTL_DAYS = 30


def lambda_handler(event, context):
    """
    Main entry point for IoT Core events
    
    Args:
        event: IoT message from pillbuddy/events/{device_id}
               Can be either:
               1. Raw ESP32 format (3 fields): event_type, slot, in_holder
               2. IoT Rule transformed format (with device_id, ts_ms, etc.)
        context: Lambda context object
        
    Returns:
        dict: Processing status
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Extract or derive required fields
        # IoT Rule adds these fields, but handle raw ESP32 format too
        device_id = event.get('device_id')
        event_type = event.get('event_type')
        
        if not device_id:
            print("Error: device_id not found in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'device_id required'})
            }
        
        if event_type == 'slot_state_changed':
            return handle_slot_state_changed(event)
        else:
            print(f"Unknown event type: {event_type}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown event type: {event_type}'})
            }
            
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_slot_state_changed(event):
    """
    Process slot state change event
    
    Implements Algorithm 2 from design document:
    1. Log event to Events table with TTL
    2. Update device slot state and last_seen
    3. Get prescription for the slot
    4. If bottle removed: decrement pill count, set removal_timestamp, check refill reminder
    5. If bottle returned: clear removal_timestamp, turn off LED
    
    Args:
        event: IoT event with required fields: event_type, slot, in_holder
               Optional fields added by IoT Rule: device_id, ts_ms, sequence, state, sensor_level
        
    Returns:
        dict: Processing status
    """
    # Required fields from ESP32
    device_id = event['device_id']
    slot = int(event['slot'])
    in_holder = event['in_holder']
    
    # Optional fields - use defaults if not provided by IoT Rule
    timestamp = event.get('ts_ms', int(time.time() * 1000))
    sequence = event.get('sequence', 0)
    state = event.get('state', 'in_holder' if in_holder else 'not_in_holder')
    sensor_level = event.get('sensor_level', 1 if in_holder else 0)
    
    # Validate slot number
    if slot not in [1, 2, 3]:
        print(f"Invalid slot number: {slot}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid slot number'})
        }
    
    # Check for duplicate events (deduplication)
    # Skip deduplication if sequence is 0 (ESP32 doesn't provide sequence numbers)
    if sequence > 0 and is_duplicate_event(device_id, sequence):
        print(f"Duplicate event detected for device {device_id}, sequence {sequence}")
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'duplicate', 'message': 'Event already processed'})
        }
    
    # 1. Log event to Events table with TTL
    log_event(device_id, timestamp, slot, state, in_holder, sensor_level, sequence)
    
    # 2. Update device slot state and last_seen
    update_device_state(device_id, slot, in_holder, timestamp)
    
    # 3. Get prescription for this slot
    prescription = get_prescription(device_id, slot)
    
    if not prescription:
        print(f"No prescription configured for device {device_id}, slot {slot}")
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'success', 'message': 'No prescription configured'})
        }
    
    # 4. Process bottle removal or return
    if not in_holder:
        # Bottle removed - decrement pill count
        process_bottle_removal(device_id, slot, prescription, timestamp)
    else:
        # Bottle returned - clear removal timestamp and turn off LED
        process_bottle_return(device_id, slot, prescription, timestamp)
    
    # Update last processed sequence (only if sequence > 0)
    if sequence > 0:
        update_last_sequence(device_id, sequence)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'success', 'message': 'Event processed'})
    }


def is_duplicate_event(device_id, sequence):
    """
    Check if event has already been processed based on sequence number
    
    Args:
        device_id: Device identifier
        sequence: Event sequence number
        
    Returns:
        bool: True if duplicate, False otherwise
    """
    try:
        response = devices_table.get_item(
            Key={'device_id': device_id},
            ProjectionExpression='last_sequence'
        )
        
        if 'Item' in response:
            last_sequence = response['Item'].get('last_sequence', -1)
            return sequence <= last_sequence
        
        return False
        
    except ClientError as e:
        print(f"Error checking duplicate: {str(e)}")
        return False


def update_last_sequence(device_id, sequence):
    """
    Update the last processed sequence number for a device
    
    Args:
        device_id: Device identifier
        sequence: Event sequence number
    """
    try:
        devices_table.update_item(
            Key={'device_id': device_id},
            UpdateExpression='SET last_sequence = :seq',
            ExpressionAttributeValues={':seq': sequence}
        )
    except ClientError as e:
        print(f"Error updating last sequence: {str(e)}")


def log_event(device_id, timestamp, slot, state, in_holder, sensor_level, sequence):
    """
    Log event to Events table with TTL for auto-deletion after 30 days
    
    Args:
        device_id: Device identifier
        timestamp: Unix timestamp in milliseconds
        slot: Slot number (1-3)
        state: "in_holder" or "not_in_holder"
        in_holder: Boolean state
        sensor_level: 0 or 1
        sequence: Event sequence number
    """
    try:
        # Calculate TTL (30 days from now in seconds)
        ttl = int(timestamp / 1000) + (TTL_DAYS * 24 * 60 * 60)
        
        events_table.put_item(
            Item={
                'device_id': device_id,
                'timestamp': timestamp,
                'event_type': 'slot_state_changed',
                'slot': slot,
                'state': state,
                'in_holder': in_holder,
                'sensor_level': sensor_level,
                'sequence': sequence,
                'ttl': ttl
            }
        )
        print(f"Event logged for device {device_id}, slot {slot}")
        
    except ClientError as e:
        print(f"Error logging event: {str(e)}")
        raise


def update_device_state(device_id, slot, in_holder, timestamp):
    """
    Update device slot state and last_seen timestamp
    
    Args:
        device_id: Device identifier
        slot: Slot number (1-3)
        in_holder: Boolean state
        timestamp: Unix timestamp in milliseconds
    """
    try:
        devices_table.update_item(
            Key={'device_id': device_id},
            UpdateExpression='SET slots.#slot.in_holder = :in_holder, '
                           'slots.#slot.last_state_change = :timestamp, '
                           'last_seen = :timestamp',
            ExpressionAttributeNames={
                '#slot': str(slot)
            },
            ExpressionAttributeValues={
                ':in_holder': in_holder,
                ':timestamp': timestamp
            }
        )
        print(f"Device state updated for {device_id}, slot {slot}")
        
    except ClientError as e:
        print(f"Error updating device state: {str(e)}")
        raise


def get_prescription(device_id, slot):
    """
    Get prescription for a specific device and slot
    
    Args:
        device_id: Device identifier
        slot: Slot number (1-3)
        
    Returns:
        dict: Prescription data or None if not found
    """
    try:
        response = prescriptions_table.get_item(
            Key={
                'device_id': device_id,
                'slot': slot
            }
        )
        
        return response.get('Item')
        
    except ClientError as e:
        print(f"Error getting prescription: {str(e)}")
        return None


def process_bottle_removal(device_id, slot, prescription, timestamp):
    """
    Process bottle removal event:
    - Decrement pill count (floor at 0)
    - Set removal_timestamp
    - Check refill reminder threshold
    
    Implements Property 2 (Pill Count Non-Negativity) and
    Property 5 (Refill Reminder Threshold)
    
    Args:
        device_id: Device identifier
        slot: Slot number (1-3)
        prescription: Prescription data
        timestamp: Unix timestamp in milliseconds
    """
    try:
        # Decrement pill count, floor at 0
        current_count = prescription.get('pill_count', 0)
        new_count = max(0, current_count - 1)
        
        # Update prescription with new count and removal timestamp
        prescriptions_table.update_item(
            Key={
                'device_id': device_id,
                'slot': slot
            },
            UpdateExpression='SET pill_count = :count, '
                           'removal_timestamp = :timestamp, '
                           'updated_at = :timestamp',
            ExpressionAttributeValues={
                ':count': new_count,
                ':timestamp': timestamp
            }
        )
        
        print(f"Pill count decremented to {new_count} for device {device_id}, slot {slot}")
        
        # Send congratulations notification for taking pill
        send_congratulations(device_id, prescription)
        
        # Check refill reminder threshold
        if new_count < REFILL_THRESHOLD:
            send_refill_reminder(device_id, prescription, new_count)
        
        # Schedule timeout check (10 minutes)
        # Note: For hackathon, we'll rely on the separate Timeout Checker Lambda
        # that runs every 5 minutes via EventBridge
        
    except ClientError as e:
        print(f"Error processing bottle removal: {str(e)}")
        raise


def process_bottle_return(device_id, slot, prescription, timestamp):
    """
    Process bottle return event:
    - Clear removal_timestamp
    - Turn off LED
    
    Implements Property 4 (Removal Timestamp Invariant)
    
    Args:
        device_id: Device identifier
        slot: Slot number (1-3)
        prescription: Prescription data
        timestamp: Unix timestamp in milliseconds
    """
    try:
        # Clear removal timestamp
        prescriptions_table.update_item(
            Key={
                'device_id': device_id,
                'slot': slot
            },
            UpdateExpression='SET removal_timestamp = :null, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':null': None,
                ':timestamp': timestamp
            }
        )
        
        print(f"Removal timestamp cleared for device {device_id}, slot {slot}")
        
        # Turn off LED
        publish_led_command(device_id, slot, 'turn_off')
        
    except ClientError as e:
        print(f"Error processing bottle return: {str(e)}")
        raise




def send_congratulations(device_id, prescription):
    """
    Send Alexa notification congratulating user for taking their pill
    
    Args:
        device_id: Device identifier
        prescription: Prescription data
    """
    try:
        prescription_name = prescription.get('prescription_name', 'medication')
        pill_count = int(prescription.get('pill_count', 0))  # Convert Decimal to int
        
        # Vary the message for engagement
        messages = [
            f"Great job! You took your {prescription_name}. Keep up the good work!",
            f"Well done! Your {prescription_name} has been taken. You have {pill_count} pills remaining.",
            f"Excellent! You're staying on track with your {prescription_name}.",
            f"Nice work! You took your {prescription_name}. Stay healthy!",
        ]
        
        # Simple rotation based on pill count
        message = messages[pill_count % len(messages)]
        
        print(f"Congratulations: {message}")
        
        # Note: Alexa proactive notifications require additional setup
        # For hackathon, we'll log the message. Full implementation would use:
        # the Alexa Proactive Events API
        
        # Placeholder for Alexa notification
        # In production, this would send via Alexa Proactive Events API
        
    except Exception as e:
        print(f"Error sending congratulations: {str(e)}")


def send_refill_reminder(device_id, prescription, pill_count):
    """
    Send Alexa notification for refill or disposal reminder
    
    Implements Property 5 (Refill Reminder Threshold)
    
    Args:
        device_id: Device identifier
        prescription: Prescription data
        pill_count: Current pill count
    """
    try:
        prescription_name = prescription.get('prescription_name', 'medication')
        has_refills = prescription.get('has_refills', False)
        
        if has_refills:
            message = (f"Your {prescription_name} is running low with {pill_count} "
                      f"pills remaining. Please get a refill soon.")
        else:
            message = (f"Your {prescription_name} is running low with {pill_count} "
                      f"pills remaining. Please dispose of the empty bottle.")
        
        print(f"Refill reminder: {message}")
        
        # Note: Alexa proactive notifications require additional setup
        # For hackathon, we'll log the message. Full implementation would use:
        # alexa_client = boto3.client('alexa-for-business')
        # or the Alexa Proactive Events API
        
        # Placeholder for Alexa notification
        # In production, this would send via Alexa Proactive Events API
        
    except Exception as e:
        print(f"Error sending refill reminder: {str(e)}")


def publish_led_command(device_id, slot, action):
    """
    Publish LED control command to IoT Core
    
    Args:
        device_id: Device identifier
        slot: Slot number (1-3)
        action: "turn_on" or "turn_off"
    """
    try:
        topic = f"pillbuddy/cmd/{device_id}"
        payload = {
            'action': action,
            'slot': slot
        }
        
        iot_client.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(payload)
        )
        
        print(f"Published LED command to {topic}: {payload}")
        
    except ClientError as e:
        print(f"Error publishing LED command: {str(e)}")
        # Non-critical error, continue processing
