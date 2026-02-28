# Design Document: Alexa APL Visual Display

## Overview

This feature adds visual display support to the PillBuddy Alexa skill using Alexa Presentation Language (APL) 1.6. When users with Echo Show devices query their pill status, they will receive both a voice response and a visual display showing their three pill bottle slots, prescription names, pill counts, and low-pill warnings.

The implementation extends the existing `handle_query_status_intent()` function in the Alexa Lambda handler to:

1. Detect device APL capabilities
2. Fetch data from both DynamoDB tables (Prescriptions and Devices)
3. Construct an APL document with slot data
4. Return a response containing both voice output and APL directives

The design maintains backward compatibility with non-visual Alexa devices (Echo Dot, Echo, etc.) by conditionally including APL directives only when the device supports them.

## Architecture

### High-Level Component Diagram

```mermaid
graph TB
    User[User with Echo Show]
    Alexa[Alexa Service]
    Lambda[Alexa Handler Lambda]
    DDB_Devices[(DynamoDB: Devices)]
    DDB_Prescriptions[(DynamoDB: Prescriptions)]

    User -->|"Alexa, ask PillBuddy for my status"| Alexa
    Alexa -->|QueryStatusIntent Request| Lambda
    Lambda -->|Query device slots| DDB_Devices
    Lambda -->|Query prescriptions| DDB_Prescriptions
    Lambda -->|Response with APL| Alexa
    Alexa -->|Voice + Visual Display| User

    subgraph Lambda Function Components
        CapabilityDetector[Device Capability Detector]
        DataFetcher[Data Fetcher]
        APLBuilder[APL Document Builder]
        ResponseBuilder[Response Builder]
    end

    Lambda --> CapabilityDetector
    CapabilityDetector --> DataFetcher
    DataFetcher --> APLBuilder
    APLBuilder --> ResponseBuilder
```
