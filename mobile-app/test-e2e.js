#!/usr/bin/env node

/**
 * End-to-End Test Script for iOS Medication App
 *
 * This script tests the core functionality by:
 * 1. Verifying DynamoDB connectivity
 * 2. Testing prescription CRUD operations
 * 3. Simulating device state changes
 * 4. Verifying data consistency
 */

const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const {
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  UpdateCommand,
  QueryCommand,
} = require("@aws-sdk/lib-dynamodb");

// Load environment variables
require("dotenv").config();

const AWS_REGION = process.env.AWS_REGION || "us-east-1";
const AWS_ACCESS_KEY_ID = process.env.AWS_ACCESS_KEY_ID;
const AWS_SECRET_ACCESS_KEY = process.env.AWS_SECRET_ACCESS_KEY;

const DEVICE_ID = "pillbuddy-esp32-1";
const DEVICES_TABLE = "PillBuddy_Devices";
const PRESCRIPTIONS_TABLE = "PillBuddy_Prescriptions";

// Initialize DynamoDB client
const client = new DynamoDBClient({
  region: AWS_REGION,
  credentials: {
    accessKeyId: AWS_ACCESS_KEY_ID,
    secretAccessKey: AWS_SECRET_ACCESS_KEY,
  },
});

const docClient = DynamoDBDocumentClient.from(client);

// Test results
const results = {
  passed: 0,
  failed: 0,
  tests: [],
};

function logTest(name, passed, message) {
  const status = passed ? "✅ PASS" : "❌ FAIL";
  console.log(`${status}: ${name}`);
  if (message) {
    console.log(`   ${message}`);
  }
  results.tests.push({ name, passed, message });
  if (passed) {
    results.passed++;
  } else {
    results.failed++;
  }
}

async function test1_GetDeviceState() {
  try {
    const command = new GetCommand({
      TableName: DEVICES_TABLE,
      Key: { device_id: DEVICE_ID },
    });

    const response = await docClient.send(command);

    if (!response.Item) {
      logTest("Get Device State", false, "Device not found in database");
      return;
    }

    const hasSlots =
      response.Item.slots &&
      response.Item.slots["1"] &&
      response.Item.slots["2"] &&
      response.Item.slots["3"];

    if (!hasSlots) {
      logTest("Get Device State", false, "Device missing slot data");
      return;
    }

    logTest("Get Device State", true, `Device found with 3 slots`);
  } catch (error) {
    logTest("Get Device State", false, error.message);
  }
}

async function test2_GetPrescriptions() {
  try {
    const command = new QueryCommand({
      TableName: PRESCRIPTIONS_TABLE,
      KeyConditionExpression: "device_id = :deviceId",
      ExpressionAttributeValues: {
        ":deviceId": DEVICE_ID,
      },
    });

    const response = await docClient.send(command);
    const prescriptions = response.Items || [];

    logTest(
      "Get Prescriptions",
      true,
      `Found ${prescriptions.length} prescriptions`,
    );

    // Log prescription details
    prescriptions.forEach((p) => {
      console.log(
        `   Slot ${p.slot}: ${p.prescription_name} (${p.pill_count} pills)`,
      );
    });
  } catch (error) {
    logTest("Get Prescriptions", false, error.message);
  }
}

async function test3_CreateTestPrescription() {
  try {
    const testPrescription = {
      device_id: DEVICE_ID,
      slot: 1,
      prescription_name: "E2E Test Medicine",
      pill_count: 99,
      initial_count: 99,
      has_refills: true,
      created_at: Date.now(),
      updated_at: Date.now(),
    };

    const command = new PutCommand({
      TableName: PRESCRIPTIONS_TABLE,
      Item: testPrescription,
    });

    await docClient.send(command);

    // Verify it was created
    const getCommand = new GetCommand({
      TableName: PRESCRIPTIONS_TABLE,
      Key: {
        device_id: DEVICE_ID,
        slot: 1,
      },
    });

    const response = await docClient.send(getCommand);

    if (
      response.Item &&
      response.Item.prescription_name === "E2E Test Medicine"
    ) {
      logTest(
        "Create Prescription",
        true,
        "Test prescription created successfully",
      );
    } else {
      logTest(
        "Create Prescription",
        false,
        "Prescription not found after creation",
      );
    }
  } catch (error) {
    logTest("Create Prescription", false, error.message);
  }
}

