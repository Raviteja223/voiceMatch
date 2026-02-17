import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Animated, Alert, Dimensions,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../src/api';
import { AVATAR_COLORS } from '../src/store';

const { width } = Dimensions.get('window');

export default function CallScreen() {
  const router = useRouter();
  const { listenerId, listenerName, listenerAvatar, callType } = useLocalSearchParams<{
    listenerId: string; listenerName: string; listenerAvatar: string; callType: string;
  }>();

  const [callId, setCallId] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [status, setStatus] = useState<'connecting' | 'active' | 'ended'>('connecting');
  const [cost, setCost] = useState(0);
  const [ratePerMin, setRatePerMin] = useState(5);
  const [hmsRoomId, setHmsRoomId] = useState('');
  const [hmsConnected, setHmsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaker, setIsSpeaker] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const colors = AVATAR_COLORS[listenerAvatar || 'avatar_1'] || AVATAR_COLORS.avatar_1;

  useEffect(() => {
    startCall();
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.15, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const startCall = async () => {
    try {
      const res = await api.post('/calls/start', {
        listener_id: listenerId,
        call_type: callType || 'voice',
      });
      if (res.success) {
        setCallId(res.call.id);
        setRatePerMin(res.call.rate_per_min);

        // 100ms room info
        if (res.call.hms_room_id) {
          setHmsRoomId(res.call.hms_room_id);
          setHmsConnected(true);
          // In a native build, you'd join the 100ms room here:
          // await hmsInstance.join({ authToken: res.call.hms_token, ... })
        }

        // Start call timer (billing runs regardless of RTC status)
        setTimeout(() => {
          setStatus('active');
          timerRef.current = setInterval(() => {
            setSeconds(prev => {
              const newSec = prev + 1;
              // Billing: free under 5s, full first minute then per-second
              if (newSec <= 5) {
                setCost(0);
              } else {
                const effectiveRate = res.call.rate_per_min;
                if (newSec <= 60) {
                  setCost(effectiveRate); // Full first minute charge
                } else {
                  setCost(Math.round((effectiveRate + ((newSec - 60) / 60) * effectiveRate) * 100) / 100);
                }
              }
              return newSec;
            });
          }, 1000);
        }, 2000);
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
      router.back();
    }
  };

  const endCall = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setStatus('ended');
    try {
      // In native build: await hmsInstance.leave();
      const res = await api.post('/calls/end', { call_id: callId });
      router.replace({
        pathname: '/rating',
        params: {
          callId,
          listenerId,
          listenerName,
          listenerAvatar,
          duration: String(res.duration_seconds || seconds),
          cost: String(res.cost || cost),
        },
      });
    } catch (e: any) {
      router.back();
    }
  };

  const formatTime = (s: number) => {
    const min = Math.floor(s / 60);
    const sec = s % 60;
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} testID="call-screen">
      <View style={styles.content}>
        {/* Status bar */}
        <View style={styles.topBar}>
          <View style={styles.statusPill}>
            <View style={[styles.statusDot, status === 'active' && styles.activeDot]} />
            <Text style={styles.statusText}>
              {status === 'connecting' ? 'Connecting...' : status === 'active' ? 'Connected' : 'Call Ended'}
            </Text>
          </View>
          <View style={styles.topRight}>
            {hmsConnected && (
              <View style={styles.hmsPill} testID="hms-connected-badge">
                <Ionicons name="radio" size={12} color="#48BB78" />
                <Text style={styles.hmsText}>100ms</Text>
              </View>
            )}
            {ratePerMin === 1 && (
              <View style={styles.discountPill}>
                <Text style={styles.discountText}>First Call ₹1/min!</Text>
              </View>
            )}
          </View>
        </View>

        {/* Avatar */}
        <View style={styles.avatarSection}>
          <Animated.View style={[styles.avatarRing, { borderColor: colors.accent, transform: [{ scale: status === 'active' ? pulseAnim : 1 }] }]}>
            <View style={[styles.avatarCircle, { backgroundColor: '#fff' }]}>
              <Text style={styles.avatarEmoji}>{colors.emoji}</Text>
            </View>
          </Animated.View>
          <Text style={styles.callerName}>{listenerName || 'Listener'}</Text>
          <View style={styles.shieldRow}>
            <Ionicons name="shield-checkmark" size={14} color="#A2E3C4" />
            <Text style={styles.shieldText}>Verified Listener</Text>
          </View>
        </View>

        {/* Timer & Cost */}
        <View style={styles.timerSection}>
          <Text style={styles.timer} testID="call-timer">{formatTime(seconds)}</Text>
          <Text style={styles.costDisplay} testID="call-cost">₹{cost.toFixed(1)} spent</Text>
          <Text style={styles.rateDisplay}>{callType === 'video' ? '₹8' : `₹${ratePerMin}`}/min</Text>
        </View>

        {/* Controls */}
        <View style={styles.controls}>
          <TouchableOpacity
            testID="mute-btn"
            style={[styles.controlBtn, isMuted && styles.controlBtnActive]}
            onPress={() => setIsMuted(!isMuted)}
          >
            <Ionicons name={isMuted ? 'mic-off' : 'mic'} size={24} color={isMuted ? '#fff' : '#4A5568'} />
            <Text style={[styles.controlLabel, isMuted && styles.controlLabelActive]}>{isMuted ? 'Unmute' : 'Mute'}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="speaker-btn"
            style={[styles.controlBtn, isSpeaker && styles.controlBtnActive]}
            onPress={() => setIsSpeaker(!isSpeaker)}
          >
            <Ionicons name={isSpeaker ? 'volume-high' : 'volume-medium'} size={24} color={isSpeaker ? '#fff' : '#4A5568'} />
            <Text style={[styles.controlLabel, isSpeaker && styles.controlLabelActive]}>Speaker</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="report-btn"
            style={styles.controlBtn}
            onPress={() => Alert.alert('Report', 'Report this listener?', [
              { text: 'Cancel' },
              { text: 'Report', style: 'destructive', onPress: async () => {
                try {
                  await api.post('/reports/submit', {
                    reported_user_id: listenerId,
                    call_id: callId,
                    reason: 'Inappropriate behavior',
                  });
                  Alert.alert('Reported', 'Thank you for reporting. We will review.');
                } catch (err) {}
              }},
            ])}
          >
            <Ionicons name="flag" size={24} color="#F56565" />
            <Text style={styles.controlLabel}>Report</Text>
          </TouchableOpacity>
        </View>

        {/* End Call */}
        <TouchableOpacity
          testID="end-call-btn"
          style={styles.endCallBtn}
          onPress={endCall}
          activeOpacity={0.85}
        >
          <Ionicons name="call" size={28} color="#fff" style={{ transform: [{ rotate: '135deg' }] }} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { flex: 1, alignItems: 'center', justifyContent: 'space-between', paddingVertical: 20, paddingHorizontal: 24 },
  topBar: { flexDirection: 'row', width: '100%', justifyContent: 'space-between', alignItems: 'center' },
  topRight: { flexDirection: 'row', gap: 6 },
  statusPill: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(255,255,255,0.6)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#A0AEC0' },
  activeDot: { backgroundColor: '#48BB78' },
  statusText: { fontSize: 12, fontWeight: '600', color: '#4A5568' },
  hmsPill: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#E6FFED', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  hmsText: { fontSize: 10, fontWeight: '700', color: '#48BB78' },
  discountPill: { backgroundColor: '#F6E05E', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  discountText: { fontSize: 11, fontWeight: '700', color: '#744210' },
  avatarSection: { alignItems: 'center' },
  avatarRing: { width: 140, height: 140, borderRadius: 70, borderWidth: 3, alignItems: 'center', justifyContent: 'center' },
  avatarCircle: { width: 120, height: 120, borderRadius: 60, alignItems: 'center', justifyContent: 'center' },
  avatarEmoji: { fontSize: 60 },
  callerName: { fontSize: 24, fontWeight: '700', color: '#2D3748', marginTop: 16 },
  shieldRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 },
  shieldText: { fontSize: 12, color: '#718096', fontWeight: '500' },
  timerSection: { alignItems: 'center' },
  timer: { fontSize: 48, fontWeight: '800', color: '#2D3748', letterSpacing: 2 },
  costDisplay: { fontSize: 16, fontWeight: '600', color: '#FF8FA3', marginTop: 4 },
  rateDisplay: { fontSize: 12, color: '#718096', marginTop: 2 },
  controls: { flexDirection: 'row', gap: 32 },
  controlBtn: { alignItems: 'center', gap: 6, width: 60, paddingVertical: 10, borderRadius: 16 },
  controlBtnActive: { backgroundColor: '#4A5568' },
  controlLabel: { fontSize: 11, color: '#718096', fontWeight: '500' },
  controlLabelActive: { color: '#fff' },
  endCallBtn: {
    width: 70, height: 70, borderRadius: 35, backgroundColor: '#F56565',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#F56565', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 12, elevation: 6,
  },
});
