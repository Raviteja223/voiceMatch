import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  ActivityIndicator, TextInput, Share, Alert, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

export default function SeekerReferralScreen() {
  const [data, setData] = useState<any>(null);
  const [inputCode, setInputCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const res = await api.get('/seeker-referral/my-code');
      setData(res);
    } catch (e) {}
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleShare = async () => {
    if (!data?.code) return;
    try {
      await Share.share({
        message: `Join Konnectra and get amazing voice companions! Use my code: ${data.code} to give me ₹15 credits. Download now!`,
      });
    } catch (e) {}
  };

  const handleApply = async () => {
    if (!inputCode.trim()) return;
    setApplying(true);
    try {
      const res = await api.post('/seeker-referral/apply', { referral_code: inputCode.trim() });
      Alert.alert('Success!', res.message);
      setInputCode('');
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setApplying(false);
  };

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#FF8FA3" /></View></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container} testID="seeker-referral-screen">
      <ScrollView contentContainerStyle={styles.scroll} refreshControl={<RefreshControl refreshing={false} onRefresh={loadData} tintColor="#FF8FA3" />}>
        <Text style={styles.title}>Refer Friends</Text>

        <View style={styles.codeCard}>
          <Ionicons name="gift" size={28} color="#fff" />
          <Text style={styles.codeLabel}>Your Referral Code</Text>
          <Text style={styles.codeText} testID="seeker-referral-code">{data?.code || '---'}</Text>
          <Text style={styles.codeInfo}>Share & earn ₹15 credits per friend!</Text>
          <TouchableOpacity testID="seeker-share-btn" style={styles.shareBtn} onPress={handleShare}>
            <Ionicons name="share-social" size={18} color="#FF8FA3" />
            <Text style={styles.shareBtnText}>Share Code</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{data?.total_referrals || 0}</Text>
            <Text style={styles.statLabel}>Friends Referred</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>₹{data?.credits_earned || 0}</Text>
            <Text style={styles.statLabel}>Credits Earned</Text>
          </View>
        </View>

        <View style={styles.howCard}>
          <Text style={styles.howTitle}>How it works</Text>
          <View style={styles.howStep}>
            <View style={styles.stepIcon}><Ionicons name="share" size={16} color="#FF8FA3" /></View>
            <Text style={styles.stepText}>Share your code with friends</Text>
          </View>
          <View style={styles.howStep}>
            <View style={styles.stepIcon}><Ionicons name="person-add" size={16} color="#A2E3C4" /></View>
            <Text style={styles.stepText}>They sign up and enter your code</Text>
          </View>
          <View style={styles.howStep}>
            <View style={styles.stepIcon}><Ionicons name="wallet" size={16} color="#F6E05E" /></View>
            <Text style={styles.stepText}>You get ₹15 credits instantly!</Text>
          </View>
        </View>

        <View style={styles.applyCard}>
          <Text style={styles.applyTitle}>Have a friend's code?</Text>
          <View style={styles.applyRow}>
            <TextInput testID="seeker-referral-input" style={styles.applyInput} placeholder="Enter code" placeholderTextColor="#A0AEC0" value={inputCode} onChangeText={setInputCode} autoCapitalize="characters" />
            <TouchableOpacity testID="seeker-apply-btn" style={[styles.applyBtn, !inputCode.trim() && styles.applyBtnDisabled]} onPress={handleApply} disabled={applying || !inputCode.trim()}>
              {applying ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.applyBtnText}>Apply</Text>}
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { paddingHorizontal: 20, paddingBottom: 30 },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748', marginTop: 8, marginBottom: 16 },
  codeCard: { backgroundColor: '#FF8FA3', borderRadius: 20, padding: 24, alignItems: 'center', marginBottom: 16, shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.3, shadowRadius: 16, elevation: 6 },
  codeLabel: { fontSize: 13, color: '#FFE0E6', fontWeight: '500', marginTop: 8 },
  codeText: { fontSize: 32, fontWeight: '800', color: '#fff', letterSpacing: 3, marginTop: 4 },
  codeInfo: { fontSize: 12, color: '#FFE0E6', marginTop: 6 },
  shareBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#fff', paddingHorizontal: 20, paddingVertical: 10, borderRadius: 16, marginTop: 14 },
  shareBtnText: { fontSize: 14, fontWeight: '600', color: '#FF8FA3' },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  statCard: { flex: 1, backgroundColor: '#fff', borderRadius: 14, padding: 16, alignItems: 'center' },
  statValue: { fontSize: 22, fontWeight: '800', color: '#2D3748' },
  statLabel: { fontSize: 11, color: '#A0AEC0', fontWeight: '500', marginTop: 4 },
  howCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16 },
  howTitle: { fontSize: 15, fontWeight: '700', color: '#2D3748', marginBottom: 12 },
  howStep: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8 },
  stepIcon: { width: 32, height: 32, borderRadius: 10, backgroundColor: '#FFFBF0', alignItems: 'center', justifyContent: 'center' },
  stepText: { fontSize: 13, color: '#4A5568', flex: 1 },
  applyCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16 },
  applyTitle: { fontSize: 14, fontWeight: '600', color: '#2D3748', marginBottom: 10 },
  applyRow: { flexDirection: 'row', gap: 10 },
  applyInput: { flex: 1, backgroundColor: '#F7F7F7', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 15, fontWeight: '600', color: '#2D3748', letterSpacing: 2 },
  applyBtn: { backgroundColor: '#FF8FA3', paddingHorizontal: 20, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  applyBtnDisabled: { opacity: 0.4 },
  applyBtnText: { fontSize: 14, fontWeight: '700', color: '#fff' },
});
