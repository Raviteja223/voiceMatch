import React, { useState, useRef } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert, ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { FirebaseAuthTypes } from '@react-native-firebase/auth';
import { sendFirebaseOtp, getFirebaseIdToken } from '../../src/firebase';
import api from '../../src/api';
import { saveUser } from '../../src/store';

/** Returns a stable per-install device fingerprint stored in AsyncStorage. */
async function getDeviceId(): Promise<string> {
  try {
    const stored = await AsyncStorage.getItem('vm_device_id');
    if (stored) return stored;
    const id = `${Platform.OS}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    await AsyncStorage.setItem('vm_device_id', id);
    return id;
  } catch {
    return '';
  }
}

export default function LoginScreen() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);
  const confirmationRef = useRef<FirebaseAuthTypes.ConfirmationResult | null>(null);

  const sendOtp = async () => {
    if (phone.length < 10) return Alert.alert('Error', 'Enter a valid phone number');
    setLoading(true);
    try {
      const confirmation = await sendFirebaseOtp(`+91${phone}`);
      confirmationRef.current = confirmation;
      setStep('otp');
    } catch (e: any) {
      const msg =
        e.code === 'auth/invalid-phone-number'
          ? 'Invalid phone number format.'
          : e.code === 'auth/too-many-requests'
            ? 'Too many attempts. Please try again later.'
            : e.message || 'Failed to send OTP';
      Alert.alert('Error', msg);
    }
    setLoading(false);
  };

  const verifyOtp = async () => {
    if (otp.length !== 6) return Alert.alert('Error', 'Enter the 6-digit OTP');
    if (!confirmationRef.current) return Alert.alert('Error', 'Please request OTP first');
    setLoading(true);
    try {
      // Confirm the OTP with Firebase
      await confirmationRef.current.confirm(otp);

      // Get Firebase ID token to send to our backend
      const firebaseToken = await getFirebaseIdToken();
      if (!firebaseToken) throw new Error('Failed to retrieve authentication token');

      const device_id = await getDeviceId();
      const res = await api.post('/auth/firebase-verify', {
        firebase_token: firebaseToken,
        phone: `+91${phone}`,
        device_id,
      });
      await api.setToken(res.token);
      await saveUser(res.user);

      if (res.needs_gender) {
        router.replace('/auth/gender');
      } else {
        const role = res.user.role;
        if (!res.user.onboarded) {
          router.replace(role === 'seeker' ? '/onboarding/seeker' : '/onboarding/listener');
        } else {
          router.replace(role === 'seeker' ? '/seeker/home' : '/listener/dashboard');
        }
      }
    } catch (e: any) {
      const msg =
        e.code === 'auth/invalid-verification-code'
          ? 'Invalid OTP. Please check and try again.'
          : e.code === 'auth/session-expired'
            ? 'OTP expired. Please request a new one.'
            : e.message || 'Verification failed';
      Alert.alert('Error', msg);
    }
    setLoading(false);
  };

  return (
    <SafeAreaView style={styles.container} testID="login-screen">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <TouchableOpacity testID="login-back-btn" onPress={() => router.replace('/')} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#2D3748" />
          </TouchableOpacity>

          <View style={styles.header}>
            <Text style={styles.title}>{step === 'phone' ? 'Welcome' : 'Enter OTP'}</Text>
            <Text style={styles.subtitle}>
              {step === 'phone'
                ? 'Sign in with your phone number'
                : `OTP sent to +91${phone}`}
            </Text>
          </View>

          {step === 'phone' && (
            <>
              <Text style={styles.label}>Phone Number</Text>
              <View style={styles.phoneRow}>
                <View style={styles.countryCode}>
                  <Text style={styles.countryText}>🇮🇳 +91</Text>
                </View>
                <TextInput
                  testID="phone-input"
                  style={styles.phoneInput}
                  placeholder="Enter phone number"
                  placeholderTextColor="#A0AEC0"
                  keyboardType="phone-pad"
                  maxLength={10}
                  value={phone}
                  onChangeText={setPhone}
                />
              </View>

              <TouchableOpacity
                testID="send-otp-btn"
                style={[styles.primaryBtn, phone.length < 10 && styles.btnDisabled]}
                onPress={sendOtp}
                disabled={loading || phone.length < 10}
              >
                {loading ? <ActivityIndicator color="#fff" /> : (
                  <Text style={styles.btnText}>Send OTP</Text>
                )}
              </TouchableOpacity>
            </>
          )}

          {step === 'otp' && (
            <>
              <Text style={styles.label}>6-Digit OTP</Text>
              <TextInput
                testID="otp-input"
                style={styles.otpInput}
                placeholder="------"
                placeholderTextColor="#A0AEC0"
                keyboardType="number-pad"
                maxLength={6}
                value={otp}
                onChangeText={setOtp}
                autoFocus
              />
              <View style={styles.otpHint}>
                <Ionicons name="information-circle" size={16} color="#A2E3C4" />
                <Text style={styles.hintText}>Check your SMS for the OTP</Text>
              </View>

              <TouchableOpacity
                testID="verify-otp-btn"
                style={[styles.primaryBtn, otp.length !== 6 && styles.btnDisabled]}
                onPress={verifyOtp}
                disabled={loading || otp.length !== 6}
              >
                {loading ? <ActivityIndicator color="#fff" /> : (
                  <Text style={styles.btnText}>Verify & Continue</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity testID="change-phone-btn" onPress={() => { setStep('phone'); setOtp(''); confirmationRef.current = null; }} style={styles.linkBtn}>
                <Text style={styles.linkText}>Change phone number</Text>
              </TouchableOpacity>

              <TouchableOpacity testID="resend-otp-btn" onPress={sendOtp} disabled={loading} style={styles.linkBtn}>
                <Text style={styles.linkText}>Resend OTP</Text>
              </TouchableOpacity>
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', marginBottom: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 },
  header: { marginBottom: 32 },
  title: { fontSize: 28, fontWeight: '700', color: '#2D3748' },
  subtitle: { fontSize: 14, color: '#718096', marginTop: 6 },
  label: { fontSize: 13, fontWeight: '600', color: '#4A5568', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  phoneRow: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  countryCode: { backgroundColor: '#fff', borderRadius: 14, paddingHorizontal: 14, justifyContent: 'center', borderWidth: 1, borderColor: '#E2E8F0' },
  countryText: { fontSize: 15, color: '#2D3748', fontWeight: '500' },
  phoneInput: { flex: 1, backgroundColor: '#fff', borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, borderWidth: 1, borderColor: '#E2E8F0', color: '#2D3748' },
  otpInput: { backgroundColor: '#fff', borderRadius: 14, paddingHorizontal: 16, paddingVertical: 16, fontSize: 24, letterSpacing: 12, textAlign: 'center', borderWidth: 1, borderColor: '#E2E8F0', color: '#2D3748', fontWeight: '700', marginBottom: 12 },
  otpHint: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 24, justifyContent: 'center' },
  hintText: { fontSize: 13, color: '#718096' },
  primaryBtn: { backgroundColor: '#FF8FA3', paddingVertical: 16, borderRadius: 28, alignItems: 'center', justifyContent: 'center', shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6, marginTop: 8 },
  btnDisabled: { opacity: 0.5 },
  btnText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  linkBtn: { alignItems: 'center', marginTop: 20 },
  linkText: { fontSize: 14, color: '#FF8FA3', fontWeight: '600' },
});
