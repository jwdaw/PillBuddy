# Implementation Plan: PillBuddy Backend Alexa Integration

## Overview

This implementation creates a serverless AWS backend for the PillBuddy smart pill bottle holder system. The system uses AWS Lambda functions to handle Alexa voice commands, process IoT events from ESP32 devices, and manage prescription data in DynamoDB. The implementation focuses on rapid prototyping for a hackathon with no authentication or formal testing requirements.

## Tasks

- [x] 1. Set up DynamoDB tables and AWS infrastructure
  - Create three DynamoDB tables: Devices, Prescriptions, and Events
  - Configure table schemas with partition keys, sort keys, and TTL settings
  - Set provisioned capacity for hackathon usage (5-10 RCU/WCU)
  - _Requirements: Data Models (Devices, Prescriptions, Events)_

- [x] 2. Configure AWS IoT Core
  - [x] 2.1 Create IoT Thing Type and policy
    - Define PillBuddyDevice thing type
    - Create IoT policy allowing connect, publish, subscribe, and receive on pillbuddy topics
    - _Requirements: AWS IoT Core Configuration, IoT Policy_
  - [x] 2.2 Set up IoT Rule for event processing
    - Create IoT Rule to forward messages from pillbuddy/events/+ to Lambda
    - Configure rule SQL: SELECT \* FROM 'pillbuddy/events/+'
    - _Requirements: MQTT Topics, Device Events Topic_

- [x] 3. Implement Alexa Skill Handler Lambda function
  - [x] 3.1 Create Lambda function structure and environment setup
    - Set up Python 3.11 Lambda with 256MB memory, 10s timeout
    - Configure environment variables (DEVICES_TABLE, PRESCRIPTIONS_TABLE, IOT_ENDPOINT, AWS_REGION)
    - Set up IAM role with DynamoDB and IoT permissions
    - _Requirements: Lambda Function Specifications - Alexa Skill Handler_
  - [x] 3.2 Implement LaunchRequest handler
    - Check device online status from Devices table
    - Return appropriate response based on device connectivity
    - _Requirements: Algorithm 1 (processSetupSlotIntent), Alexa Skill Configuration - LaunchRequest_
  - [x] 3.3 Implement SetupSlotIntent handler
    - Parse prescription details from Alexa slots (prescriptionName, pillCount, hasRefills)
    - Store prescription in DynamoDB Prescriptions table
    - Publish LED turn_on command to IoT Core topic pillbuddy/cmd/{device_id}
    - Manage multi-turn conversation state for 3 slots
    - _Requirements: Algorithm 1 (processSetupSlotIntent), Alexa Skill Configuration - SetupSlotIntent_
  - [x] 3.4 Implement QueryStatusIntent handler
    - Query all prescriptions for device from Prescriptions table
    - Format speech response with slot status and pill counts
    - _Requirements: Alexa Skill Configuration - QueryStatusIntent_
  - [x] 3.5 Implement built-in intent handlers
    - Add handlers for AMAZON.HelpIntent, AMAZON.StopIntent, AMAZON.CancelIntent
    - _Requirements: Alexa Skill Configuration - Built-in Intents_
  - [x] 3.6 Add error handling for common scenarios
    - Handle device offline condition
    - Handle DynamoDB write failures with user-friendly messages
    - Handle IoT publish failures gracefully
    - _Requirements: Error Handling (Scenarios 1, 2, 3)_

- [x] 4. Checkpoint - Verify Alexa Lambda setup
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement IoT Event Processor Lambda function
  - [x] 5.1 Create Lambda function structure and environment setup
    - Set up Python 3.11 Lambda with 256MB memory, 30s timeout
    - Configure environment variables (all table names, IOT_ENDPOINT, ALEXA_SKILL_ID, AWS_REGION)
    - Set up IAM role with DynamoDB, IoT, Alexa notifications, and EventBridge permissions
    - _Requirements: Lambda Function Specifications - IoT Event Processor_
  - [x] 5.2 Implement event logging and device state update
    - Parse IoT Core MQTT message from pillbuddy/events/{device_id}
    - Log event to Events table with TTL (timestamp + 30 days)
    - Update device slot state and last_seen in Devices table
    - _Requirements: Algorithm 2 (processSlotStateChanged), Data Models (Events, Devices)_
  - [x] 5.3 Implement bottle removal logic
    - Decrement pill count when bottle removed (in_holder = false)
    - Set removal_timestamp in Prescriptions table
    - Floor pill count at 0 if negative
    - _Requirements: Algorithm 2 (processSlotStateChanged), Property 2 (Pill Count Non-Negativity)_
  - [x] 5.4 Implement refill reminder logic
    - Check if pill count < 5 after decrement
    - Send Alexa notification based on has_refills flag (refill vs disposal reminder)
    - _Requirements: Algorithm 2 (processSlotStateChanged), Property 5 (Refill Reminder Threshold)_
  - [x] 5.5 Implement bottle return logic
    - Clear removal_timestamp when bottle returned (in_holder = true)
    - Publish LED turn_off command to IoT Core
    - _Requirements: Algorithm 2 (processSlotStateChanged), Property 4 (Removal Timestamp Invariant)_
  - [x] 5.6 Add event deduplication
    - Track last processed sequence number per device
    - Skip processing if sequence <= last processed
    - _Requirements: Error Handling (Scenario 4 - Duplicate Event Processing)_

