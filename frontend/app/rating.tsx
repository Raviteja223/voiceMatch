import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, Animated } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../src/api';
import { AVATAR_COLORS } from '../src/store';

const RATINGS = [
  { key: 'great', label: 'Great', icon: 'happy', color: '#48BB78' },
  { key: 'good', label: 'Good', icon: 'thumbs-up', color: '#85C1E9' },
  { key: 'okay', label: 'Okay', icon: 'remove-circle', color: '#F6E05E' },
  { key: 'bad', label: 'Bad', icon: 'thumbs-down', color: '#F56565' },
];

export default function RatingScreen() {
  const router = useRouter();
  const { callId, listenerName, listenerAvatar, duration, cost, isListener } = useLocalSearchParams<{
    callId: string; listenerName: string; listenerAvatar: string; duration: string; cost: string; isListener: string;
  }>();
  const [selectedRating, setSelectedRating] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [videoUnlocked, setVideoUnlocked] = useState(false);

  const isListenerSide = isListener === 'true';
  const colors = AVATAR_COLORS[listenerAvatar || 'avatar_1'] || AVATAR_COLORS.avatar_1;
  const durationNum = parseInt(duration || '0');

  const navigateHome = () => {
    router.replace(isListenerSide ? '/listener/dashboard' : '/seeker/home');
  };

  const submit = async () => {
    if (!selectedRating) return;
    setSubmitting(true);
    try {
      const res = await api.post('/ratings/submit', { call_id: callId, rating: selectedRating });
      if (res.video_unlocked) {
        // Show video unlock celebration before navigating
        setVideoUnlocked(true);
        setTimeout(() => navigateHome(), 2800);
      } else {
        navigateHome();
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
      setSubmitting(false);
    }
  };

  // Video unlock celebration overlay
  if (videoUnlocked) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.unlockOverlay}>
          <View style={styles.unlockCard}>
            <Text style={styles.unlockEmoji}>🎥</Text>
            <Text style={styles.unlockTitle}>Video Unlocked!</Text>
            <Text style={styles.unlockSub}>
              You and <Text style={{ fontWeight: '700' }}>{listenerName}</Text> both had a great conversation.{'\n'}
              Video calls are now available between you!
            </Text>
            <View style={styles.unlockBadge}>
              <Ionicons name="videocam" size={16} color="#BB8FCE" />
              <Text style={styles.unlockBadgeText}>Video call now available</Text>
            </View>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="rating-screen">
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Call Ended</Text>
          <Text style={styles.subtitle}>
            {isListenerSide ? 'How was this conversation?' : 'How was your conversation?'}
          </Text>
        </View>

        <View style={styles.summaryCard}>
          <View style={[styles.avatarCircle, { backgroundColor: colors.bg }]}>
            <Text style={styles.avatarEmoji}>{colors.emoji}</Text>
          </View>
          <Text style={styles.listenerName}>{listenerName || 'User'}</Text>
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Ionicons name="time" size={16} color="#718096" />
              <Text style={styles.statText}>{Math.floor(durationNum / 60)}m {durationNum % 60}s</Text>
            </View>
            {!isListenerSide && (
              <>
                <View style={styles.statDivider} />
                <View style={styles.stat}>
                  <Ionicons name="wallet" size={16} color="#FF8FA3" />
                  <Text style={styles.statText}>₹{parseFloat(cost || '0').toFixed(1)}</Text>
                </View>
              </>
            )}
          </View>

          {/* Video unlock progress hint */}
          {durationNum >= 300 && (
            <View style={styles.videoUnlockHint}>
              <Ionicons name="videocam" size={14} color="#BB8FCE" />
              <Text style={styles.videoUnlockHintText}>
                Rate Great or Good to unlock video calls!
              </Text>
            </View>
          )}
          {durationNum < 300 && durationNum > 0 && (
            <View style={styles.videoLockHint}>
              <Ionicons name="lock-closed" size={12} color="#A0AEC0" />
              <Text style={styles.videoLockHintText}>
                Talk 5+ min & rate highly to unlock video
              </Text>
            </View>
          )}
        </View>

        <View style={styles.ratingSection}>
          <Text style={styles.ratingLabel}>Rate this conversation</Text>
          <View style={styles.ratingRow}>
            {RATINGS.map(r => (
              <TouchableOpacity
                key={r.key}
                testID={`rating-${r.key}`}
                style={[styles.ratingBtn, selectedRating === r.key && { backgroundColor: r.color, borderColor: r.color }]}
                onPress={() => setSelectedRating(r.key)}
              >
                <Ionicons name={r.icon as any} size={24} color={selectedRating === r.key ? '#fff' : r.color} />
                <Text style={[styles.ratingText, selectedRating === r.key && { color: '#fff' }]}>{r.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.bottomSection}>
          <TouchableOpacity
            testID="submit-rating-btn"
            style={[styles.submitBtn, !selectedRating && styles.btnDisabled]}
            onPress={submit}
            disabled={!selectedRating || submitting}
          >
            <Text style={styles.submitText}>Submit & Continue</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="skip-rating-btn" onPress={navigateHome}>
            <Text style={styles.skipText}>Skip</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  content: { flex: 1, paddingHorizontal: 24, justifyContent: 'space-between', paddingVertical: 20 },
  header: { alignItems: 'center' },
  title: { fontSize: 24, fontWeight: '700', color: '#2D3748' },
  subtitle: { fontSize: 14, color: '#718096', marginTop: 4 },
  summaryCard: { backgroundColor: '#fff', borderRadius: 20, padding: 24, alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  avatarCircle: { width: 64, height: 64, borderRadius: 32, alignItems: 'center', justifyContent: 'center' },
  avatarEmoji: { fontSize: 32 },
  listenerName: { fontSize: 18, fontWeight: '700', color: '#2D3748', marginTop: 10 },
  statsRow: { flexDirection: 'row', alignItems: 'center', marginTop: 12, gap: 16 },
  stat: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  statText: { fontSize: 14, fontWeight: '600', color: '#4A5568' },
  statDivider: { width: 1, height: 20, backgroundColor: '#E2E8F0' },
  videoUnlockHint: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12, backgroundColor: '#F3E8FF', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10 },
  videoUnlockHintText: { fontSize: 12, color: '#BB8FCE', fontWeight: '600' },
  videoLockHint: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12 },
  videoLockHintText: { fontSize: 11, color: '#A0AEC0', fontWeight: '500' },
  ratingSection: { alignItems: 'center' },
  ratingLabel: { fontSize: 15, fontWeight: '600', color: '#4A5568', marginBottom: 16 },
  ratingRow: { flexDirection: 'row', gap: 10 },
  ratingBtn: { alignItems: 'center', paddingVertical: 12, paddingHorizontal: 14, borderRadius: 14, backgroundColor: '#fff', borderWidth: 1.5, borderColor: '#E2E8F0', flex: 1 },
  ratingText: { fontSize: 11, fontWeight: '600', color: '#4A5568', marginTop: 4 },
  bottomSection: { alignItems: 'center', gap: 12 },
  submitBtn: { backgroundColor: '#FF8FA3', paddingVertical: 16, borderRadius: 28, alignItems: 'center', width: '100%' },
  btnDisabled: { opacity: 0.5 },
  submitText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  skipText: { fontSize: 14, color: '#A0AEC0', fontWeight: '500' },
  // Video unlock celebration
  unlockOverlay: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  unlockCard: { backgroundColor: '#fff', borderRadius: 28, padding: 36, alignItems: 'center', shadowColor: '#BB8FCE', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.3, shadowRadius: 24, elevation: 10, width: '100%' },
  unlockEmoji: { fontSize: 64, marginBottom: 16 },
  unlockTitle: { fontSize: 28, fontWeight: '800', color: '#2D3748', marginBottom: 12 },
  unlockSub: { fontSize: 15, color: '#718096', textAlign: 'center', lineHeight: 22, marginBottom: 20 },
  unlockBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#F3E8FF', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20 },
  unlockBadgeText: { fontSize: 14, fontWeight: '700', color: '#BB8FCE' },
});
