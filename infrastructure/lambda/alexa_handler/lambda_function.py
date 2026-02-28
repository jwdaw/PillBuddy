"""
PillBuddy Alexa Skill Handler Lambda Function

This Lambda function processes Alexa voice commands for the PillBuddy system.
It handles device setup, prescription management, and status queries.

APL Visual Display Support:
    This skill supports visual display on Echo Show devices using Alexa Presentation Language (APL).
    IMPORTANT: The APL interface must be enabled in the Alexa Developer Console for visual display to work.
    To enable: Developer Console > Build > Interfaces > Alexa Presentation Language > Toggle ON
    Without APL enabled, Echo Show devices will only receive voice responses.

Environment Variables:
    DEVICES_TABLE: DynamoDB table name for devices (PillBuddy_Devices)
    PRESCRIPTIONS_TABLE: DynamoDB table name for prescriptions (PillBuddy_Prescriptions)
    IOT_ENDPOINT: AWS IoT Core endpoint URL
    AWS_REGION: AWS region (e.g., us-east-1)
"""

import os
import json
import time
import boto3
from typing import Dict, Any, Optional

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
iot_client = boto3.client('iot-data')

# Environment variables
DEVICES_TABLE = os.environ['DEVICES_TABLE']
PRESCRIPTIONS_TABLE = os.environ['PRESCRIPTIONS_TABLE']
IOT_ENDPOINT = os.environ['IOT_ENDPOINT']
# AWS_REGION is automatically available in Lambda environment

# DynamoDB table references
devices_table = dynamodb.Table(DEVICES_TABLE)
prescriptions_table = dynamodb.Table(PRESCRIPTIONS_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main entry point for Alexa Skill requests
    
    Args:
        event: Alexa request (LaunchRequest, IntentRequest, SessionEndedRequest)
        context: Lambda context object
    
    Returns:
        Alexa response with speech output and session attributes
    """
    request_type = event['request']['type']
    
    # Extract device_id from session or use default for hackathon
    # In production, this would come from account linking
    device_id = event.get('session', {}).get('user', {}).get('userId', 'esp32_001')
    
    try:
        if request_type == 'LaunchRequest':
            return handle_launch_request(device_id, event)
        elif request_type == 'IntentRequest':
            intent_name = event['request']['intent']['name']
            
            if intent_name == 'SetupSlotIntent':
                return handle_setup_slot_intent(device_id, event)
            elif intent_name == 'QueryStatusIntent':
                return handle_query_status_intent(device_id, event)
            elif intent_name == 'StartSetupIntent':
                return handle_launch_request(device_id, event)
            elif intent_name == 'AMAZON.HelpIntent':
                return handle_help_intent()
            elif intent_name == 'AMAZON.StopIntent':
                return handle_stop_intent()
            elif intent_name == 'AMAZON.CancelIntent':
                return handle_cancel_intent()
            else:
                return build_response(
                    "Sorry, I don't understand that command.",
                    should_end_session=True
                )
        elif request_type == 'SessionEndedRequest':
            return build_response("", should_end_session=True)
        else:
            return build_response(
                "Sorry, I don't understand that request.",
                should_end_session=True
            )
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return build_response(
            "Sorry, I encountered an error. Please try again.",
            should_end_session=True
        )


def build_response(speech_text: str, 
                   session_attributes: Optional[Dict[str, Any]] = None,
                   should_end_session: bool = False,
                   reprompt_text: Optional[str] = None,
                   apl_document: Optional[Dict[str, Any]] = None,
                   apl_datasources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build Alexa response in the required format
    
    Args:
        speech_text: Text for Alexa to speak
        session_attributes: Session state to maintain
        should_end_session: Whether to end the session
        reprompt_text: Text to speak if user doesn't respond
        apl_document: Optional APL document for visual display
        apl_datasources: Optional APL datasources for visual display
    
    Returns:
        Alexa response dictionary
    """
    response = {
        'version': '1.0',
        'sessionAttributes': session_attributes or {},
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': speech_text
            },
            'shouldEndSession': should_end_session
        }
    }
    
    if reprompt_text:
        response['response']['reprompt'] = {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        }
    
    # Add APL directive if document and datasources are provided
    if apl_document and apl_datasources:
        response['response']['directives'] = [
            {
                'type': 'Alexa.Presentation.APL.RenderDocument',
                'token': 'pillStatusToken',
                'document': apl_document,
                'datasources': apl_datasources
            }
        ]
    
    return response


def supports_apl(event: Dict[str, Any]) -> bool:
    """
    Check if the requesting device supports APL (Alexa Presentation Language)
    
    Args:
        event: Alexa request event
    
    Returns:
        True if device supports APL, False otherwise
    """
    try:
        supported_interfaces = event['context']['System']['device']['supportedInterfaces']
        return 'Alexa.Presentation.APL' in supported_interfaces
    except (KeyError, TypeError):
        # If any key is missing or structure is unexpected, assume no APL support
        return False


