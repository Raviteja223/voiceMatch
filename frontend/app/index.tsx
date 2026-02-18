import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated, Dimensions, Image, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../src/api';
import { getUser } from '../src/store';

const { width } = Dimensions.get('window');

export default function WelcomeScreen() {
  const router = useRouter();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Check for existing session on app open
    const checkSession = async () => {
      await api.init();
      const user = await getUser();
      if (user && api.getToken()) {
        // Restore session - navigate to appropriate home screen
        if (!user.onboarded) {
          router.replace(user.role === 'seeker' ? '/onboarding/seeker' : '/onboarding/listener');
        } else {
          router.replace(user.role === 'seeker' ? '/seeker/home' : '/listener/dashboard');
        }
        return;
      }
      // No valid session, show welcome screen
      setChecking(false);
      startAnimations();
    };

    checkSession();
  }, []);

  const startAnimations = () => {
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
  };

  if (checking) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color="#FF8FA3" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="welcome-screen">
      <View style={styles.content}>
        <View style={styles.topSection}>
          <Animated.View style={[styles.logoContainer, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
            <Image
              source={require('../assets/images/konnectra-logo.png')}
              style={styles.logoImage}
              resizeMode="contain"
            />
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
          <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
            <TouchableOpacity
              testID="get-started-btn"
              style={styles.primaryBtn}
              onPress={() => router.replace('/auth/login')}
              activeOpacity={0.85}
            >
              <Ionicons name="chatbubble-ellipses" size={22} color="#fff" />
              <Text style={styles.primaryBtnText}>Get Started</Text>
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
  loaderContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  content: { flex: 1, justifyContent: 'space-between', paddingHorizontal: 24 },
  topSection: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 40 },
  logoContainer: { alignItems: 'center', marginBottom: 48 },
  logoImage: {
    width: 220, height: 80, marginBottom: 12,
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
});
