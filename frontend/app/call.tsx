import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Animated, Alert, Dimensions,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../src/api';
import { AVATAR_COLORS } from '../src/store';
import { t } from '../src/i18n';

const { width } = Dimensions.get('window');

export default function CallScreen() {
  const router = useRouter();
  const { listenerId, listenerName, listenerAvatar, callType } = useLocalSearchParams<{
    listenerId: string; listenerName: string; listenerAvatar: string; callType: string;
  }>();

  const [callId, setCallId] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [status, setStatus] = useState<'connecting' | 'ringing' | 'active' | 'ended'>('connecting');
  const [cost, setCost] = useState(0);
  const [ratePerMin, setRatePerMin] = useState(5);
  const [hmsRoomId, setHmsRoomId] = useState('');
  const [hmsConnected, setHmsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaker, setIsSpeaker] = useState(false);
  const [connectingDots, setConnectingDots] = useState('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dotsRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const connectAnim = useRef(new Animated.Value(0)).current;
  const callIdRef = useRef('');
  const rateRef = useRef(5);

  const colors = AVATAR_COLORS[listenerAvatar || 'avatar_1'] || AVATAR_COLORS.avatar_1;

  useEffect(() => {
    // Connecting animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(connectAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
        Animated.timing(connectAnim, { toValue: 0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
    // Dots animation
    dotsRef.current = setInterval(() => {
      setConnectingDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    startCall();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (dotsRef.current) clearInterval(dotsRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startActiveCall = () => {
    if (dotsRef.current) clearInterval(dotsRef.current);
    if (pollRef.current) clearInterval(pollRef.current);
    setStatus('active');
    // Start pulse animation for active call
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.15, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();
    timerRef.current = setInterval(() => {
      setSeconds(prev => {
        const newSec = prev + 1;
        if (newSec <= 5) {
          setCost(0);
        } else {
          const effectiveRate = rateRef.current;
          if (newSec <= 60) {
            setCost(effectiveRate);
          } else {
            setCost(Math.round((effectiveRate + ((newSec - 60) / 60) * effectiveRate) * 100) / 100);
          }
        }
        return newSec;
      });
    }, 1000);
  };

  const startCall = async () => {
    try {
      const res = await api.post('/calls/start', {
        listener_id: listenerId,
        call_type: callType || 'voice',
      });
      if (res.success) {
        setCallId(res.call.id);
        callIdRef.current = res.call.id;
        setRatePerMin(res.call.rate_per_min);
        rateRef.current = res.call.rate_per_min;
        if (res.call.hms_room_id) {
          setHmsRoomId(res.call.hms_room_id);
          setHmsConnected(true);
        }
        // Transition to ringing state - waiting for listener to accept
        setStatus('ringing');
        // Poll backend every 2 seconds to check if listener accepted
        pollRef.current = setInterval(async () => {
          try {
            const statusRes = await api.get(`/calls/status/${callIdRef.current}`);
            if (statusRes.status === 'active') {
              // Listener accepted! Start the active call
              startActiveCall();
            } else if (statusRes.status === 'rejected' || statusRes.status === 'missed' || statusRes.status === 'ended') {
              // Listener rejected or call expired
              if (pollRef.current) clearInterval(pollRef.current);
              if (dotsRef.current) clearInterval(dotsRef.current);
              Alert.alert(
                statusRes.status === 'rejected' ? t('call_rejected') : t('call_ended'),
                statusRes.status === 'rejected'
                  ? t('listener_busy')
                  : t('call_ended')
              );
              router.back();
            }
          } catch (e) {
            // Polling error - ignore and retry
          }
        }, 2000);
        // Auto-cancel after 60 seconds if listener doesn't answer
        setTimeout(async () => {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
            try {
              await api.post('/calls/end', { call_id: callIdRef.current });
            } catch (e) {}
            Alert.alert(t('no_answer'), t('listener_no_answer'));
            router.back();
          }
        }, 60000);
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
      router.back();
    }
  };

  const endCall = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
    setStatus('ended');
    try {
      const res = await api.post('/calls/end', { call_id: callId || callIdRef.current });
      router.replace({
        pathname: '/rating',
        params: {
          callId: callId || callIdRef.current, listenerId, listenerName, listenerAvatar,
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

  // CONNECTING / RINGING SCREEN
  if (status === 'connecting' || status === 'ringing') {
    return (
      <SafeAreaView style={[styles.connectingContainer, { backgroundColor: colors.bg }]} testID="call-connecting-screen">
        <View style={styles.connectingContent}>
          <Text style={styles.connectingTitle}>
            {status === 'ringing' ? `${t('ringing')}${connectingDots}` : `${t('connecting')}${connectingDots}`}
          </Text>

          <Animated.View style={[styles.connectingAvatarRing, {
            borderColor: colors.accent,
            opacity: Animated.add(0.5, Animated.multiply(connectAnim, 0.5)),
            transform: [{ scale: Animated.add(1, Animated.multiply(connectAnim, 0.1)) }],
          }]}>
            <View style={[styles.connectingAvatar, { backgroundColor: '#fff' }]}>
              <Text style={styles.connectingEmoji}>{colors.emoji}</Text>
            </View>
          </Animated.View>

          <Text style={styles.connectingName}>{listenerName || 'Listener'}</Text>
          <View style={styles.connectingShield}>
            <Ionicons name="shield-checkmark" size={14} color="#A2E3C4" />
            <Text style={styles.connectingShieldText}>{t('verified_listener')}</Text>
          </View>

          {status === 'ringing' && (
            <Text style={styles.ringingHint}>{t('waiting_for_answer')}</Text>
          )}

          <View style={styles.connectingWaves}>
            {[0, 1, 2].map(i => (
              <Animated.View
                key={i}
                style={[styles.wave, {
                  backgroundColor: colors.accent,
                  opacity: Animated.add(0.2, Animated.multiply(connectAnim, 0.3)),
                  transform: [{ scale: Animated.add(1 + i * 0.3, Animated.multiply(connectAnim, 0.2)) }],
                }]}
              />
            ))}
          </View>

          <TouchableOpacity testID="cancel-connecting-btn" style={styles.cancelBtn} onPress={endCall}>
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ACTIVE CALL SCREEN
  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} testID="call-screen">
      <View style={styles.content}>
        <View style={styles.topBar}>
          <View style={styles.statusPill}>
            <View style={[styles.statusDot, styles.activeDot]} />
            <Text style={styles.statusText}>{t('connected')}</Text>
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
                <Text style={styles.discountText}>{t('first_call_discount')}</Text>
              </View>
            )}
          </View>
        </View>

        <View style={styles.avatarSection}>
          <Animated.View style={[styles.avatarRing, { borderColor: colors.accent, transform: [{ scale: pulseAnim }] }]}>
            <View style={[styles.avatarCircle, { backgroundColor: '#fff' }]}>
              <Text style={styles.avatarEmoji}>{colors.emoji}</Text>
            </View>
          </Animated.View>
          <Text style={styles.callerName}>{listenerName || 'Listener'}</Text>
          <View style={styles.shieldRow}>
            <Ionicons name="shield-checkmark" size={14} color="#A2E3C4" />
            <Text style={styles.shieldText}>{t('verified_listener')}</Text>
          </View>
        </View>

        <View style={styles.timerSection}>
          <Text style={styles.timer} testID="call-timer">{formatTime(seconds)}</Text>
          <Text style={styles.costDisplay} testID="call-cost">
            {seconds <= 5 ? t('free_under_5s') : `₹${cost.toFixed(1)} ${t('spent')}`}
          </Text>
          <Text style={styles.rateDisplay}>{callType === 'video' ? '₹8' : `₹${ratePerMin}`}/min</Text>
          {seconds <= 5 && seconds > 0 && (
            <View style={styles.freeBadge}><Ionicons name="gift" size={12} color="#48BB78" /><Text style={styles.freeText}>Free trial: {5 - seconds}s left</Text></View>
          )}
        </View>

        <View style={styles.controls}>
          <TouchableOpacity testID="mute-btn" style={[styles.controlBtn, isMuted && styles.controlBtnActive]} onPress={() => setIsMuted(!isMuted)}>
            <Ionicons name={isMuted ? 'mic-off' : 'mic'} size={24} color={isMuted ? '#fff' : '#4A5568'} />
            <Text style={[styles.controlLabel, isMuted && styles.controlLabelActive]}>{isMuted ? t('unmute') : t('mute')}</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="speaker-btn" style={[styles.controlBtn, isSpeaker && styles.controlBtnActive]} onPress={() => setIsSpeaker(!isSpeaker)}>
            <Ionicons name={isSpeaker ? 'volume-high' : 'volume-medium'} size={24} color={isSpeaker ? '#fff' : '#4A5568'} />
            <Text style={[styles.controlLabel, isSpeaker && styles.controlLabelActive]}>{t('speaker')}</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="report-btn" style={styles.controlBtn} onPress={() => Alert.alert(t('report'), 'Report this listener?', [
            { text: 'Cancel' },
            { text: t('report'), style: 'destructive', onPress: async () => {
              try {
                await api.post('/reports/submit', { reported_user_id: listenerId, call_id: callId, reason: 'Inappropriate behavior' });
                Alert.alert('Reported', 'Thank you. We will review.');
              } catch (err) {}
            }},
          ])}>
            <Ionicons name="flag" size={24} color="#F56565" />
            <Text style={styles.controlLabel}>{t('report')}</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity testID="end-call-btn" style={styles.endCallBtn} onPress={endCall} activeOpacity={0.85}>
          <Ionicons name="call" size={28} color="#fff" style={{ transform: [{ rotate: '135deg' }] }} />
        </TouchableOpacity>

        <Text style={styles.recordingNote}>Calls are recorded for safety</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  // Connecting screen styles
  connectingContainer: { flex: 1 },
  connectingContent: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  connectingTitle: { fontSize: 20, fontWeight: '600', color: '#4A5568', marginBottom: 40, width: 200, textAlign: 'center' },
  connectingAvatarRing: { width: 160, height: 160, borderRadius: 80, borderWidth: 4, alignItems: 'center', justifyContent: 'center' },
  connectingAvatar: { width: 130, height: 130, borderRadius: 65, alignItems: 'center', justifyContent: 'center' },
  connectingEmoji: { fontSize: 60 },
  connectingName: { fontSize: 24, fontWeight: '700', color: '#2D3748', marginTop: 24 },
  connectingShield: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 8 },
  connectingShieldText: { fontSize: 12, color: '#718096', fontWeight: '500' },
  connectingWaves: { position: 'absolute', alignItems: 'center', justifyContent: 'center' },
  wave: { position: 'absolute', width: 200, height: 200, borderRadius: 100 },
  ringingHint: { fontSize: 13, color: '#718096', marginTop: 12, fontWeight: '500' },
  cancelBtn: { position: 'absolute', bottom: 60, paddingHorizontal: 32, paddingVertical: 12, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.6)' },
  cancelText: { fontSize: 15, fontWeight: '600', color: '#4A5568' },
  // Active call styles
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
  freeBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#E6FFED', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, marginTop: 8 },
  freeText: { fontSize: 11, fontWeight: '600', color: '#48BB78' },
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
  recordingNote: { fontSize: 10, color: '#A0AEC0' },
});