def fetch_device_slots(device_id: str) -> Dict[str, Any]:
    """
    Fetch device slot data from DynamoDB
    
    Queries the PillBuddy_Devices table to get the in_holder status for all three slots.
    This data is used for APL visual display to show which bottles are physically present.
    
    Args:
        device_id: Device identifier
    
    Returns:
        Dictionary with slot data in format:
        {
            '1': {'in_holder': bool, 'last_state_change': int},
            '2': {'in_holder': bool, 'last_state_change': int},
            '3': {'in_holder': bool, 'last_state_change': int}
        }
        Returns empty dict {} on failure
    """
    try:
        response = devices_table.get_item(Key={'device_id': device_id})
        
        if 'Item' in response and 'slots' in response['Item']:
            return response['Item']['slots']
        else:
            # Device not found or no slots data - return empty dict
            return {}
    except Exception as e:
        print(f"Error fetching device slots: {str(e)}")
        return {}


def build_apl_datasources(combined_slots: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build APL datasources structure from combined slot data

    Transforms the combined_slots data structure (prescriptions + device status) into
    the format expected by the APL template. Calculates low_pill_warning for each slot
    and uses placeholder values for missing data.

    Args:
        combined_slots: Dictionary with slot data in format:
            {
                '1': {'slot_number': 1, 'prescription_name': str|None, 'pill_count': int, 'in_holder': bool},
                '2': {...},
                '3': {...}
            }

    Returns:
        Dictionary with datasources structure for APL:
        {
            'slots': [
                {
                    'slot_number': int,
                    'prescription_name': str,
                    'pill_count': int,
                    'in_holder': bool,
                    'low_pill_warning': bool
                },
                ...
            ]
        }
    """
    LOW_PILL_THRESHOLD = 7

    slots_array = []

    # Process all three slots in order
    for slot_num in [1, 2, 3]:
        slot_key = str(slot_num)
        slot_data = combined_slots.get(slot_key, {})

        # Extract data with defaults for missing values
        prescription_name = slot_data.get('prescription_name') or 'Empty Slot'
        pill_count = slot_data.get('pill_count', 0)
        in_holder = slot_data.get('in_holder', False)

        # Calculate low pill warning (only relevant if bottle is in holder and has prescription)
        low_pill_warning = in_holder and pill_count > 0 and pill_count <= LOW_PILL_THRESHOLD

        slots_array.append({
            'slot_number': slot_num,
            'prescription_name': prescription_name,
            'pill_count': pill_count,
            'in_holder': in_holder,
            'low_pill_warning': low_pill_warning
        })

    return {
        'slots': slots_array
    }


def load_apl_document() -> Optional[Dict[str, Any]]:
    """
    Load APL document template from file system
    
    Reads the APL template from apl_templates/pill_status_display.json and returns
    it as a parsed JSON object. Handles file read errors gracefully to ensure the
    voice response still works even if the APL template can't be loaded.
    
    Returns:
        Parsed APL document dictionary, or None if loading fails
    """
    try:
        # Construct path relative to this Lambda function file
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, 'apl_templates', 'pill_status_display.json')
        
        with open(template_path, 'r') as f:
            apl_document = json.load(f)
        
        return apl_document
    except FileNotFoundError:
        print(f"APL template file not found at {template_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing APL template JSON: {str(e)}")
        return None
    except Exception as e:
        print(f"Error loading APL document: {str(e)}")
        return None



def handle_launch_request(device_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle LaunchRequest - start setup flow
    
    Args:
        device_id: Device identifier
        event: Alexa request event
    
    Returns:
        Alexa response
    """
    try:
        # Check if device exists, create if not
        response = devices_table.get_item(Key={'device_id': device_id})
        
        if 'Item' not in response:
            # Device not found - create initial device record
            current_time = int(time.time() * 1000)
            devices_table.put_item(Item={
                'device_id': device_id,
                'online': False,
                'last_seen': current_time,
                'created_at': current_time,
                'slots': {
                    '1': {'in_holder': False, 'last_state_change': current_time},
                    '2': {'in_holder': False, 'last_state_change': current_time},
                    '3': {'in_holder': False, 'last_state_change': current_time}
                }
            })
        
        # Start setup flow (no online check - MQTT can be intermittent)
        session_attributes = {
            'device_id': device_id,
            'setup_state': {
                'slots_configured': 0,
                'current_slot': 1
            }
        }
        
        speech_text = "Welcome to PillBuddy! Let's set up your pill bottles. I'll guide you through configuring each of the three slots. For the first slot, please tell me the prescription name, number of pills, and whether you have refills."
        reprompt_text = "Please tell me the prescription name, number of pills, and whether you have refills for slot 1."
        
        return build_response(
            speech_text,
            session_attributes=session_attributes,
            should_end_session=False,
            reprompt_text=reprompt_text
        )
        
    except Exception as e:
        print(f"Error in handle_launch_request: {str(e)}")
        return build_response(
            "Sorry, I'm having trouble starting the setup. Please try again.",
            should_end_session=True
        )



def handle_setup_slot_intent(device_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle SetupSlotIntent - store prescription data and trigger LED
    
    Implements Algorithm 1 (processSetupSlotIntent) from design.md
    
    Args:
        device_id: Device identifier
        event: Alexa request event
    
    Returns:
        Alexa response
    """
    try:
        # Extract slots from intent
        intent = event['request']['intent']
        slots = intent.get('slots', {})
        
        # Get session attributes
        session_attributes = event.get('session', {}).get('attributes', {})
        setup_state = session_attributes.get('setup_state', {'slots_configured': 0, 'current_slot': 1})
        
        # Extract slot values
        prescription_name = slots.get('prescriptionName', {}).get('value')
        pill_count_str = slots.get('pillCount', {}).get('value')
        has_refills_str = slots.get('hasRefills', {}).get('value')
        
        # Validate required slots
        if not prescription_name:
            return build_response(
                "I didn't catch the prescription name. Please tell me the prescription name, number of pills, and whether you have refills.",
                session_attributes=session_attributes,
                should_end_session=False,
                reprompt_text="What's the prescription name?"
            )
        
        if not pill_count_str:
            return build_response(
                "I didn't catch the number of pills. Please tell me how many pills are in the bottle.",
                session_attributes=session_attributes,
                should_end_session=False,
                reprompt_text="How many pills are in the bottle?"
            )
        
        # Parse pill count
        try:
            pill_count = int(pill_count_str)
            if pill_count <= 0:
                return build_response(
                    "The pill count must be a positive number. Please tell me how many pills are in the bottle.",
                    session_attributes=session_attributes,
                    should_end_session=False
                )
        except ValueError:
            return build_response(
                "I didn't understand the pill count. Please tell me how many pills are in the bottle.",
                session_attributes=session_attributes,
                should_end_session=False
            )
        
        # Parse has_refills (default to False if not provided)
        has_refills = False
        if has_refills_str:
            has_refills_lower = has_refills_str.lower()
            has_refills = has_refills_lower in ['yes', 'true', 'yeah', 'yep']
        
        # Determine which slot to configure
        current_slot = setup_state.get('current_slot', 1)
        
        # Store prescription in DynamoDB
        current_time = int(time.time() * 1000)
        prescription_item = {
            'device_id': device_id,
            'slot': current_slot,
            'prescription_name': prescription_name,
            'pill_count': pill_count,
            'initial_count': pill_count,
            'has_refills': has_refills,
            'created_at': current_time,
            'updated_at': current_time,
            'removal_timestamp': None
        }
        
        try:
            prescriptions_table.put_item(Item=prescription_item)
        except Exception as e:
            print(f"DynamoDB write error: {str(e)}")
            return build_response(
                "Sorry, I couldn't save that prescription. Please try again.",
                session_attributes=session_attributes,
                should_end_session=False
            )
        
        # Publish LED turn_on command to IoT Core
        try:
            publish_iot_command(device_id, 'turn_on', current_slot)
        except Exception as e:
            print(f"IoT publish error: {str(e)}")
            # Continue even if LED command fails (non-critical)
        
        # Update session state
        slots_configured = setup_state.get('slots_configured', 0) + 1
        setup_state['slots_configured'] = slots_configured
        setup_state['current_slot'] = current_slot + 1
        session_attributes['setup_state'] = setup_state
        
        # Build response based on progress
        if slots_configured < 3:
            refill_text = "with refills" if has_refills else "without refills"
            speech_text = f"Great! I've saved {prescription_name} {refill_text} with {pill_count} pills for slot {current_slot}. The LED is on. Please place the bottle in slot {current_slot}. Would you like to set up slot {current_slot + 1}?"
            reprompt_text = f"Would you like to set up another bottle for slot {current_slot + 1}?"
            should_end_session = False
        else:
            refill_text = "with refills" if has_refills else "without refills"
            speech_text = f"Perfect! I've saved {prescription_name} {refill_text} with {pill_count} pills for slot {current_slot}. All three slots are configured. Your PillBuddy is ready to use!"
            reprompt_text = None
            should_end_session = True
        
        return build_response(
            speech_text,
            session_attributes=session_attributes,
            should_end_session=should_end_session,
            reprompt_text=reprompt_text
        )
        
    except Exception as e:
        print(f"Error in handle_setup_slot_intent: {str(e)}")
        return build_response(
            "Sorry, I encountered an error setting up that slot. Please try again.",
            should_end_session=True
        )


def publish_iot_command(device_id: str, action: str, slot: int) -> None:
    """
    Publish command to IoT Core topic
    
    Args:
        device_id: Device identifier
        action: Command action ('turn_on' or 'turn_off')
        slot: Slot number (1, 2, or 3)
    """
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



def handle_query_status_intent(device_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle QueryStatusIntent - return current status of all slots
    
    Args:
        device_id: Device identifier
        event: Alexa request event
    
    Returns:
        Alexa response with prescription status
    """
    try:
        # Check if device supports APL for visual display
        device_supports_apl = supports_apl(event)
        
        # Query all prescriptions for this device
        response = prescriptions_table.query(
            KeyConditionExpression='device_id = :device_id',
            ExpressionAttributeValues={
                ':device_id': device_id
            }
        )
        
        prescriptions = response.get('Items', [])
        
        # Fetch device slot data (in_holder status)
        device_slots = fetch_device_slots(device_id)
        
        # Build combined slot data structure ensuring all three slots are represented
        combined_slots = {}
        for slot_num in [1, 2, 3]:
            slot_key = str(slot_num)
            combined_slots[slot_key] = {
                'slot_number': slot_num,
                'prescription_name': None,
                'pill_count': 0,
                'in_holder': device_slots.get(slot_key, {}).get('in_holder', False)
            }
        
        # Populate prescription data into combined structure
        for prescription in prescriptions:
            slot_key = str(prescription['slot'])
            if slot_key in combined_slots:
                combined_slots[slot_key]['prescription_name'] = prescription['prescription_name']
                combined_slots[slot_key]['pill_count'] = prescription['pill_count']
        
        # Build status message for voice response (only for slots with prescriptions)
        status_parts = []
        for slot_num in [1, 2, 3]:
            slot_key = str(slot_num)
            slot_data = combined_slots[slot_key]
            if slot_data['prescription_name']:
                name = slot_data['prescription_name']
                count = slot_data['pill_count']
                
                if count == 1:
                    status_parts.append(f"Slot {slot_num} has {name} with {count} pill remaining")
                else:
                    status_parts.append(f"Slot {slot_num} has {name} with {count} pills remaining")
        
        if not status_parts:
            return build_response(
                "You don't have any prescriptions set up yet. Say 'Alexa, open pillbuddy' to set up your bottles.",
                should_end_session=True
            )
        
        if len(status_parts) == 1:
            speech_text = status_parts[0] + "."
        elif len(status_parts) == 2:
            speech_text = status_parts[0] + ", and " + status_parts[1] + "."
        else:
            speech_text = ", ".join(status_parts[:-1]) + ", and " + status_parts[-1] + "."
        
        # Add APL visual display if device supports it
        apl_document = None
        apl_datasources = None
        
        if device_supports_apl:
            try:
                # Load APL document template
                apl_document = load_apl_document()
                
                if apl_document:
                    # Build datasources from combined slot data
                    apl_datasources = build_apl_datasources(combined_slots)
                else:
                    print("APL document could not be loaded, skipping visual display")
            except Exception as e:
                # Log error but don't fail the request - voice response should always work
                print(f"Error preparing APL response: {str(e)}")
                apl_document = None
                apl_datasources = None
        
        return build_response(
            speech_text, 
            should_end_session=True,
            apl_document=apl_document,
            apl_datasources=apl_datasources
        )
        
    except Exception as e:
        print(f"Error in handle_query_status_intent: {str(e)}")
        return build_response(
            "Sorry, I'm having trouble retrieving your prescription status. Please try again.",
            should_end_session=True
        )



def handle_help_intent() -> Dict[str, Any]:
    """
    Handle AMAZON.HelpIntent
    
    Returns:
        Alexa response with help information
    """
    speech_text = "PillBuddy helps you track your pill bottles. You can set up bottles, check your pill counts, and get refill reminders. What would you like to do?"
    reprompt_text = "You can say 'set up my bottles' or 'check my status'. What would you like to do?"
    
    return build_response(
        speech_text,
        should_end_session=False,
        reprompt_text=reprompt_text
    )


def handle_stop_intent() -> Dict[str, Any]:
    """
    Handle AMAZON.StopIntent
    
    Returns:
        Alexa response to end session
    """
    return build_response("Goodbye!", should_end_session=True)


def handle_cancel_intent() -> Dict[str, Any]:
    """
    Handle AMAZON.CancelIntent
    
    Returns:
        Alexa response to cancel and end session
    """
    return build_response("Okay, cancelled.", should_end_session=True)
