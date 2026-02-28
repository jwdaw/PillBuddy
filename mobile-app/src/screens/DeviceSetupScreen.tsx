import React, { useState, useEffect } from "react";
import { View, Text, TextInput, Button, StyleSheet, Alert } from "react-native";
import { StackNavigationProp } from "@react-navigation/stack";
import { RootStackParamList } from "../navigation/AppNavigator";
import { StorageService } from "../services/storage";
import { DynamoDBService } from "../services/dynamodb";

type DeviceSetupScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  "DeviceSetup"
>;

interface Props {
  navigation: DeviceSetupScreenNavigationProp;
}

export default function DeviceSetupScreen({ navigation }: Props) {
  const [deviceId, setDeviceId] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if device ID is already saved
    checkExistingDeviceId();
  }, []);

  const checkExistingDeviceId = async () => {
    try {
      const savedDeviceId = await StorageService.getDeviceId();
      if (savedDeviceId) {
        // Navigate to dashboard if device ID exists
        navigation.replace("Dashboard");
      }
    } catch (error) {
      console.error("Error checking device ID:", error);
    }
  };

  const handleContinue = async () => {
    if (!deviceId.trim()) {
      Alert.alert("Error", "Please enter a device ID");
      return;
    }

    setLoading(true);
    try {
      // Validate device exists in DynamoDB
      const deviceState = await DynamoDBService.getDeviceState(deviceId);

      if (!deviceState) {
        Alert.alert(
          "Error",
          "Device not found. Please check the device ID and try again.",
        );
        setLoading(false);
        return;
      }

      // Save device ID
      await StorageService.setDeviceId(deviceId);

      // Navigate to dashboard
      navigation.replace("Dashboard");
    } catch (error) {
      console.error("Error validating device:", error);
      Alert.alert(
        "Error",
        "Failed to validate device. Please check your connection and try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Welcome to PillBuddy</Text>
      <Text style={styles.subtitle}>Enter your device ID to get started</Text>

      <TextInput
        style={styles.input}
        placeholder="Device ID (e.g., pillbuddy_001)"
        value={deviceId}
        onChangeText={setDeviceId}
        autoCapitalize="none"
        autoCorrect={false}
      />

      <Button
        title={loading ? "Validating..." : "Continue"}
        onPress={handleContinue}
        disabled={loading}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: "center",
    backgroundColor: "#fff",
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 10,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 16,
    color: "#666",
    marginBottom: 30,
    textAlign: "center",
  },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
    fontSize: 16,
  },
});
