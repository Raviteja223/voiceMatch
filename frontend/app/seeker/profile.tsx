import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { clearUser } from '../../src/store';

export default function SeekerProfile() {
  const router = useRouter();

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      { text: 'Cancel' },
      { text: 'Logout', style: 'destructive', onPress: async () => {
        await api.clearToken();
        await clearUser();
        router.replace('/');
      }},
    ]);
  };

  return (
    <SafeAreaView style={styles.container} testID="seeker-profile-screen">
      <Text style={styles.title}>Profile</Text>
      <View style={styles.card}>
        <TouchableOpacity testID="admin-link" style={styles.menuItem} onPress={() => router.push('/admin')}>
          <Ionicons name="shield" size={22} color="#BB8FCE" />
          <Text style={styles.menuText}>Admin Panel</Text>
          <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
        </TouchableOpacity>
        <View style={styles.divider} />
        <TouchableOpacity testID="about-link" style={styles.menuItem}>
          <Ionicons name="information-circle" size={22} color="#85C1E9" />
          <Text style={styles.menuText}>About VoiceMatch</Text>
          <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
        </TouchableOpacity>
        <View style={styles.divider} />
        <TouchableOpacity testID="support-link" style={styles.menuItem}>
          <Ionicons name="help-circle" size={22} color="#F6E05E" />
          <Text style={styles.menuText}>Support</Text>
          <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
        </TouchableOpacity>
        <View style={styles.divider} />
        <TouchableOpacity testID="logout-btn" style={styles.menuItem} onPress={handleLogout}>
          <Ionicons name="log-out" size={22} color="#F56565" />
          <Text style={[styles.menuText, { color: '#F56565' }]}>Logout</Text>
          <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
        </TouchableOpacity>
      </View>
      <Text style={styles.version}>VoiceMatch v1.0.0</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0', paddingHorizontal: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748', marginTop: 8, marginBottom: 24 },
  card: { backgroundColor: '#fff', borderRadius: 18, padding: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  menuItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 16, gap: 12 },
  menuText: { flex: 1, fontSize: 15, fontWeight: '500', color: '#2D3748' },
  divider: { height: 1, backgroundColor: '#F0F0F0', marginHorizontal: 16 },
  version: { textAlign: 'center', color: '#A0AEC0', fontSize: 12, marginTop: 24 },
});
