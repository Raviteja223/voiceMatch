import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function ListenerLayout() {
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
      <Tabs.Screen name="dashboard" options={{ title: 'Dashboard', tabBarIcon: ({ color, size }) => <Ionicons name="stats-chart" size={size} color={color} /> }} />
      <Tabs.Screen name="referral" options={{ title: 'Refer & Earn', tabBarIcon: ({ color, size }) => <Ionicons name="gift" size={size} color={color} /> }} />
      <Tabs.Screen name="calls" options={{ title: 'Calls', tabBarIcon: ({ color, size }) => <Ionicons name="call" size={size} color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: ({ color, size }) => <Ionicons name="person" size={size} color={color} /> }} />
    </Tabs>
  );
}
