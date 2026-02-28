import { AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY } from "@env";
import {
  IoTDataPlaneClient,
  PublishCommand,
} from "@aws-sdk/client-iot-data-plane";

// AWS IoT Core endpoint
const IOT_ENDPOINT = "agmz51s8c5jwp-ats.iot.us-east-1.amazonaws.com";

// MQTT topics
const COMMAND_TOPIC_PREFIX = "pillbuddy/cmd/";

// Initialize IoT Data Plane client for publishing
const iotDataClient = new IoTDataPlaneClient({
  region: AWS_REGION,
  credentials: {
    accessKeyId: AWS_ACCESS_KEY_ID,
    secretAccessKey: AWS_SECRET_ACCESS_KEY,
  },
  endpoint: `https://${IOT_ENDPOINT}`,
});

export interface LEDCommand {
  action: "turn_on" | "turn_off";
  slot: 1 | 2 | 3;
}

class MQTTService {
  /**
   * Publish LED control command using AWS IoT Data Plane API
   */
  async publishLEDCommand(
    deviceId: string,
    command: LEDCommand,
  ): Promise<void> {
    const topic = `${COMMAND_TOPIC_PREFIX}${deviceId}`;
    const payload = JSON.stringify(command);

    console.log(`📤 Publishing to ${topic}:`, command);

    try {
      const publishCommand = new PublishCommand({
        topic: topic,
        payload: new TextEncoder().encode(payload),
        qos: 1,
      });

      await iotDataClient.send(publishCommand);
      console.log(
        `✅ Published LED command via IoT Data API to ${topic}:`,
        command,
      );
    } catch (error) {
      console.error(`Failed to publish via IoT Data API:`, error);
      throw new Error("Cannot publish: IoT Data API error");
    }
  }

  /**
   * Turn on LED for a specific slot
   */
  async turnOnLED(deviceId: string, slot: 1 | 2 | 3): Promise<void> {
    const command: LEDCommand = {
      action: "turn_on",
      slot: slot,
    };
    await this.publishLEDCommand(deviceId, command);
  }

  /**
   * Turn off LED for a specific slot
   */
  async turnOffLED(deviceId: string, slot: 1 | 2 | 3): Promise<void> {
    const command: LEDCommand = {
      action: "turn_off",
      slot: slot,
    };
    await this.publishLEDCommand(deviceId, command);
  }

  /**
   * Turn off all LEDs
   */
  async turnOffAllLEDs(deviceId: string): Promise<void> {
    await Promise.all([
      this.turnOffLED(deviceId, 1),
      this.turnOffLED(deviceId, 2),
      this.turnOffLED(deviceId, 3),
    ]);
  }
}

// Export singleton instance
export default new MQTTService();
