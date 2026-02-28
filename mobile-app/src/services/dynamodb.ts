import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  UpdateCommand,
  DeleteCommand,
  QueryCommand,
} from "@aws-sdk/lib-dynamodb";
import { AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY } from "@env";

// AWS Configuration loaded from .env file
// See .env.example for required variables
// ⚠️ IMPORTANT: Never commit .env file to git

// Log environment variables on load (for debugging)
console.log("DynamoDB Service initializing...");
console.log("AWS_REGION:", AWS_REGION || "❌ NOT LOADED");
console.log(
  "AWS_ACCESS_KEY_ID:",
  AWS_ACCESS_KEY_ID ? "✅ Loaded" : "❌ NOT LOADED",
);
console.log(
  "AWS_SECRET_ACCESS_KEY:",
  AWS_SECRET_ACCESS_KEY ? "✅ Loaded" : "❌ NOT LOADED",
);

// Initialize DynamoDB client
const client = new DynamoDBClient({
  region: AWS_REGION,
  credentials: {
    accessKeyId: AWS_ACCESS_KEY_ID,
    secretAccessKey: AWS_SECRET_ACCESS_KEY,
  },
});

const docClient = DynamoDBDocumentClient.from(client);

// Table names - these match the CloudFormation stack output
const DEVICES_TABLE = "PillBuddy_Devices";
const PRESCRIPTIONS_TABLE = "PillBuddy_Prescriptions";

export interface Prescription {
  device_id: string;
  slot: 1 | 2 | 3;
  prescription_name: string;
  pill_count: number;
  initial_count: number;
  has_refills: boolean;
  created_at: number;
  updated_at: number;
  removal_timestamp?: number;
  last_taken_date?: string; // ISO date string (YYYY-MM-DD) of last pill taken
}

export interface DeviceState {
  device_id: string;
  slots: {
    [key: string]: {
      in_holder: boolean;
      last_state_change: number;
    };
  };
  last_seen: number;
}

export const DynamoDBService = {
  // Get device state
  async getDeviceState(deviceId: string): Promise<DeviceState | null> {
    try {
      const command = new GetCommand({
        TableName: DEVICES_TABLE,
        Key: { device_id: deviceId },
      });

      const response = await docClient.send(command);
      return (response.Item as DeviceState) || null;
    } catch (error) {
      console.error("Error getting device state:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to get device state: ${error.message}`);
      }
      throw new Error("Failed to get device state");
    }
  },

  // Get all prescriptions for a device
  async getPrescriptions(deviceId: string): Promise<Prescription[]> {
    try {
      const command = new QueryCommand({
        TableName: PRESCRIPTIONS_TABLE,
        KeyConditionExpression: "device_id = :deviceId",
        ExpressionAttributeValues: {
          ":deviceId": deviceId,
        },
      });

      const response = await docClient.send(command);
      return (response.Items as Prescription[]) || [];
    } catch (error) {
      console.error("Error getting prescriptions:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to get prescriptions: ${error.message}`);
      }
      throw new Error("Failed to get prescriptions");
    }
  },

  // Get a single prescription
  async getPrescription(
    deviceId: string,
    slot: number,
  ): Promise<Prescription | null> {
    try {
      const command = new GetCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Key: {
          device_id: deviceId,
          slot: slot,
        },
      });

      const response = await docClient.send(command);
      return (response.Item as Prescription) || null;
    } catch (error) {
      console.error("Error getting prescription:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to get prescription: ${error.message}`);
      }
      throw new Error("Failed to get prescription");
    }
  },

  // Create or update a prescription
  async savePrescription(
    prescription: Omit<Prescription, "created_at" | "updated_at">,
  ): Promise<void> {
    try {
      const now = Date.now();
      const command = new PutCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Item: {
          ...prescription,
          created_at: now,
          updated_at: now,
        },
      });

      await docClient.send(command);
    } catch (error) {
      console.error("Error saving prescription:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to save prescription: ${error.message}`);
      }
      throw new Error("Failed to save prescription");
    }
  },

  // Update prescription pill count
  async updatePillCount(
    deviceId: string,
    slot: number,
    pillCount: number,
  ): Promise<void> {
    try {
      const command = new UpdateCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Key: {
          device_id: deviceId,
          slot: slot,
        },
        UpdateExpression:
          "SET pill_count = :pillCount, updated_at = :updatedAt",
        ExpressionAttributeValues: {
          ":pillCount": pillCount,
          ":updatedAt": Date.now(),
        },
      });

      await docClient.send(command);
    } catch (error) {
      console.error("Error updating pill count:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to update pill count: ${error.message}`);
      }
      throw new Error("Failed to update pill count");
    }
  },

  // Delete a prescription
  async deletePrescription(deviceId: string, slot: number): Promise<void> {
    try {
      const command = new DeleteCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Key: {
          device_id: deviceId,
          slot: slot,
        },
      });

      await docClient.send(command);
    } catch (error) {
      console.error("Error deleting prescription:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to delete prescription: ${error.message}`);
      }
      throw new Error("Failed to delete prescription");
    }
  },

  // Mark pill as taken for today
  async markPillTaken(deviceId: string, slot: number): Promise<void> {
    try {
      const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD format
      const command = new UpdateCommand({
        TableName: PRESCRIPTIONS_TABLE,
        Key: {
          device_id: deviceId,
          slot: slot,
        },
        UpdateExpression:
          "SET last_taken_date = :today, updated_at = :updatedAt",
        ExpressionAttributeValues: {
          ":today": today,
          ":updatedAt": Date.now(),
        },
      });

      await docClient.send(command);
    } catch (error) {
      console.error("Error marking pill taken:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to mark pill taken: ${error.message}`);
      }
      throw new Error("Failed to mark pill taken");
    }
  },

  // Reset daily status (for demo purposes)
  async resetDailyStatus(deviceId: string): Promise<void> {
    try {
      // Get all prescriptions for the device
      const prescriptions = await this.getPrescriptions(deviceId);

      // Reset last_taken_date for each prescription
      const updatePromises = prescriptions.map((prescription) => {
        const command = new UpdateCommand({
          TableName: PRESCRIPTIONS_TABLE,
          Key: {
            device_id: deviceId,
            slot: prescription.slot,
          },
          UpdateExpression:
            "REMOVE last_taken_date SET updated_at = :updatedAt",
          ExpressionAttributeValues: {
            ":updatedAt": Date.now(),
          },
        });
        return docClient.send(command);
      });

      await Promise.all(updatePromises);
    } catch (error) {
      console.error("Error resetting daily status:", error);
      if (error instanceof Error) {
        throw new Error(`Failed to reset daily status: ${error.message}`);
      }
      throw new Error("Failed to reset daily status");
    }
  },

  // Check if pill was taken today
  hasTakenPillToday(prescription: Prescription): boolean {
    if (!prescription.last_taken_date) return false;
    const today = new Date().toISOString().split("T")[0];
    return prescription.last_taken_date === today;
  },
};
