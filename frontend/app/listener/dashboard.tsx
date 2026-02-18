import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  ActivityIndicator, Alert, RefreshControl, Modal, Animated, Vibration,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { t } from '../../src/i18n';

export default function ListenerDashboard() {
  const router = useRouter();
  const [earnings, setEarnings] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [incomingCall, setIncomingCall] = useState<{
    call_id: string; caller_name: string; call_type: string;
  } | null>(null);
  const [accepting, setAccepting] = useState(false);
  const incomingPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const loadData = useCallback(async () => {
    try {
      // Auto-set online via heartbeat
      api.post('/listeners/heartbeat').catch(() => {});
      const [earningsRes, profileRes] = await Promise.all([
        api.get('/earnings/dashboard'),
        api.get('/listeners/profile'),
      ]);
      setEarnings(earningsRes.earnings);
      setProfile(profileRes);
    } catch (e) {}
    setLoading(false);
  }, []);

  // Poll for incoming calls every 3 seconds
  const checkIncomingCall = useCallback(async () => {
    try {
      const res = await api.get('/calls/check-incoming');
      if (res.has_incoming && res.call_id) {
        setIncomingCall({
          call_id: res.call_id,
          caller_name: res.caller_name || 'Someone',
          call_type: res.call_type || 'voice',
        });
        // Vibrate to alert the listener
        Vibration.vibrate([0, 500, 200, 500]);
      } else {
        setIncomingCall(null);
      }
    } catch (e) {
      // No incoming call or error - ignore
    }
  }, []);

  const handleAcceptCall = async () => {
    if (!incomingCall) return;
    setAccepting(true);
    try {
      const res = await api.post('/calls/accept', { call_id: incomingCall.call_id });
      if (res.success) {
        setIncomingCall(null);
        // Navigate to the call screen, passing HMS tokens so audio can connect
        router.push({
          pathname: '/call',
          params: {
            listenerId: '', // Not needed for listener side
            listenerName: incomingCall.caller_name,
            listenerAvatar: 'avatar_1',
            callType: incomingCall.call_type,
            callId: incomingCall.call_id,
            isListener: 'true',
            hmsToken: res.hms_token || '',
            hmsRoomId: res.hms_room_id || '',
          },
        });
      }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Could not accept call');
    }
    setAccepting(false);
  };

  const handleRejectCall = async () => {
    if (!incomingCall) return;
    try {
      await api.post('/calls/reject', { call_id: incomingCall.call_id });
    } catch (e) {}
    setIncomingCall(null);
  };

  useEffect(() => {
    loadData();
    // Poll for incoming calls every 3 seconds
    checkIncomingCall();
    incomingPollRef.current = setInterval(checkIncomingCall, 3000);
    return () => {
      if (incomingPollRef.current) clearInterval(incomingPollRef.current);
    };
  }, [loadData, checkIncomingCall]);

  // Pulse animation for incoming call modal
  useEffect(() => {
    if (incomingCall) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.1, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [incomingCall]);

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#A2E3C4" /></View></SafeAreaView>;

  const e = earnings || { total_earned: 0, pending_balance: 0, withdrawn: 0 };
  const kycStatus = profile?.kyc_status || 'pending';

  return (
    <SafeAreaView style={styles.container} testID="listener-dashboard-screen">
      <ScrollView refreshControl={<RefreshControl refreshing={false} onRefresh={loadData} tintColor="#A2E3C4" />}>
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>{t('welcome_back')}</Text>
            <Text style={styles.name}>{profile?.name || 'Listener'}</Text>
          </View>
          <View style={styles.onlineBadge} testID="auto-online-badge">
            <View style={styles.greenDot} />
            <Text style={styles.onlineText}>{t('online')}</Text>
          </View>
        </View>

        {/* KYC Banner */}
        {kycStatus !== 'verified' && (
          <TouchableOpacity testID="kyc-banner" style={styles.kycBanner} onPress={() => router.push('/listener/kyc')}>
            <Ionicons name="shield-half" size={20} color="#ED8936" />
            <View style={styles.kycBannerInfo}>
              <Text style={styles.kycBannerTitle}>
                {kycStatus === 'submitted' ? 'KYC Under Review' : 'Complete KYC Verification'}
              </Text>
              <Text style={styles.kycBannerSub}>
                {kycStatus === 'submitted' ? 'Your documents are being verified' : 'Required to receive calls and withdraw'}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#ED8936" />
          </TouchableOpacity>
        )}

        {/* Earnings Summary */}
        <View style={styles.earningsCard}>
          <Text style={styles.earningsLabel}>{t('pending_balance')}</Text>
          <Text style={styles.earningsAmount}>₹{Math.round(e.pending_balance)}</Text>
          <View style={styles.earningsRow}>
            <View style={styles.earningsStat}>
              <Text style={styles.statLabel}>{t('total_earned')}</Text>
              <Text style={styles.statValue}>₹{Math.round(e.total_earned)}</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.earningsStat}>
              <Text style={styles.statLabel}>{t('withdrawn')}</Text>
              <Text style={styles.statValue}>₹{Math.round(e.withdrawn)}</Text>
            </View>
          </View>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Ionicons name="call" size={20} color="#FF8FA3" />
            <Text style={styles.statCardValue}>{profile?.total_calls || 0}</Text>
            <Text style={styles.statCardLabel}>{t('total_calls')}</Text>
          </View>
          <View style={styles.statCard}>
            <Ionicons name="time" size={20} color="#85C1E9" />
            <Text style={styles.statCardValue}>{Math.round(profile?.total_minutes || 0)}m</Text>
            <Text style={styles.statCardLabel}>{t('talk_time')}</Text>
          </View>
          <View style={styles.statCard}>
            <Ionicons name="star" size={20} color="#F6E05E" />
            <Text style={styles.statCardValue}>{profile?.avg_rating?.toFixed(1) || '0'}</Text>
            <Text style={styles.statCardLabel}>{t('rating')}</Text>
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
            Alert.alert('Instant Withdraw', `Withdraw ₹${Math.round(e.pending_balance)} instantly to your UPI?`, [
              { text: 'Cancel' },
              { text: 'Withdraw Now', onPress: async () => {
                try {
                  const res = await api.post('/earnings/withdraw', { amount: e.pending_balance, upi_id: 'demo@upi' });
                  Alert.alert('Success', res.message);
                  loadData();
                } catch (err: any) { Alert.alert('Error', err.message); }
              }},
            ]);
          }
        }}>
          <Ionicons name="flash" size={20} color="#1A4D2E" />
          <Text style={styles.withdrawText}>Instant {t('withdraw_upi')}</Text>
        </TouchableOpacity>

        {/* Rate Info */}
        <View style={styles.rateInfoCard}>
          <Text style={styles.rateInfoTitle}>{t('earning_rates')}</Text>
          <View style={styles.rateRow}>
            <View style={styles.rateItem}><Ionicons name="mic" size={16} color="#FF8FA3" /><Text style={styles.rateLabel}>Voice</Text><Text style={styles.rateValue}>₹2.5/min</Text></View>
            <View style={styles.rateItem}><Ionicons name="videocam" size={16} color="#BB8FCE" /><Text style={styles.rateLabel}>Video</Text><Text style={styles.rateValue}>₹5/min</Text></View>
          </View>
        </View>

        {/* Recording Notice */}
        <View style={styles.recordingNotice}>
          <Ionicons name="shield-checkmark" size={16} color="#A2E3C4" />
          <Text style={styles.recordingText}>All calls are recorded for safety (15-day retention, encrypted)</Text>
        </View>
      </ScrollView>

      {/* Incoming Call Modal */}
      <Modal
        visible={!!incomingCall}
        transparent
        animationType="slide"
        testID="incoming-call-modal"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.incomingCallCard}>
            <Text style={styles.incomingLabel}>{t('incoming_call')}</Text>
            <Animated.View style={[styles.incomingAvatarRing, { transform: [{ scale: pulseAnim }] }]}>
              <View style={styles.incomingAvatar}>
                <Ionicons name="person" size={40} color="#FF8FA3" />
              </View>
            </Animated.View>
            <Text style={styles.incomingCallerName}>{incomingCall?.caller_name || 'Someone'}</Text>
            <Text style={styles.incomingCallType}>
              {incomingCall?.call_type === 'video' ? t('video_call') : t('voice_call')}
            </Text>

            <View style={styles.incomingActions}>
              <TouchableOpacity
                testID="reject-call-btn"
                style={styles.rejectBtn}
                onPress={handleRejectCall}
              >
                <Ionicons name="close" size={28} color="#fff" />
                <Text style={styles.rejectText}>{t('decline')}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="accept-call-btn"
                style={styles.acceptBtn}
                onPress={handleAcceptCall}
                disabled={accepting}
              >
                {accepting ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <>
                    <Ionicons name="call" size={28} color="#fff" />
                    <Text style={styles.acceptText}>{t('accept')}</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 16 },
  greeting: { fontSize: 13, color: '#718096', fontWeight: '500' },
  name: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  onlineBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#E6FFED', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  greenDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#48BB78' },
  onlineText: { fontSize: 12, fontWeight: '600', color: '#48BB78' },
  kycBanner: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#FFF5E6', borderRadius: 14, padding: 14, marginHorizontal: 20, marginBottom: 16, borderLeftWidth: 3, borderLeftColor: '#ED8936' },
  kycBannerInfo: { flex: 1 },
  kycBannerTitle: { fontSize: 13, fontWeight: '700', color: '#744210' },
  kycBannerSub: { fontSize: 11, color: '#A0AEC0', marginTop: 2 },
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
  rateInfoCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginHorizontal: 20, marginBottom: 16 },
  rateInfoTitle: { fontSize: 14, fontWeight: '700', color: '#2D3748', marginBottom: 12 },
  rateRow: { flexDirection: 'row', gap: 12 },
  rateItem: { flex: 1, alignItems: 'center', backgroundColor: '#FFFBF0', borderRadius: 12, padding: 10 },
  rateLabel: { fontSize: 11, color: '#718096', fontWeight: '500', marginTop: 4 },
  rateValue: { fontSize: 14, fontWeight: '700', color: '#2D3748', marginTop: 2 },
  recordingNotice: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 20, marginBottom: 20 },
  recordingText: { fontSize: 11, color: '#A0AEC0', flex: 1 },
  // Incoming call modal styles
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  incomingCallCard: { backgroundColor: '#fff', borderRadius: 28, padding: 32, alignItems: 'center', width: '100%', maxWidth: 340, shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.2, shadowRadius: 24, elevation: 10 },
  incomingLabel: { fontSize: 14, fontWeight: '600', color: '#48BB78', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 20 },
  incomingAvatarRing: { width: 100, height: 100, borderRadius: 50, borderWidth: 3, borderColor: '#48BB78', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  incomingAvatar: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#FFF0F3', alignItems: 'center', justifyContent: 'center' },
  incomingCallerName: { fontSize: 22, fontWeight: '700', color: '#2D3748', marginBottom: 4 },
  incomingCallType: { fontSize: 14, color: '#718096', fontWeight: '500', marginBottom: 28 },
  incomingActions: { flexDirection: 'row', gap: 32 },
  rejectBtn: { width: 70, height: 70, borderRadius: 35, backgroundColor: '#F56565', alignItems: 'center', justifyContent: 'center', shadowColor: '#F56565', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  rejectText: { fontSize: 10, fontWeight: '600', color: '#fff', marginTop: 2 },
  acceptBtn: { width: 70, height: 70, borderRadius: 35, backgroundColor: '#48BB78', alignItems: 'center', justifyContent: 'center', shadowColor: '#48BB78', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  acceptText: { fontSize: 10, fontWeight: '600', color: '#fff', marginTop: 2 },
});