- [x] 6. Implement Timeout Checker Lambda function
  - [x] 6.1 Create Lambda function structure
    - Set up Python 3.11 Lambda with 128MB memory, 10s timeout
    - Configure environment variables (PRESCRIPTIONS_TABLE, ALEXA_SKILL_ID)
    - Set up IAM role with DynamoDB read and Alexa notification permissions
    - _Requirements: Lambda Function Specifications - Timeout Checker_
  - [x] 6.2 Implement timeout check logic
    - Query Prescriptions table for entries with non-null removal_timestamp
    - Calculate elapsed time since removal
    - Send Alexa notification if elapsed time >= 10 minutes
    - _Requirements: Algorithm 3 (checkBottleReturnTimeout)_
  - [x] 6.3 Set up EventBridge scheduled rule
    - Create EventBridge rule to trigger Lambda every 5 minutes
    - _Requirements: Lambda Function Specifications - Timeout Checker_

- [x] 7. Checkpoint - Verify Lambda functions
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Create Alexa Skill configuration
  - [x] 8.1 Define skill manifest and interaction model
    - Set invocation name to "pill buddy" (two words required by Alexa)
    - Define custom intents (SetupSlotIntent, QueryStatusIntent)
    - Add sample utterances for each intent
    - Configure dialog model for multi-turn SetupSlotIntent
    - _Requirements: Alexa Skill Configuration (all sections)_
  - [x] 8.2 Configure skill permissions and endpoints
    - Enable proactive notifications permission (alexa::devices:all:notifications:write)
    - Set Lambda ARN as skill endpoint
    - _Requirements: Alexa Skill Configuration - Proactive Notifications_

- [x] 9. Implement optional API Gateway REST API
  - [x] 9.1 Create API Handler Lambda function
    - Set up Python 3.11 Lambda with 256MB memory, 10s timeout
    - Configure environment variables for all table names
    - Set up IAM role with DynamoDB read/write permissions
    - _Requirements: Lambda Function Specifications - API Handler_
  - [x] 9.2 Implement GET /devices/{device_id}/status endpoint
    - Query Devices table and return device status with slot states
    - _Requirements: API Gateway Configuration - GET /devices/{device_id}/status_
  - [x] 9.3 Implement GET /devices/{device_id}/prescriptions endpoint
    - Query Prescriptions table for all slots
    - Return array of prescription objects
    - _Requirements: API Gateway Configuration - GET /devices/{device_id}/prescriptions_
  - [x] 9.4 Implement GET /devices/{device_id}/events endpoint
    - Query Events table with optional start_time, end_time, limit parameters
    - Return array of event objects
    - _Requirements: API Gateway Configuration - GET /devices/{device_id}/events_
  - [x] 9.5 Implement PATCH /devices/{device_id}/slots/{slot} endpoint
    - Update prescription pill_count and has_refills
    - Return updated prescription object
    - _Requirements: API Gateway Configuration - PATCH /devices/{device_id}/slots/{slot}_
  - [x] 9.6 Set up API Gateway REST API
    - Create REST API with /devices resource and sub-resources
    - Configure CORS for hackathon (allow all origins)
    - Deploy to dev stage
    - _Requirements: API Gateway Configuration (all sections)_

- [x] 10. Create deployment and configuration documentation
  - [x] 10.1 Document environment variables and IAM permissions
    - List all required environment variables for each Lambda
    - Document IAM policy requirements
    - _Requirements: Lambda Function Specifications (all functions)_
  - [x] 10.2 Document IoT Core setup steps
    - Provide instructions for creating IoT Thing and certificates
    - Document MQTT topic structure and message formats
    - _Requirements: AWS IoT Core Configuration (all sections)_
  - [x] 10.3 Document Alexa Skill setup
    - Provide skill.json and interaction model files
    - Document testing steps with Alexa Developer Console
    - _Requirements: Alexa Skill Configuration (all sections)_

- [x] 11. Final checkpoint - Integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks focus on rapid prototyping for hackathon - no authentication or formal testing
- Implementation uses Python 3.11 for all Lambda functions
- DynamoDB tables use provisioned capacity (5-10 RCU/WCU) suitable for hackathon scale
- API Gateway endpoints (task 9) are optional and can be skipped for MVP
- Error handling is included but simplified for hackathon timeline
- Alexa proactive notifications require skill certification for production use
