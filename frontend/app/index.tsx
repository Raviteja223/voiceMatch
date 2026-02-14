import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated, Dimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useI18n, AppLanguage } from '../src/i18n';

const { width } = Dimensions.get('window');

export default function WelcomeScreen() {
  const router = useRouter();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const { t, setLanguage, language } = useI18n();

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 800, useNativeDriver: true }),
    ]).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.08, duration: 1200, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1200, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  return (
    <SafeAreaView style={styles.container} testID="welcome-screen">
      <View style={styles.content}>
        <View style={styles.topSection}>
          <Animated.View style={[styles.logoContainer, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
            <View style={styles.logoCircle}>
              <Ionicons name="chatbubbles" size={48} color="#FF8FA3" />
            </View>
            <Text style={styles.appName}>VoiceMatch</Text>
            <Text style={styles.tagline}>Voice Companionship Platform</Text>
          </Animated.View>

          <Animated.View style={[styles.features, { opacity: fadeAnim }]}>
            <View style={styles.featureRow}>
              <View style={styles.featureIcon}>
                <Ionicons name="shield-checkmark" size={20} color="#A2E3C4" />
              </View>
              <Text style={styles.featureText}>Safe & Verified Conversations</Text>
            </View>
            <View style={styles.featureRow}>
              <View style={styles.featureIcon}>
                <Ionicons name="mic" size={20} color="#FF8FA3" />
              </View>
              <Text style={styles.featureText}>Voice-First Companionship</Text>
            </View>
            <View style={styles.featureRow}>
              <View style={styles.featureIcon}>
                <Ionicons name="heart" size={20} color="#F6E05E" />
              </View>
              <Text style={styles.featureText}>Respectful & Caring Listeners</Text>
            </View>
          </Animated.View>
        </View>

        <View style={styles.bottomSection}>
          <View style={styles.langRow}>
            {([['en','EN'], ['hi','हिं'], ['ta','த'], ['te','తె'], ['kn','ಕ'], ['ml','മ']] as [AppLanguage, string][]).map(([code, label]) => (
              <TouchableOpacity key={code} style={[styles.langChip, language === code && styles.langChipActive]} onPress={() => setLanguage(code)}>
                <Text style={[styles.langChipText, language === code && styles.langChipTextActive]}>{label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
            <TouchableOpacity
              testID="get-started-btn"
              style={styles.primaryBtn}
              onPress={() => router.push('/auth/login')}
              activeOpacity={0.85}
            >
              <Ionicons name="chatbubble-ellipses" size={22} color="#fff" />
              <Text style={styles.primaryBtnText}>{t('getStarted')}</Text>
            </TouchableOpacity>
          </Animated.View>
          <Text style={styles.disclaimer}>18+ only · Respectful conversations only</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  content: { flex: 1, justifyContent: 'space-between', paddingHorizontal: 24 },
  topSection: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 40 },
  logoContainer: { alignItems: 'center', marginBottom: 48 },
  logoCircle: {
    width: 96, height: 96, borderRadius: 48,
    backgroundColor: '#FFE0E6', alignItems: 'center', justifyContent: 'center',
    marginBottom: 20, shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2, shadowRadius: 12, elevation: 6,
  },
  appName: { fontSize: 32, fontWeight: '700', color: '#2D3748', letterSpacing: -0.5 },
  tagline: { fontSize: 15, color: '#718096', marginTop: 6, fontWeight: '500' },
  features: { width: '100%', gap: 16 },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 8 },
  featureIcon: {
    width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  featureText: { fontSize: 15, color: '#4A5568', fontWeight: '500', flex: 1 },
  bottomSection: { paddingBottom: 24, alignItems: 'center' },
  primaryBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10,
    backgroundColor: '#FF8FA3', paddingVertical: 16, paddingHorizontal: 48,
    borderRadius: 28, width: width - 48,
    shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6,
  },
  primaryBtnText: { fontSize: 17, fontWeight: '700', color: '#fff' },
  disclaimer: { fontSize: 12, color: '#A0AEC0', marginTop: 14 },
  langRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginBottom: 12 },
  langChip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 14, backgroundColor: '#fff' },
  langChipActive: { backgroundColor: '#FF8FA3' },
  langChipText: { color: '#4A5568', fontWeight: '600', fontSize: 12 },
  langChipTextActive: { color: '#fff' },
});
