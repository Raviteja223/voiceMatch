import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  ActivityIndicator, Switch, Alert, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

export default function ListenerDashboard() {
  const [earnings, setEarnings] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(false);
  const [toggling, setToggling] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [earningsRes, profileRes] = await Promise.all([
        api.get('/earnings/dashboard'),
        api.get('/listeners/profile'),
      ]);
      setEarnings(earningsRes.earnings);
      setProfile(profileRes);
      setIsOnline(profileRes.is_online || false);
    } catch (e) {}
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const toggleOnline = async (value: boolean) => {
    setToggling(true);
    try {
      await api.post('/listeners/toggle-online', { online: value });
      setIsOnline(value);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setToggling(false);
  };

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#A2E3C4" /></View></SafeAreaView>;

  const e = earnings || { total_earned: 0, pending_balance: 0, withdrawn: 0 };

  return (
    <SafeAreaView style={styles.container} testID="listener-dashboard-screen">
      <ScrollView refreshControl={<RefreshControl refreshing={false} onRefresh={loadData} tintColor="#A2E3C4" />}>
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome back!</Text>
            <Text style={styles.name}>{profile?.name || 'Listener'}</Text>
          </View>
          <View style={styles.onlineToggle}>
            <Text style={styles.onlineLabel}>{isOnline ? 'Online' : 'Offline'}</Text>
            <Switch
              testID="online-toggle"
              value={isOnline}
              onValueChange={toggleOnline}
              disabled={toggling}
              trackColor={{ false: '#E2E8F0', true: '#A2E3C4' }}
              thumbColor={isOnline ? '#fff' : '#fff'}
            />
          </View>
        </View>

        {/* Earnings Summary */}
        <View style={styles.earningsCard}>
          <Text style={styles.earningsLabel}>Pending Balance</Text>
          <Text style={styles.earningsAmount}>₹{Math.round(e.pending_balance)}</Text>
          <View style={styles.earningsRow}>
            <View style={styles.earningsStat}>
              <Text style={styles.statLabel}>Total Earned</Text>
              <Text style={styles.statValue}>₹{Math.round(e.total_earned)}</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.earningsStat}>
              <Text style={styles.statLabel}>Withdrawn</Text>
              <Text style={styles.statValue}>₹{Math.round(e.withdrawn)}</Text>
            </View>
          </View>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Ionicons name="call" size={20} color="#FF8FA3" />
            <Text style={styles.statCardValue}>{profile?.total_calls || 0}</Text>
            <Text style={styles.statCardLabel}>Total Calls</Text>
          </View>
          <View style={styles.statCard}>
            <Ionicons name="time" size={20} color="#85C1E9" />
            <Text style={styles.statCardValue}>{Math.round(profile?.total_minutes || 0)}m</Text>
            <Text style={styles.statCardLabel}>Talk Time</Text>
          </View>
          <View style={styles.statCard}>
            <Ionicons name="star" size={20} color="#F6E05E" />
            <Text style={styles.statCardValue}>{profile?.avg_rating?.toFixed(1) || '0'}</Text>
            <Text style={styles.statCardLabel}>Rating</Text>
          </View>
        </View>

        {/* Tier Badge */}
        <View style={styles.tierCard}>
          <View style={styles.tierLeft}>
            <Ionicons name="ribbon" size={24} color={profile?.tier === 'elite' ? '#F6E05E' : profile?.tier === 'trusted' ? '#A2E3C4' : '#E2E8F0'} />
            <View>
              <Text style={styles.tierTitle}>Tier: {(profile?.tier || 'new').charAt(0).toUpperCase() + (profile?.tier || 'new').slice(1)}</Text>
              <Text style={styles.tierSub}>
                {profile?.tier === 'elite' ? '+20% earnings boost' : profile?.tier === 'trusted' ? '+10% earnings boost' : 'Keep talking to level up!'}
              </Text>
            </View>
          </View>
        </View>

        {/* Withdraw */}
        <TouchableOpacity testID="withdraw-btn" style={styles.withdrawBtn} onPress={() => {
          if (e.pending_balance < 1000) {
            Alert.alert('Minimum ₹1000', `You need ₹${1000 - Math.round(e.pending_balance)} more to withdraw`);
          } else {
            Alert.alert('Withdraw', `Withdraw ₹${Math.round(e.pending_balance)} to your UPI?`, [
              { text: 'Cancel' },
              { text: 'Withdraw', onPress: async () => {
                try {
                  await api.post('/earnings/withdraw', { amount: e.pending_balance, upi_id: 'demo@upi' });
                  Alert.alert('Success', 'Withdrawal initiated!');
                  loadData();
                } catch (err: any) { Alert.alert('Error', err.message); }
              }},
            ]);
          }
        }}>
          <Ionicons name="wallet" size={20} color="#1A4D2E" />
          <Text style={styles.withdrawText}>Withdraw to UPI</Text>
        </TouchableOpacity>

        {/* Rate Info */}
        <View style={styles.rateInfoCard}>
          <Text style={styles.rateInfoTitle}>Your Earning Rates</Text>
          <View style={styles.rateRow}>
            <View style={styles.rateItem}><Ionicons name="mic" size={16} color="#FF8FA3" /><Text style={styles.rateLabel}>Voice</Text><Text style={styles.rateValue}>₹3/min</Text></View>
            <View style={styles.rateItem}><Ionicons name="videocam" size={16} color="#BB8FCE" /><Text style={styles.rateLabel}>Video</Text><Text style={styles.rateValue}>₹5/min</Text></View>
            <View style={styles.rateItem}><Ionicons name="timer" size={16} color="#85C1E9" /><Text style={styles.rateLabel}>Base</Text><Text style={styles.rateValue}>₹50/hr</Text></View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 16 },
  greeting: { fontSize: 13, color: '#718096', fontWeight: '500' },
  name: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  onlineToggle: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  onlineLabel: { fontSize: 13, fontWeight: '600', color: '#4A5568' },
  earningsCard: { backgroundColor: '#A2E3C4', borderRadius: 20, padding: 24, marginHorizontal: 20, alignItems: 'center', marginBottom: 16 },
  earningsLabel: { fontSize: 13, color: '#1A4D2E', fontWeight: '500', opacity: 0.7 },
  earningsAmount: { fontSize: 40, fontWeight: '800', color: '#1A4D2E', marginTop: 4 },
  earningsRow: { flexDirection: 'row', alignItems: 'center', marginTop: 16, gap: 24 },
  earningsStat: { alignItems: 'center' },
  statLabel: { fontSize: 11, color: '#1A4D2E', opacity: 0.6, fontWeight: '500' },
  statValue: { fontSize: 16, fontWeight: '700', color: '#1A4D2E', marginTop: 2 },
  statDivider: { width: 1, height: 28, backgroundColor: 'rgba(26,77,46,0.2)' },
  statsGrid: { flexDirection: 'row', paddingHorizontal: 20, gap: 10, marginBottom: 16 },
  statCard: { flex: 1, backgroundColor: '#fff', borderRadius: 14, padding: 14, alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  statCardValue: { fontSize: 18, fontWeight: '700', color: '#2D3748', marginTop: 6 },
  statCardLabel: { fontSize: 10, color: '#A0AEC0', fontWeight: '500', marginTop: 2 },
  tierCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginHorizontal: 20, marginBottom: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  tierLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  tierTitle: { fontSize: 15, fontWeight: '700', color: '#2D3748' },
  tierSub: { fontSize: 12, color: '#718096', marginTop: 2 },
  withdrawBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#A2E3C4', paddingVertical: 14, borderRadius: 24, marginHorizontal: 20, marginBottom: 16 },
  withdrawText: { fontSize: 15, fontWeight: '700', color: '#1A4D2E' },
  rateInfoCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginHorizontal: 20, marginBottom: 20 },
  rateInfoTitle: { fontSize: 14, fontWeight: '700', color: '#2D3748', marginBottom: 12 },
  rateRow: { flexDirection: 'row', gap: 12 },
  rateItem: { flex: 1, alignItems: 'center', backgroundColor: '#FFFBF0', borderRadius: 12, padding: 10 },
  rateLabel: { fontSize: 11, color: '#718096', fontWeight: '500', marginTop: 4 },
  rateValue: { fontSize: 14, fontWeight: '700', color: '#2D3748', marginTop: 2 },
});
