import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, StyleSheet, Platform } from 'react-native';
import * as ScreenCapture from 'expo-screen-capture';

export default function RootLayout() {
  useEffect(() => {
    // Prevent screen capture (screenshots and recording) for privacy
    const enableScreenCapturePrevention = async () => {
      try {
        // Only works on native platforms, not web
        if (Platform.OS !== 'web') {
          await ScreenCapture.preventScreenCaptureAsync();
        }
      } catch (error) {
        console.log('Screen capture prevention not available:', error);
      }
    };

    enableScreenCapturePrevention();

    // Re-allow screen capture when app is closed
    return () => {
      if (Platform.OS !== 'web') {
        ScreenCapture.allowScreenCaptureAsync().catch(() => {});
      }
    };
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: '#FFFBF0' },
          animation: 'slide_from_right',
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFBF0',
  },
});
