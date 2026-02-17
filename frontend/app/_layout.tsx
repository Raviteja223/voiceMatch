import { useEffect, useRef } from 'react';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, StyleSheet, Platform } from 'react-native';
import * as ScreenCapture from 'expo-screen-capture';
import * as Notifications from 'expo-notifications';
import {
  registerForPushNotifications,
  addNotificationResponseListener,
} from '../src/notifications';

export default function RootLayout() {
  const router = useRouter();
  const responseListenerRef = useRef<Notifications.Subscription>();

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

    // Register for push notifications
    registerForPushNotifications();

    // Handle notification taps - navigate to the right screen
    responseListenerRef.current = addNotificationResponseListener((response) => {
      const data = response.notification.request.content.data;
      if (data?.type === 'incoming_call') {
        // Navigate to listener dashboard where the incoming call modal will show
        router.push('/listener/dashboard');
      }
    });

    // Re-allow screen capture when app is closed
    return () => {
      if (Platform.OS !== 'web') {
        ScreenCapture.allowScreenCaptureAsync().catch(() => {});
      }
      if (responseListenerRef.current) {
        responseListenerRef.current.remove();
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
