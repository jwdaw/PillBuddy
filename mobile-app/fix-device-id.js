/**
 * Script to fix device_id mismatch in DynamoDB
 * This will:
 * 1. Scan for items with wrong device_id
 * 2. Copy them with correct device_id
 * 3. Delete old items
 */

const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const {
  DynamoDBDocumentClient,
  ScanCommand,
  PutCommand,
  DeleteCommand,
} = require("@aws-sdk/lib-dynamodb");
require("dotenv").config();

const PRESCRIPTIONS_TABLE = "PillBuddy_Prescriptions";
const WRONG_DEVICE_ID = "pill buddy-esp32-1"; // with space
const CORRECT_DEVICE_ID = "pillbuddy-esp32-1"; // no space

// Initialize DynamoDB client
const client = new DynamoDBClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

const docClient = DynamoDBDocumentClient.from(client);

async function fixDeviceId() {
  console.log("=== Fixing device_id in DynamoDB ===");
  console.log("Wrong device_id:", WRONG_DEVICE_ID);
  console.log("Correct device_id:", CORRECT_DEVICE_ID);
  console.log("");

  try {
    // Step 1: Scan for items with wrong device_id
    console.log("Step 1: Scanning for items with wrong device_id...");
    const scanCommand = new ScanCommand({
      TableName: PRESCRIPTIONS_TABLE,
      FilterExpression: "device_id = :wrongId",
      ExpressionAttributeValues: {
        ":wrongId": WRONG_DEVICE_ID,
      },
    });

    const scanResponse = await docClient.send(scanCommand);
    const itemsToFix = scanResponse.Items || [];

    console.log(`Found ${itemsToFix.length} items to fix`);
    console.log("");

    if (itemsToFix.length === 0) {
      console.log("✅ No items to fix!");
      return;
    }

    // Step 2: Create new items with correct device_id
    console.log("Step 2: Creating items with correct device_id...");
    for (const item of itemsToFix) {
      const newItem = {
        ...item,
        device_id: CORRECT_DEVICE_ID,
      };

      const putCommand = new PutCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Item: newItem,
      });

      await docClient.send(putCommand);
      console.log(`✅ Created item for slot ${item.slot}`);
    }
    console.log("");

    // Step 3: Delete old items
    console.log("Step 3: Deleting old items...");
    for (const item of itemsToFix) {
      const deleteCommand = new DeleteCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Key: {
          device_id: WRONG_DEVICE_ID,
          slot: item.slot,
        },
      });

      await docClient.send(deleteCommand);
      console.log(`✅ Deleted old item for slot ${item.slot}`);
    }
    console.log("");

    console.log("🎉 All done! Device IDs fixed.");
    console.log("");
    console.log("Verifying fix...");

    // Verify
    const verifyCommand = new ScanCommand({
      TableName: PRESCRIPTIONS_TABLE,
    });
    const verifyResponse = await docClient.send(verifyCommand);
    console.log("All items in table:");
    console.log(JSON.stringify(verifyResponse.Items, null, 2));
  } catch (error) {
    console.error("❌ Error:", error.message);
    console.error("Full error:", error);
  }
}

fixDeviceId();
