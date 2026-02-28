# Implementation Plan: Alexa APL Visual Display

## Overview

This implementation adds APL (Alexa Presentation Language) visual display support to the PillBuddy Alexa skill. The feature extends the existing `handle_query_status_intent()` function to detect device capabilities, fetch device slot data, and return APL directives for Echo Show devices while maintaining backward compatibility with voice-only devices.

## Tasks

- [x] 1. Create APL document template
  - Create `infrastructure/lambda/alexa_handler/apl_templates/` directory
  - Create `pill_status_display.json` APL document with APL 1.6 specification
  - Define layout with three horizontal pill slots
  - Include data bindings for slot_number, prescription_name, pill_count, in_holder, and low_pill_warning
  - Add visual styles for present bottles, missing bottles, and low-pill warnings
  - Include "PillBuddy Status" title section
  - Use responsive sizing units (dp or percentage) for Echo Show 5/8/10 compatibility
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4_

- [ ] 2. Implement device capability detection
  - [x] 2.1 Add `supports_apl()` helper function
    - Check `event['context']['System']['device']['supportedInterfaces']` for APL support
    - Return boolean indicating APL capability
    - Handle missing keys gracefully with try-except
    - _Requirements: 2.1, 2.4_

- [ ] 3. Implement data fetching for visual display
  - [x] 3.1 Add `fetch_device_slots()` helper function
    - Query PillBuddy_Devices table for device_id
    - Return slot data with in_holder status for all three slots
    - Handle query errors and return empty dict on failure
    - _Requirements: 6.2, 6.4_
  - [x] 3.2 Modify prescription data fetching
    - Update existing prescription query in `handle_query_status_intent()`
    - Ensure all three slots (1, 2, 3) are represented in data structure
    - Combine prescription data with device slot data by slot_number
    - _Requirements: 6.1, 6.3_

- [ ] 4. Implement APL document builder
  - [x] 4.1 Add `build_apl_datasources()` helper function
    - Accept combined slot data (prescriptions + device status)
    - Build datasources dict with slot array containing all three slots
    - For each slot: include slot_number, prescription_name, pill_count, in_holder status
    - Calculate low_pill_warning boolean (pill_count <= 7)
    - Use placeholder values for missing data (empty slots)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 9.3_
  - [x] 4.2 Add `load_apl_document()` helper function
    - Load APL template from `apl_templates/pill_status_display.json`
    - Return parsed JSON document
    - Handle file read errors gracefully
    - _Requirements: 1.1, 9.1, 9.2, 9.4_

- [ ] 5. Update response builder for APL support
  - [x] 5.1 Modify `build_response()` function signature
    - Add optional `apl_document` parameter (default None)
    - Add optional `apl_datasources` parameter (default None)
    - _Requirements: 7.1, 7.2_
  - [x] 5.2 Add APL directive construction to `build_response()`
    - When apl_document and apl_datasources are provided, add directives array
    - Include Alexa.Presentation.APL.RenderDocument directive
    - Set document, datasources, and token fields in directive
    - Maintain existing outputSpeech and shouldEndSession properties
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 6. Integrate APL into handle_query_status_intent
  - [x] 6.1 Add capability detection logic
    - Call `supports_apl()` at start of function
    - Store result in variable for conditional logic
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 6.2 Add device slot data fetching
    - Call `fetch_device_slots()` to get in_holder status
    - Combine with prescription data by slot_number
    - _Requirements: 6.2, 6.3_
  - [x] 6.3 Add APL response construction
    - When device supports APL, load APL document and build datasources
    - Pass APL document and datasources to `build_response()`
    - When device doesn't support APL, call `build_response()` without APL parameters
    - Wrap APL operations in try-except to ensure voice response always works
    - Log errors for debugging but don't fail the request
    - _Requirements: 2.2, 2.3, 7.1, 7.2, 7.3, 9.1, 9.2, 9.3, 9.4_

- [x] 7. Checkpoint - Test basic functionality
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Update Alexa skill configuration
  - Add instructions in comment or documentation for enabling APL interface in Alexa Developer Console
  - Note: This is a manual step in the Alexa Developer Console under "Interfaces" section
  - _Requirements: All requirements depend on APL interface being enabled_

- [ ] 9. Final checkpoint - Verify implementation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation maintains backward compatibility with non-visual devices
- APL rendering errors will not break voice responses
- Low pill threshold is hardcoded to 7 pills as specified in requirements
- All three slots (1, 2, 3) must be represented in the visual display
- Testing on actual Echo Show device is manual and outside scope of coding tasks
