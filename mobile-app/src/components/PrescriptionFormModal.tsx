import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TextInput,
  TouchableOpacity,
  Switch,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { Prescription } from "../services/dynamodb";

interface PrescriptionFormModalProps {
  visible: boolean;
  slotNumber: 1 | 2 | 3;
  existingPrescription?: Prescription | null;
  onSave: (data: PrescriptionFormData) => Promise<void>;
  onCancel: () => void;
}

export interface PrescriptionFormData {
  prescription_name: string;
  pill_count: number;
  has_refills: boolean;
}

export default function PrescriptionFormModal({
  visible,
  slotNumber,
  existingPrescription,
  onSave,
  onCancel,
}: PrescriptionFormModalProps) {
  const [prescriptionName, setPrescriptionName] = useState("");
  const [pillCount, setPillCount] = useState("");
  const [hasRefills, setHasRefills] = useState(false);
  const [errors, setErrors] = useState<{
    prescriptionName?: string;
    pillCount?: string;
  }>({});
  const [saving, setSaving] = useState(false);

  // Reset form when modal opens or prescription changes
  useEffect(() => {
    if (visible) {
      if (existingPrescription) {
        // Edit mode - pre-populate with existing values
        setPrescriptionName(existingPrescription.prescription_name);
        setPillCount(existingPrescription.pill_count.toString());
        setHasRefills(existingPrescription.has_refills);
      } else {
        // New prescription mode - clear form
        setPrescriptionName("");
        setPillCount("");
        setHasRefills(false);
      }
      setErrors({});
    }
  }, [visible, existingPrescription]);

  const validate = (): boolean => {
    const newErrors: { prescriptionName?: string; pillCount?: string } = {};

    // Validate prescription name
    if (!prescriptionName.trim()) {
      newErrors.prescriptionName = "Prescription name is required";
    }

    // Validate pill count
    const pillCountNum = parseInt(pillCount, 10);
    if (!pillCount.trim()) {
      newErrors.pillCount = "Pill count is required";
    } else if (isNaN(pillCountNum)) {
      newErrors.pillCount = "Pill count must be a number";
    } else if (pillCountNum <= 0) {
      newErrors.pillCount = "Pill count must be a positive number";
    } else if (!Number.isInteger(pillCountNum)) {
      newErrors.pillCount = "Pill count must be a whole number";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      return;
    }

    setSaving(true);
    try {
      await onSave({
        prescription_name: prescriptionName.trim(),
        pill_count: parseInt(pillCount, 10),
        has_refills: hasRefills,
      });
      // Success - modal will be closed by parent component
    } catch (error) {
      console.error("Error saving prescription:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unable to save prescription";
      Alert.alert(
        "Save Failed",
        `${errorMessage}. Please check your connection and try again.`,
      );
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (!saving) {
      onCancel();
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={handleCancel}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.modalOverlay}
      >
        <View style={styles.modalContainer}>
          <ScrollView style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {existingPrescription ? "Edit" : "Setup"} Prescription - Slot{" "}
              {slotNumber}
            </Text>

            {/* Prescription Name Input */}
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Prescription Name *</Text>
              <TextInput
                style={[
                  styles.input,
                  errors.prescriptionName && styles.inputError,
                ]}
                value={prescriptionName}
                onChangeText={setPrescriptionName}
                placeholder="e.g., Aspirin, Vitamin D"
                editable={!saving}
              />
              {errors.prescriptionName && (
                <Text style={styles.errorText}>{errors.prescriptionName}</Text>
              )}
            </View>

            {/* Pill Count Input */}
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Pill Count *</Text>
              <TextInput
                style={[styles.input, errors.pillCount && styles.inputError]}
                value={pillCount}
                onChangeText={setPillCount}
                placeholder="e.g., 30"
                keyboardType="number-pad"
                editable={!saving}
              />
              {errors.pillCount && (
                <Text style={styles.errorText}>{errors.pillCount}</Text>
              )}
            </View>

            {/* Has Refills Toggle */}
            <View style={styles.inputGroup}>
              <View style={styles.switchRow}>
                <Text style={styles.label}>Has Refills</Text>
                <Switch
                  value={hasRefills}
                  onValueChange={setHasRefills}
                  disabled={saving}
                />
              </View>
              <Text style={styles.helpText}>
                Turn on if you can get refills for this prescription
              </Text>
            </View>

            {/* Buttons */}
            <View style={styles.buttonContainer}>
              <TouchableOpacity
                style={[styles.button, styles.cancelButton]}
                onPress={handleCancel}
                disabled={saving}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.button,
                  styles.saveButton,
                  saving && styles.saveButtonDisabled,
                ]}
                onPress={handleSave}
                disabled={saving}
              >
                <Text style={styles.saveButtonText}>
                  {saving ? "Saving..." : "Save"}
                </Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    justifyContent: "flex-end",
  },
  modalContainer: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: "80%",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 8,
  },
  modalContent: {
    padding: 24,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 24,
    letterSpacing: 0.3,
  },
  inputGroup: {
    marginBottom: 24,
  },
  label: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    marginBottom: 10,
  },
  input: {
    borderWidth: 1,
    borderColor: "#DDD",
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    backgroundColor: "#F9F9F9",
  },
  inputError: {
    borderColor: "#F44336",
    backgroundColor: "#FFEBEE",
  },
  errorText: {
    color: "#F44336",
    fontSize: 13,
    marginTop: 6,
    fontWeight: "500",
  },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  helpText: {
    fontSize: 13,
    color: "#666",
    marginTop: 6,
    lineHeight: 18,
  },
  buttonContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 32,
    marginBottom: 20,
    gap: 12,
  },
  button: {
    flex: 1,
    padding: 16,
    borderRadius: 10,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 3,
    elevation: 3,
  },
  cancelButton: {
    backgroundColor: "#F5F5F5",
  },
  cancelButtonText: {
    color: "#666",
    fontSize: 16,
    fontWeight: "600",
  },
  saveButton: {
    backgroundColor: "#2196F3",
  },
  saveButtonDisabled: {
    backgroundColor: "#BBDEFB",
    opacity: 0.7,
  },
  saveButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
