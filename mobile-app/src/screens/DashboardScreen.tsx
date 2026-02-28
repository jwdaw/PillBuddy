import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  TouchableOpacity,
  AppState,
  AppStateStatus,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import { StackNavigationProp } from "@react-navigation/stack";
import { RootStackParamList } from "../navigation/AppNavigator";
import { StorageService } from "../services/storage";
import {
  DynamoDBService,
  Prescription,
  DeviceState,
} from "../services/dynamodb";
import MQTTService from "../services/mqtt";
import SlotCard from "../components/SlotCard";
import PrescriptionFormModal, {
  PrescriptionFormData,
} from "../components/PrescriptionFormModal";

type DashboardScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  "Dashboard"
>;

interface Props {
  navigation: DashboardScreenNavigationProp;
}

// Hardcoded device ID for hackathon - no auth needed
// This matches the ESP32 device configured in pillBuddy/sdkconfig
const DEVICE_ID = "pillbuddy-esp32-1";

export default function DashboardScreen({ navigation }: Props) {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [deviceState, setDeviceState] = useState<DeviceState | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatingSlot, setUpdatingSlot] = useState<number | null>(null);

  // Modal state
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<1 | 2 | 3 | null>(null);

  // Refs for polling
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const appStateRef = useRef<AppStateStatus>(AppState.currentState);

  useEffect(() => {
    // Load data immediately on mount
    console.log("DashboardScreen mounted, loading data...");
    fetchData(DEVICE_ID).catch((err) => {
      console.error("Error in initial fetch:", err);
      setError(err.message || "Failed to load data");
    });

    // Set up app state listener
    const subscription = AppState.addEventListener(
      "change",
      handleAppStateChange,
    );

    return () => {
      // Clean up polling interval and listener on unmount
      stopPolling();
      subscription.remove();
    };
  }, []);

  useEffect(() => {
    // Start polling
    startPolling();

    return () => {
      stopPolling();
    };
  }, []);

  const handleAppStateChange = (nextAppState: AppStateStatus) => {
    if (
      appStateRef.current.match(/inactive|background/) &&
      nextAppState === "active"
    ) {
      // App has come to the foreground - restart polling
      fetchData(DEVICE_ID);
      startPolling();
    } else if (nextAppState.match(/inactive|background/)) {
      // App is going to background - stop polling
      stopPolling();
    }

    appStateRef.current = nextAppState;
  };

  const handleResetDailyStatus = async () => {
    try {
      console.log("Resetting daily status for demo...");
      await DynamoDBService.resetDailyStatus(DEVICE_ID);

      // Turn on LEDs for all configured prescriptions
      const configuredSlots = prescriptions
        .filter((p) => p.prescription_name)
        .map((p) => p.slot);

      for (const slot of configuredSlots) {
        try {
          await MQTTService.turnOnLED(DEVICE_ID, slot);
          console.log(`✅ LED turned on for slot ${slot}`);
        } catch (error) {
          console.error(`Failed to turn on LED for slot ${slot}:`, error);
        }
      }

      // Refresh data to update UI
      await fetchDataSilently(DEVICE_ID);

      Alert.alert(
        "Demo Reset",
        `Daily pill status reset. LEDs turned on for ${configuredSlots.length} slot(s).`,
      );
    } catch (error) {
      console.error("Error resetting daily status:", error);
      Alert.alert("Reset Error", "Failed to reset daily status.");
    }
  };

  const startPolling = () => {
    // Clear any existing interval
    stopPolling();

    // Set up new polling interval (0.05 seconds = 50ms)
    pollingIntervalRef.current = setInterval(() => {
      fetchDataSilently(DEVICE_ID);
    }, 50); // 0.05 seconds (50 milliseconds)
  };

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  const fetchDataSilently = async (deviceId: string) => {
    // Fetch data without showing loading indicators
    try {
      console.log("🔄 POLLING DYNAMODB (background)...");
      const [prescriptionsData, stateData] = await Promise.all([
        DynamoDBService.getPrescriptions(deviceId),
        DynamoDBService.getDeviceState(deviceId),
      ]);

      console.log("✅ POLL SUCCESS - Updated data received");

      setPrescriptions(prescriptionsData);
      setDeviceState(stateData);
      setLastUpdated(new Date());

      // Cache the data
      await StorageService.cachePrescriptions(deviceId, prescriptionsData);
      await StorageService.cacheDeviceState(deviceId, stateData);
    } catch (error) {
      console.error("❌ POLL ERROR:", error);
      // Silently fail - don't show alerts during background polling
    }
  };

  const loadDeviceData = async () => {
    try {
      await fetchData(DEVICE_ID);
    } catch (error) {
      console.error("Error loading device data:", error);
      Alert.alert("Error", "Failed to load device data");
    }
  };

  const fetchData = async (deviceId: string) => {
    setLoading(true);
    setError(null);
    try {
      console.log("📡 FETCHING FROM DYNAMODB for device:", deviceId);
      // Fetch prescriptions and device state
      const [prescriptionsData, stateData] = await Promise.all([
        DynamoDBService.getPrescriptions(deviceId),
        DynamoDBService.getDeviceState(deviceId),
      ]);

      console.log(
        "✅ DYNAMODB RESPONSE - Prescriptions:",
        JSON.stringify(prescriptionsData, null, 2),
      );
      console.log(
        "✅ DYNAMODB RESPONSE - Device State:",
        JSON.stringify(stateData, null, 2),
      );

      setPrescriptions(prescriptionsData);
      setDeviceState(stateData);
      setLastUpdated(new Date());

      // Cache the data
      await StorageService.cachePrescriptions(deviceId, prescriptionsData);
      await StorageService.cacheDeviceState(deviceId, stateData);
      console.log("💾 Data cached to local storage");
    } catch (error) {
      console.error("❌ ERROR fetching from DynamoDB:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unable to connect to server";
      setError(errorMessage);

      // Try to load from cache
      console.log("🔄 Attempting to load from cache...");
      const cachedPrescriptions =
        await StorageService.getCachedPrescriptions(deviceId);
      const cachedState = await StorageService.getCachedDeviceState(deviceId);

      if (cachedPrescriptions) {
        console.log(
          "📦 LOADED FROM CACHE - Prescriptions:",
          cachedPrescriptions,
        );
        setPrescriptions(cachedPrescriptions);
      }
      if (cachedState) {
        console.log("📦 LOADED FROM CACHE - Device State:", cachedState);
        setDeviceState(cachedState);
      }

      Alert.alert(
        "Connection Error",
        "Unable to fetch latest data. Showing cached data if available.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchData(DEVICE_ID);
  };

  const handleSlotPress = (slotNumber: 1 | 2 | 3) => {
    setSelectedSlot(slotNumber);
    setModalVisible(true);
  };

  const handleModalCancel = () => {
    setModalVisible(false);
    setSelectedSlot(null);
  };

  const handleModalSave = async (data: PrescriptionFormData) => {
    if (selectedSlot === null) {
      Alert.alert("Error", "Invalid slot selection");
      return;
    }

    try {
      // Check if we're editing an existing prescription
      const existingPrescription = prescriptions.find(
        (p) => p.slot === selectedSlot,
      );

      // Prepare prescription data
      const prescriptionData: Omit<Prescription, "created_at" | "updated_at"> =
        {
          device_id: DEVICE_ID,
          slot: selectedSlot,
          prescription_name: data.prescription_name,
          pill_count: data.pill_count,
          initial_count: existingPrescription
            ? existingPrescription.initial_count
            : data.pill_count, // Preserve initial_count on edit, set to pill_count on create
          has_refills: data.has_refills,
        };

      // Save to DynamoDB
      await DynamoDBService.savePrescription(prescriptionData);

      // Show success message
      Alert.alert(
        "Success",
        existingPrescription
          ? "Prescription updated successfully"
          : "Prescription saved successfully! Please place the bottle in the indicated slot.",
      );

      // Close modal
      setModalVisible(false);
      setSelectedSlot(null);

      // Refresh device state
      await fetchData(DEVICE_ID);
    } catch (error) {
      console.error("Error saving prescription:", error);
      Alert.alert(
        "Save Failed",
        "Failed to save prescription. Please check your connection and try again.",
      );
      throw error; // Let the modal handle the error display
    }
  };

  const handlePillCountChange = async (
    slotNumber: 1 | 2 | 3,
    newCount: number,
  ) => {
    try {
      console.log(
        `Updating pill count for slot ${slotNumber} to ${newCount}...`,
      );

      // Set loading state for this specific slot
      setUpdatingSlot(slotNumber);

      // Update in DynamoDB
      await DynamoDBService.updatePillCount(DEVICE_ID, slotNumber, newCount);

      // Update local state immediately for responsive UI
      setPrescriptions((prev) =>
        prev.map((p) =>
          p.slot === slotNumber ? { ...p, pill_count: newCount } : p,
        ),
      );

      console.log(`✅ Pill count updated successfully`);

      // Refresh data from DynamoDB to ensure consistency
      await fetchDataSilently(DEVICE_ID);
    } catch (error) {
      console.error("Error updating pill count:", error);
      Alert.alert(
        "Update Failed",
        "Failed to update pill count. Please check your connection and try again.",
      );
    } finally {
      setUpdatingSlot(null);
    }
  };

  const getSelectedPrescription = (): Prescription | null => {
    if (selectedSlot === null) return null;
    return prescriptions.find((p) => p.slot === selectedSlot) || null;
  };

  const renderSlot = (slotNumber: 1 | 2 | 3) => {
    const prescription = prescriptions.find((p) => p.slot === slotNumber);
    const slotState = deviceState?.slots[slotNumber.toString()];
    const inHolder = slotState?.in_holder ?? false;
    const isUpdating = updatingSlot === slotNumber;
    const takenToday = prescription
      ? DynamoDBService.hasTakenPillToday(prescription)
      : false;

    return (
      <SlotCard
        key={slotNumber}
        slotNumber={slotNumber}
        prescriptionName={prescription?.prescription_name}
        pillCount={prescription?.pill_count}
        inHolder={inHolder}
        takenToday={takenToday}
        isUpdating={isUpdating}
        onPress={() => handleSlotPress(slotNumber)}
        onPillCountChange={
          prescription
            ? (newCount) => handlePillCountChange(slotNumber, newCount)
            : undefined
        }
      />
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        style={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>PillBuddy</Text>
          <Text style={styles.deviceId}>Device: {DEVICE_ID}</Text>
        </View>

        {error && (
          <View style={styles.errorBanner}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
            <Text style={styles.errorSubtext}>
              Pull down to refresh or check your connection
            </Text>
          </View>
        )}

        {loading && !refreshing && prescriptions.length === 0 && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#2196F3" />
            <Text style={styles.loadingText}>Loading device data...</Text>
          </View>
        )}

        <View style={styles.slotsContainer}>
          {renderSlot(1)}
          {renderSlot(2)}
          {renderSlot(3)}
        </View>

        {/* Demo reset button - subtle and at bottom */}
        <View style={styles.demoResetContainer}>
          <TouchableOpacity
            style={styles.demoResetButton}
            onPress={handleResetDailyStatus}
          >
            <Text style={styles.demoResetText}>Reset Daily Status (Demo)</Text>
          </TouchableOpacity>
        </View>

        {/* Prescription Form Modal */}
        <PrescriptionFormModal
          visible={modalVisible}
          slotNumber={selectedSlot || 1}
          existingPrescription={getSelectedPrescription()}
          onSave={handleModalSave}
          onCancel={handleModalCancel}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#FF6B35",
  },
  container: {
    flex: 1,
    backgroundColor: "#FAFAFA",
  },
  header: {
    padding: 24,
    paddingTop: 20,
    paddingBottom: 28,
    backgroundColor: "#FF6B35",
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },
  title: {
    fontSize: 32,
    fontWeight: "800",
    color: "#FFFFFF",
    marginBottom: 4,
    letterSpacing: -0.5,
  },
  deviceId: {
    fontSize: 13,
    color: "#FFE5DC",
    fontWeight: "600",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  errorBanner: {
    backgroundColor: "#FFF3F3",
    padding: 18,
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: "#FF4444",
  },
  errorText: {
    color: "#CC0000",
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 4,
  },
  errorSubtext: {
    color: "#CC0000",
    fontSize: 12,
    opacity: 0.8,
  },
  loadingContainer: {
    padding: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: "#666",
  },
  slotsContainer: {
    padding: 16,
  },
  demoResetContainer: {
    padding: 16,
    paddingTop: 8,
    alignItems: "center",
  },
  demoResetButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    backgroundColor: "transparent",
  },
  demoResetText: {
    fontSize: 11,
    color: "#999",
    textAlign: "center",
  },
});