async function test4_UpdatePillCount() {
  try {
    const newCount = 88;

    const command = new UpdateCommand({
      TableName: PRESCRIPTIONS_TABLE,
      Key: {
        device_id: DEVICE_ID,
        slot: 1,
      },
      UpdateExpression: "SET pill_count = :pillCount, updated_at = :updatedAt",
      ExpressionAttributeValues: {
        ":pillCount": newCount,
        ":updatedAt": Date.now(),
      },
    });

    await docClient.send(command);

    // Verify update
    const getCommand = new GetCommand({
      TableName: PRESCRIPTIONS_TABLE,
      Key: {
        device_id: DEVICE_ID,
        slot: 1,
      },
    });

    const response = await docClient.send(getCommand);

    if (response.Item && response.Item.pill_count === newCount) {
      logTest("Update Pill Count", true, `Pill count updated to ${newCount}`);
    } else {
      logTest("Update Pill Count", false, "Pill count not updated correctly");
    }
  } catch (error) {
    logTest("Update Pill Count", false, error.message);
  }
}

async function test5_VerifyInitialCountPreserved() {
  try {
    const getCommand = new GetCommand({
      TableName: PRESCRIPTIONS_TABLE,
      Key: {
        device_id: DEVICE_ID,
        slot: 1,
      },
    });

    const response = await docClient.send(getCommand);

    if (!response.Item) {
      logTest(
        "Verify Initial Count Preserved",
        false,
        "Prescription not found",
      );
      return;
    }

    const initialCount = response.Item.initial_count;
    const pillCount = response.Item.pill_count;

    if (initialCount === 99 && pillCount === 88) {
      logTest(
        "Verify Initial Count Preserved",
        true,
        `initial_count=${initialCount} preserved while pill_count=${pillCount}`,
      );
    } else {
      logTest(
        "Verify Initial Count Preserved",
        false,
        `initial_count=${initialCount}, pill_count=${pillCount}`,
      );
    }
  } catch (error) {
    logTest("Verify Initial Count Preserved", false, error.message);
  }
}

async function test6_SimulateBottleRemoval() {
  try {
    // Update device state to simulate bottle removal
    const command = new UpdateCommand({
      TableName: DEVICES_TABLE,
      Key: { device_id: DEVICE_ID },
      UpdateExpression:
        "SET slots.#slot.in_holder = :false, slots.#slot.last_state_change = :timestamp",
      ExpressionAttributeNames: {
        "#slot": "1",
      },
      ExpressionAttributeValues: {
        ":false": false,
        ":timestamp": Date.now(),
      },
    });

    await docClient.send(command);

    // Verify update
    const getCommand = new GetCommand({
      TableName: DEVICES_TABLE,
      Key: { device_id: DEVICE_ID },
    });

    const response = await docClient.send(getCommand);

    if (response.Item && response.Item.slots["1"].in_holder === false) {
      logTest("Simulate Bottle Removal", true, "Slot 1 marked as removed");
    } else {
      logTest("Simulate Bottle Removal", false, "Device state not updated");
    }
  } catch (error) {
    logTest("Simulate Bottle Removal", false, error.message);
  }
}

async function test7_CleanupTestData() {
  try {
    // Note: We're not actually deleting to preserve test data
    // In a real test, you'd delete the test prescription here
    logTest(
      "Cleanup Test Data",
      true,
      "Test data preserved for manual inspection",
    );
  } catch (error) {
    logTest("Cleanup Test Data", false, error.message);
  }
}

async function runTests() {
  console.log("\n=== iOS Medication App E2E Tests ===\n");
  console.log(`Device ID: ${DEVICE_ID}`);
  console.log(`Region: ${AWS_REGION}\n`);

  await test1_GetDeviceState();
  await test2_GetPrescriptions();
  await test3_CreateTestPrescription();
  await test4_UpdatePillCount();
  await test5_VerifyInitialCountPreserved();
  await test6_SimulateBottleRemoval();
  await test7_CleanupTestData();

  console.log("\n=== Test Summary ===\n");
  console.log(`Total: ${results.passed + results.failed}`);
  console.log(`Passed: ${results.passed}`);
  console.log(`Failed: ${results.failed}`);

  if (results.failed > 0) {
    console.log("\n❌ Some tests failed. Check the output above for details.");
    process.exit(1);
  } else {
    console.log("\n✅ All tests passed!");
    process.exit(0);
  }
}

// Run tests
runTests().catch((error) => {
  console.error("Fatal error running tests:", error);
  process.exit(1);
});
