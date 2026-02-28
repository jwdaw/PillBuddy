import AsyncStorage from "@react-native-async-storage/async-storage";

const DEVICE_ID_KEY = "device_id";
const PRESCRIPTIONS_CACHE_PREFIX = "prescriptions_";
const DEVICE_STATE_CACHE_PREFIX = "device_state_";

export const StorageService = {
  // Device ID
  async setDeviceId(deviceId: string): Promise<void> {
    try {
      await AsyncStorage.setItem(DEVICE_ID_KEY, deviceId);
    } catch (error) {
      console.error("Error saving device ID:", error);
      throw error;
    }
  },

  async getDeviceId(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(DEVICE_ID_KEY);
    } catch (error) {
      console.error("Error getting device ID:", error);
      throw error;
    }
  },

  async clearDeviceId(): Promise<void> {
    try {
      await AsyncStorage.removeItem(DEVICE_ID_KEY);
    } catch (error) {
      console.error("Error clearing device ID:", error);
      throw error;
    }
  },

  // Cache prescriptions
  async cachePrescriptions(
    deviceId: string,
    prescriptions: any[],
  ): Promise<void> {
    try {
      const key = `${PRESCRIPTIONS_CACHE_PREFIX}${deviceId}`;
      await AsyncStorage.setItem(key, JSON.stringify(prescriptions));
    } catch (error) {
      console.error("Error caching prescriptions:", error);
      throw error;
    }
  },

  async getCachedPrescriptions(deviceId: string): Promise<any[] | null> {
    try {
      const key = `${PRESCRIPTIONS_CACHE_PREFIX}${deviceId}`;
      const data = await AsyncStorage.getItem(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error("Error getting cached prescriptions:", error);
      throw error;
    }
  },

  // Cache device state
  async cacheDeviceState(deviceId: string, state: any): Promise<void> {
    try {
      const key = `${DEVICE_STATE_CACHE_PREFIX}${deviceId}`;
      await AsyncStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      console.error("Error caching device state:", error);
      throw error;
    }
  },

  async getCachedDeviceState(deviceId: string): Promise<any | null> {
    try {
      const key = `${DEVICE_STATE_CACHE_PREFIX}${deviceId}`;
      const data = await AsyncStorage.getItem(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error("Error getting cached device state:", error);
      throw error;
    }
  },

  // Clear all cache
  async clearCache(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(
        (key) =>
          key.startsWith(PRESCRIPTIONS_CACHE_PREFIX) ||
          key.startsWith(DEVICE_STATE_CACHE_PREFIX),
      );
      await AsyncStorage.multiRemove(cacheKeys);
    } catch (error) {
      console.error("Error clearing cache:", error);
      throw error;
    }
  },
};
