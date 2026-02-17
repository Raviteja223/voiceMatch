import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  ActivityIndicator, Alert, TextInput, Share, FlatList, RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

const TIER_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  bronze: { bg: '#FDEBD0', text: '#A04000', icon: '🥉' },
  silver: { bg: '#E8DAEF', text: '#6C3483', icon: '🥈' },
  gold: { bg: '#FFF3CD', text: '#744210', icon: '🥇' },
};

export default function ReferralScreen() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [referrals, setReferrals] = useState<any[]>([]);
  const [inputCode, setInputCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [tab, setTab] = useState<'share' | 'referrals'>('share');

  const loadData = useCallback(async () => {
    try {
      const [codeRes, refsRes] = await Promise.all([
        api.get('/referral/my-code'),
        api.get('/referral/my-referrals'),
      ]);
      setData(codeRes);
      setReferrals(refsRes.referrals || []);
    } catch (e) {}
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleShare = async () => {
    if (!data?.code) return;
    try {
      await Share.share({
        message: `Join Konnectra as a Listener and start earning! Use my referral code: ${data.code}\n\nEarn ₹3/min voice calls, ₹5/min video calls. Download now!`,
      });
    } catch (e) {}
  };

  const handleApplyCode = async () => {
    if (!inputCode.trim()) return;
    setApplying(true);
    try {
      const res = await api.post('/referral/apply', { referral_code: inputCode.trim() });
      Alert.alert('Success!', res.message);
      setInputCode('');
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setApplying(false);
  };

  const tierInfo = TIER_COLORS[data?.tier || 'bronze'] || TIER_COLORS.bronze;

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#A2E3C4" /></View></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container} testID="referral-screen">
      <View style={styles.header}>
        <TouchableOpacity testID="referral-back-btn" onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#2D3748" />
        </TouchableOpacity>
        <Text style={styles.title}>Refer & Earn</Text>
      </View>

      <View style={styles.tabRow}>
        <TouchableOpacity testID="tab-share" style={[styles.tab, tab === 'share' && styles.tabActive]} onPress={() => setTab('share')}>
          <Text style={[styles.tabText, tab === 'share' && styles.tabTextActive]}>Share & Earn</Text>
        </TouchableOpacity>
        <TouchableOpacity testID="tab-referrals" style={[styles.tab, tab === 'referrals' && styles.tabActive]} onPress={() => setTab('referrals')}>
          <Text style={[styles.tabText, tab === 'referrals' && styles.tabTextActive]}>My Referrals ({referrals.length})</Text>
        </TouchableOpacity>
      </View>

      {tab === 'share' ? (
        <ScrollView contentContainerStyle={styles.scrollContent} refreshControl={<RefreshControl refreshing={false} onRefresh={loadData} tintColor="#A2E3C4" />}>
          {/* Referral Code Card */}
          <View style={styles.codeCard}>
            <Text style={styles.codeLabel}>Your Referral Code</Text>
            <View style={styles.codeBox}>
              <Text style={styles.codeText} testID="referral-code">{data?.code || '---'}</Text>
              <TouchableOpacity testID="copy-code-btn" style={styles.copyBtn} onPress={handleShare}>
                <Ionicons name="share-social" size={20} color="#fff" />
              </TouchableOpacity>
            </View>
            <TouchableOpacity testID="share-btn" style={styles.shareBtn} onPress={handleShare}>
              <Ionicons name="share" size={18} color="#1A4D2E" />
              <Text style={styles.shareBtnText}>Share with Friends</Text>
            </TouchableOpacity>
          </View>

          {/* Tier Badge */}
          <View style={[styles.tierCard, { backgroundColor: tierInfo.bg }]}>
            <Text style={styles.tierEmoji}>{tierInfo.icon}</Text>
            <View style={styles.tierInfo}>
              <Text style={[styles.tierName, { color: tierInfo.text }]}>{(data?.tier || 'bronze').toUpperCase()} Tier</Text>
              <Text style={styles.tierDetail}>₹{data?.bonus_per_referral}/referral · {data?.commission_rate} commission for {data?.commission_days} days</Text>
            </View>
          </View>

          {/* Earnings Summary */}
          <View style={styles.earningsGrid}>
            <View style={styles.earnCard}>
              <Ionicons name="people" size={20} color="#A2E3C4" />
              <Text style={styles.earnValue}>{data?.active_referrals || 0}</Text>
              <Text style={styles.earnLabel}>Active</Text>
            </View>
            <View style={styles.earnCard}>
              <Ionicons name="hourglass" size={20} color="#F6E05E" />
              <Text style={styles.earnValue}>{data?.pending_referrals || 0}</Text>
              <Text style={styles.earnLabel}>Pending</Text>
            </View>
            <View style={styles.earnCard}>
              <Ionicons name="cash" size={20} color="#FF8FA3" />
              <Text style={styles.earnValue}>₹{data?.total_bonuses_earned || 0}</Text>
              <Text style={styles.earnLabel}>Bonuses</Text>
            </View>
            <View style={styles.earnCard}>
              <Ionicons name="trending-up" size={20} color="#BB8FCE" />
              <Text style={styles.earnValue}>₹{data?.total_commission_earned || 0}</Text>
              <Text style={styles.earnLabel}>Commission</Text>
            </View>
          </View>

          {/* How it works */}
          <View style={styles.howItWorks}>
            <Text style={styles.howTitle}>How Referrals Work</Text>
            <View style={styles.howStep}>
              <View style={styles.stepNum}><Text style={styles.stepNumText}>1</Text></View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>Share your code</Text>
                <Text style={styles.stepDesc}>Send your unique code to friends who want to become listeners</Text>
              </View>
            </View>
            <View style={styles.howStep}>
              <View style={styles.stepNum}><Text style={styles.stepNumText}>2</Text></View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>They join & start talking</Text>
                <Text style={styles.stepDesc}>Your friend signs up and completes 30 minutes of calls</Text>
              </View>
            </View>
            <View style={styles.howStep}>
              <View style={[styles.stepNum, { backgroundColor: '#A2E3C4' }]}><Text style={styles.stepNumText}>3</Text></View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>You earn bonus + commission</Text>
                <Text style={styles.stepDesc}>Get ₹{data?.bonus_per_referral || 200} bonus + {data?.commission_rate || '5%'} of their earnings for {data?.commission_days || 90} days</Text>
              </View>
            </View>
          </View>

          {/* Tier Progression */}
          <View style={styles.tierProgression}>
            <Text style={styles.tierProgTitle}>Tier Rewards</Text>
            <Text style={styles.tierNote}>⚡ Bonus paid when referral completes 30 min calls</Text>
            <View style={styles.tierRow}>
              <View style={[styles.tierBadge, { backgroundColor: '#FDEBD0' }]}><Text style={styles.tierBadgeText}>🥉 Bronze (1-5)</Text></View>
              <Text style={styles.tierRowText}>₹50/ref · 5%/15 days</Text>
            </View>
            <View style={styles.tierRow}>
              <View style={[styles.tierBadge, { backgroundColor: '#E8DAEF' }]}><Text style={styles.tierBadgeText}>🥈 Silver (6-15)</Text></View>
              <Text style={styles.tierRowText}>₹75/ref · 7.5%/15 days</Text>
            </View>
            <View style={styles.tierRow}>
              <View style={[styles.tierBadge, { backgroundColor: '#FFF3CD' }]}><Text style={styles.tierBadgeText}>🥇 Gold (16-25)</Text></View>
              <Text style={styles.tierRowText}>₹100/ref · 10%/15 days</Text>
            </View>
            <Text style={styles.maxNote}>Maximum 25 referrals per listener</Text>
          </View>

          {/* Apply Code Section */}
          <View style={styles.applySection}>
            <Text style={styles.applyTitle}>Have a referral code?</Text>
            <View style={styles.applyRow}>
              <TextInput
                testID="referral-code-input"
                style={styles.applyInput}
                placeholder="Enter code"
                placeholderTextColor="#A0AEC0"
                value={inputCode}
                onChangeText={setInputCode}
                autoCapitalize="characters"
              />
              <TouchableOpacity
                testID="apply-code-btn"
                style={[styles.applyBtn, !inputCode.trim() && styles.applyBtnDisabled]}
                onPress={handleApplyCode}
                disabled={applying || !inputCode.trim()}
              >
                {applying ? <ActivityIndicator size="small" color="#fff" /> : (
                  <Text style={styles.applyBtnText}>Apply</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      ) : (
        <FlatList
          data={referrals}
          keyExtractor={item => item.id}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
          refreshControl={<RefreshControl refreshing={false} onRefresh={loadData} tintColor="#A2E3C4" />}
          renderItem={({ item }) => (
            <View style={styles.refCard} testID={`referral-${item.id}`}>
              <View style={styles.refLeft}>
                <View style={[styles.refAvatar, { backgroundColor: item.status === 'active' ? '#E6FFED' : '#FFF5F5' }]}>
                  <Ionicons name={item.status === 'active' ? 'checkmark-circle' : 'hourglass'} size={20} color={item.status === 'active' ? '#48BB78' : '#F6E05E'} />
                </View>
                <View>
                  <Text style={styles.refName}>{item.referred_name}</Text>
                  <Text style={styles.refDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
                </View>
              </View>
              <View style={styles.refRight}>
                <View style={[styles.statusBadge, { backgroundColor: item.status === 'active' ? '#E6FFED' : '#FFF5F5' }]}>
                  <Text style={[styles.statusText, { color: item.status === 'active' ? '#48BB78' : '#F6E05E' }]}>
                    {item.status === 'active' ? 'Active' : 'Pending'}
                  </Text>
                </View>
                {item.status === 'active' && (
                  <Text style={styles.refEarning}>₹{Math.round((item.bonus_paid || 0) + (item.total_commission || 0))}</Text>
                )}
              </View>
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Ionicons name="people-outline" size={48} color="#E2E8F0" />
              <Text style={styles.emptyText}>No referrals yet</Text>
              <Text style={styles.emptySubText}>Share your code to start earning</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 8, gap: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  tabRow: { flexDirection: 'row', paddingHorizontal: 20, marginBottom: 12, gap: 10 },
  tab: { flex: 1, paddingVertical: 10, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', borderWidth: 1, borderColor: '#E2E8F0' },
  tabActive: { backgroundColor: '#A2E3C4', borderColor: '#A2E3C4' },
  tabText: { fontSize: 13, fontWeight: '600', color: '#718096' },
  tabTextActive: { color: '#1A4D2E' },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 30 },
  codeCard: { backgroundColor: '#A2E3C4', borderRadius: 20, padding: 24, alignItems: 'center', marginBottom: 16 },
  codeLabel: { fontSize: 13, color: '#1A4D2E', fontWeight: '500', opacity: 0.7 },
  codeBox: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 8, marginBottom: 16 },
  codeText: { fontSize: 32, fontWeight: '800', color: '#1A4D2E', letterSpacing: 3 },
  copyBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#1A4D2E', alignItems: 'center', justifyContent: 'center' },
  shareBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: 'rgba(255,255,255,0.5)', paddingHorizontal: 20, paddingVertical: 10, borderRadius: 16 },
  shareBtnText: { fontSize: 14, fontWeight: '600', color: '#1A4D2E' },
  tierCard: { borderRadius: 16, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  tierEmoji: { fontSize: 32 },
  tierInfo: { flex: 1 },
  tierName: { fontSize: 16, fontWeight: '700' },
  tierDetail: { fontSize: 12, color: '#718096', marginTop: 2 },
  earningsGrid: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  earnCard: { flex: 1, backgroundColor: '#fff', borderRadius: 14, padding: 12, alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  earnValue: { fontSize: 16, fontWeight: '700', color: '#2D3748', marginTop: 4 },
  earnLabel: { fontSize: 10, color: '#A0AEC0', fontWeight: '500', marginTop: 2 },
  howItWorks: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16 },
  howTitle: { fontSize: 15, fontWeight: '700', color: '#2D3748', marginBottom: 14 },
  howStep: { flexDirection: 'row', gap: 12, marginBottom: 14 },
  stepNum: { width: 28, height: 28, borderRadius: 14, backgroundColor: '#FF8FA3', alignItems: 'center', justifyContent: 'center' },
  stepNumText: { fontSize: 13, fontWeight: '700', color: '#fff' },
  stepContent: { flex: 1 },
  stepTitle: { fontSize: 14, fontWeight: '600', color: '#2D3748' },
  stepDesc: { fontSize: 12, color: '#718096', marginTop: 2 },
  tierProgression: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16 },
  tierProgTitle: { fontSize: 15, fontWeight: '700', color: '#2D3748', marginBottom: 8 },
  tierNote: { fontSize: 11, color: '#48BB78', fontWeight: '600', marginBottom: 10, backgroundColor: '#E6FFED', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6, alignSelf: 'flex-start' },
  tierRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  tierBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  tierBadgeText: { fontSize: 12, fontWeight: '600' },
  tierRowText: { fontSize: 12, color: '#718096', fontWeight: '500' },
  maxNote: { fontSize: 10, color: '#A0AEC0', textAlign: 'center', marginTop: 10, fontStyle: 'italic' },
  applySection: { backgroundColor: '#fff', borderRadius: 16, padding: 16 },
  applyTitle: { fontSize: 14, fontWeight: '600', color: '#2D3748', marginBottom: 10 },
  applyRow: { flexDirection: 'row', gap: 10 },
  applyInput: { flex: 1, backgroundColor: '#F7F7F7', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 15, fontWeight: '600', color: '#2D3748', letterSpacing: 2 },
  applyBtn: { backgroundColor: '#A2E3C4', paddingHorizontal: 20, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  applyBtnDisabled: { opacity: 0.4 },
  applyBtnText: { fontSize: 14, fontWeight: '700', color: '#1A4D2E' },
  refCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fff', borderRadius: 14, padding: 14, marginBottom: 8, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  refLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  refAvatar: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  refName: { fontSize: 14, fontWeight: '600', color: '#2D3748' },
  refDate: { fontSize: 11, color: '#A0AEC0', marginTop: 2 },
  refRight: { alignItems: 'flex-end' },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  statusText: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase' },
  refEarning: { fontSize: 14, fontWeight: '700', color: '#48BB78', marginTop: 4 },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, fontWeight: '600', color: '#718096', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#A0AEC0', marginTop: 4 },
});
