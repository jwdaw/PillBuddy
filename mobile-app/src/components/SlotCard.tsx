import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";

interface SlotCardProps {
  slotNumber: 1 | 2 | 3;
  prescriptionName?: string;
  pillCount?: number;
  inHolder: boolean;
  takenToday?: boolean;
  isUpdating?: boolean;
  onPress?: () => void;
  onPillCountChange?: (newCount: number) => void;
}

export default function SlotCard({
  slotNumber,
  prescriptionName,
  pillCount,
  inHolder,
  takenToday = false,
  isUpdating = false,
  onPress,
  onPillCountChange,
}: SlotCardProps) {
  // Determine card background color based on state
  const getCardColor = () => {
    if (!prescriptionName) {
      return "#F5F5F5"; // Light gray for empty slot
    }
    if (pillCount !== undefined && pillCount < 5) {
      return "#FFF8E1"; // Soft yellow for needs refill
    }
    if (inHolder) {
      return "#E8F5E9"; // Soft green for bottle present
    }
    return "#FFFFFF"; // White default
  };

  // Determine status indicator
  const getStatusIndicator = () => {
    if (!prescriptionName) {
      return { text: "Empty Slot", color: "#757575" };
    }
    if (inHolder) {
      return { text: "✓ Bottle Present", color: "#4CAF50" };
    }
    return { text: "○ Bottle Removed", color: "#FF9800" };
  };

  const status = getStatusIndicator();
  const cardColor = getCardColor();

  return (
    <TouchableOpacity
      style={[styles.card, { backgroundColor: cardColor }]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.header}>
        <Text style={styles.slotNumber}>Slot {slotNumber}</Text>
        <Text style={[styles.statusText, { color: status.color }]}>
          {status.text}
        </Text>
      </View>

      {prescriptionName ? (
        <View style={styles.content}>
          <Text style={styles.prescriptionName}>{prescriptionName}</Text>
          {takenToday && (
            <View style={styles.takenTodayBadge}>
              <Text style={styles.takenTodayText}>✓ Taken Today</Text>
            </View>
          )}
          <View style={styles.pillCountRow}>
            <Text style={styles.pillCount}>
              {pillCount !== undefined ? `${pillCount} pills` : "0 pills"}
            </Text>
            {onPillCountChange && (
              <View style={styles.pillCountControls}>
                {isUpdating ? (
                  <ActivityIndicator size="small" color="#2196F3" />
                ) : (
                  <>
                    <TouchableOpacity
                      style={styles.pillCountButton}
                      onPress={(e) => {
                        e.stopPropagation();
                        const currentCount = pillCount || 0;
                        if (currentCount > 0) {
                          onPillCountChange(currentCount - 1);
                        }
                      }}
                    >
                      <Text style={styles.pillCountButtonText}>−</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.pillCountButton}
                      onPress={(e) => {
                        e.stopPropagation();
                        const currentCount = pillCount || 0;
                        onPillCountChange(currentCount + 1);
                      }}
                    >
                      <Text style={styles.pillCountButtonText}>+</Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            )}
          </View>
          {pillCount !== undefined && pillCount < 5 && (
            <Text style={styles.refillWarning}>⚠️ Refill Needed</Text>
          )}
        </View>
      ) : (
        <View style={styles.content}>
          <Text style={styles.emptyText}>No prescription configured</Text>
          <Text style={styles.tapToSetup}>Tap to set up</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 20,
    padding: 24,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
    borderWidth: 0,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },
  slotNumber: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FF6B35",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  statusText: {
    fontSize: 13,
    fontWeight: "600",
  },
  content: {
    marginTop: 8,
  },
  prescriptionName: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1A1A1A",
    marginBottom: 14,
    letterSpacing: -0.3,
  },
  pillCount: {
    fontSize: 17,
    color: "#666",
    marginBottom: 4,
    fontWeight: "500",
  },
  pillCountRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  pillCountControls: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  pillCountButton: {
    backgroundColor: "#FF6B35",
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#FF6B35",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  pillCountButtonText: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "bold",
    lineHeight: 22,
  },
  refillWarning: {
    fontSize: 15,
    color: "#FF4444",
    fontWeight: "600",
    marginTop: 10,
  },
  emptyText: {
    fontSize: 16,
    color: "#999",
    fontStyle: "italic",
  },
  tapToSetup: {
    fontSize: 14,
    color: "#FF6B35",
    marginTop: 6,
    fontWeight: "600",
  },
  takenTodayBadge: {
    backgroundColor: "#00C853",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    alignSelf: "flex-start",
    marginBottom: 12,
  },
  takenTodayText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
});
