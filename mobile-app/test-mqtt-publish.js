// Test script to verify MQTT publishing to AWS IoT Core
const {
  IoTDataPlaneClient,
  PublishCommand,
} = require("@aws-sdk/client-iot-data-plane");

// Load environment variables
require("dotenv").config();

const IOT_ENDPOINT = "agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com";
const DEVICE_ID = "pillbuddy-esp32-1";

const iotDataClient = new IoTDataPlaneClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
  endpoint: `https://${IOT_ENDPOINT}`,
});

async function testPublish() {
  const topic = `pillbuddy/cmd/${DEVICE_ID}`;
  const command = {
    action: "turn_on",
    slot: 1,
  };

  console.log(`📤 Publishing to topic: ${topic}`);
  console.log(`📦 Payload:`, command);

  try {
    const publishCommand = new PublishCommand({
      topic: topic,
      payload: new TextEncoder().encode(JSON.stringify(command)),
      qos: 1,
    });

    const result = await iotDataClient.send(publishCommand);
    console.log(`✅ Successfully published to ${topic}`);
    console.log(`Response:`, result);
  } catch (error) {
    console.error(`❌ Failed to publish:`, error);
    console.error(`Error details:`, error.message);
  }
}

testPublish();
