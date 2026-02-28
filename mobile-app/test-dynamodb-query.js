/**
 * Test script to verify DynamoDB connection and query prescriptions
 * Run with: node test-dynamodb-query.js
 */

const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const {
  DynamoDBDocumentClient,
  QueryCommand,
  ScanCommand,
} = require("@aws-sdk/lib-dynamodb");
require("dotenv").config();

const DEVICE_ID = "pillbuddy-esp32-1";
const PRESCRIPTIONS_TABLE = "PillBuddy_Prescriptions";

// Initialize DynamoDB client
const client = new DynamoDBClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

const docClient = DynamoDBDocumentClient.from(client);

async function testQuery() {
  console.log("=== Testing DynamoDB Query ===");
  console.log("Region:", process.env.AWS_REGION);
  console.log("Table:", PRESCRIPTIONS_TABLE);
  console.log("Device ID:", DEVICE_ID);
  console.log("");

  try {
    // Test 1: Query by device_id (same as app)
    console.log("Test 1: Query prescriptions by device_id...");
    const queryCommand = new QueryCommand({
      TableName: PRESCRIPTIONS_TABLE,
      KeyConditionExpression: "device_id = :deviceId",
      ExpressionAttributeValues: {
        ":deviceId": DEVICE_ID,
      },
    });

    const queryResponse = await docClient.send(queryCommand);
    console.log("✅ Query successful!");
    console.log("Items found:", queryResponse.Items?.length || 0);
    console.log("Items:", JSON.stringify(queryResponse.Items, null, 2));
    console.log("");

    // Test 2: Scan entire table to see all items
    console.log("Test 2: Scan entire table...");
    const scanCommand = new ScanCommand({
      TableName: PRESCRIPTIONS_TABLE,
    });

    const scanResponse = await docClient.send(scanCommand);
    console.log("✅ Scan successful!");
    console.log("Total items in table:", scanResponse.Items?.length || 0);
    console.log("All items:", JSON.stringify(scanResponse.Items, null, 2));
    console.log("");

    // Test 3: Check for device_id mismatches
    if (scanResponse.Items && scanResponse.Items.length > 0) {
      console.log("Test 3: Checking device_id values...");
      const deviceIds = [
        ...new Set(scanResponse.Items.map((item) => item.device_id)),
      ];
      console.log("Unique device_ids in table:", deviceIds);
      console.log("Expected device_id:", DEVICE_ID);
      console.log("Match:", deviceIds.includes(DEVICE_ID) ? "✅ YES" : "❌ NO");
    }
  } catch (error) {
    console.error("❌ Error:", error.message);
    console.error("Full error:", error);
  }
}

testQuery();
