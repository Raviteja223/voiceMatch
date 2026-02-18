import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import { AppState } from 'react-native';
import api from '../../src/api';

export default function ListenerLayout() {
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Send heartbeat immediately when listener enters the listener section
    api.post('/listeners/heartbeat').catch(() => {});

    // Keep heartbeat running every 30 seconds across all listener tabs
    heartbeatRef.current = setInterval(() => {
      api.post('/listeners/heartbeat').catch(() => {});
    }, 30000);

    // Re-send heartbeat immediately whenever app returns to foreground
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') {
        api.post('/listeners/heartbeat').catch(() => {});
      }
    });

    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      subscription.remove();
      // Mark offline when listener leaves the listener section (logout, etc.)
      api.post('/listeners/go-offline').catch(() => {});
    };
  }, []);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopWidth: 0,
          height: 65,
          paddingBottom: 8,
          paddingTop: 6,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.06,
          shadowRadius: 8,
          elevation: 8,
        },
        tabBarActiveTintColor: '#A2E3C4',
        tabBarInactiveTintColor: '#A0AEC0',
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
      }}
    >
      <Tabs.Screen name="dashboard" options={{ title: 'Home', tabBarIcon: ({ color, size }) => <Ionicons name="home" size={size} color={color} /> }} />
      <Tabs.Screen name="leaderboard" options={{ title: 'Leaderboard', tabBarIcon: ({ color, size }) => <Ionicons name="trophy" size={size} color={color} /> }} />
      <Tabs.Screen name="referral" options={{ title: 'Refer', tabBarIcon: ({ color, size }) => <Ionicons name="gift" size={size} color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: ({ color, size }) => <Ionicons name="person" size={size} color={color} /> }} />
      <Tabs.Screen name="kyc" options={{ href: null }} />
      <Tabs.Screen name="calls" options={{ href: null }} />
    </Tabs>
  );
}
