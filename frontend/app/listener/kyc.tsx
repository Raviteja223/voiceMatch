import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, Alert, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

export default function KYCScreen() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [aadhaarLast4, setAadhaarLast4] = useState('');
  const [panNumber, setPanNumber] = useState('');
  const [dob, setDob] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('pending');

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/kyc/status');
        setStatus(res.status);
      } catch (e) {}
    })();
  }, []);

  const handleSubmit = async () => {
    if (!fullName.trim()) return Alert.alert('Error', 'Enter your full name');
    if (aadhaarLast4.length !== 4) return Alert.alert('Error', 'Enter last 4 digits of Aadhaar');
    if (!dob.match(/^\d{4}-\d{2}-\d{2}$/)) return Alert.alert('Error', 'Enter DOB as YYYY-MM-DD');
    setLoading(true);
    try {
      const res = await api.post('/kyc/submit', {
        full_name: fullName.trim(),
        aadhaar_last4: aadhaarLast4,
        pan_number: panNumber.trim() || null,
        dob,
      });
      setStatus('submitted');
      Alert.alert('Submitted', res.message);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setLoading(false);
  };

  if (status === 'verified') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-verified-screen">
        <View style={styles.header}>
          <TouchableOpacity testID="kyc-back-btn" onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#2D3748" />
          </TouchableOpacity>
          <Text style={styles.title}>KYC Verification</Text>
        </View>
        <View style={styles.verifiedCard}>
          <View style={styles.verifiedIcon}><Ionicons name="shield-checkmark" size={48} color="#48BB78" /></View>
          <Text style={styles.verifiedTitle}>KYC Verified</Text>
          <Text style={styles.verifiedSub}>Your identity has been verified successfully</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (status === 'submitted') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-submitted-screen">
        <View style={styles.header}>
          <TouchableOpacity testID="kyc-back-btn" onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#2D3748" />
          </TouchableOpacity>
          <Text style={styles.title}>KYC Verification</Text>
        </View>
        <View style={styles.verifiedCard}>
          <View style={[styles.verifiedIcon, { backgroundColor: '#FFF5E6' }]}><Ionicons name="hourglass" size={48} color="#ED8936" /></View>
          <Text style={styles.verifiedTitle}>Under Review</Text>
          <Text style={styles.verifiedSub}>Your documents are being verified. This usually takes 24-48 hours.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="kyc-screen">
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.header}>
            <TouchableOpacity testID="kyc-back-btn" onPress={() => router.back()} style={styles.backBtn}>
              <Ionicons name="arrow-back" size={24} color="#2D3748" />
            </TouchableOpacity>
            <Text style={styles.title}>KYC Verification</Text>
          </View>

          <View style={styles.infoCard}>
            <Ionicons name="shield-half" size={24} color="#85C1E9" />
            <View style={styles.infoContent}>
              <Text style={styles.infoTitle}>Why KYC?</Text>
              <Text style={styles.infoText}>KYC verification ensures safety for all users and is required to withdraw earnings.</Text>
            </View>
          </View>

          <View style={styles.formCard}>
            <Text style={styles.label}>Full Name (as per Aadhaar)</Text>
            <TextInput testID="kyc-name-input" style={styles.input} placeholder="Enter full name" placeholderTextColor="#A0AEC0" value={fullName} onChangeText={setFullName} />

            <Text style={styles.label}>Last 4 digits of Aadhaar</Text>
            <TextInput testID="kyc-aadhaar-input" style={styles.input} placeholder="XXXX" placeholderTextColor="#A0AEC0" keyboardType="number-pad" maxLength={4} value={aadhaarLast4} onChangeText={setAadhaarLast4} />

            <Text style={styles.label}>PAN Number (Optional)</Text>
            <TextInput testID="kyc-pan-input" style={styles.input} placeholder="ABCDE1234F" placeholderTextColor="#A0AEC0" autoCapitalize="characters" maxLength={10} value={panNumber} onChangeText={setPanNumber} />

            <Text style={styles.label}>Date of Birth</Text>
            <TextInput testID="kyc-dob-input" style={styles.input} placeholder="YYYY-MM-DD" placeholderTextColor="#A0AEC0" maxLength={10} value={dob} onChangeText={setDob} />

            <View style={styles.privacyRow}>
              <Ionicons name="lock-closed" size={14} color="#A2E3C4" />
              <Text style={styles.privacyText}>Your data is encrypted and stored securely. We only store last 4 digits of Aadhaar.</Text>
            </View>

            <TouchableOpacity testID="kyc-submit-btn" style={styles.submitBtn} onPress={handleSubmit} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" /> : (
                <Text style={styles.submitText}>Submit KYC</Text>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  scroll: { paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 16, gap: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  infoCard: { flexDirection: 'row', gap: 12, backgroundColor: '#EBF5FB', borderRadius: 14, padding: 14, marginHorizontal: 20, marginBottom: 20 },
  infoContent: { flex: 1 },
  infoTitle: { fontSize: 14, fontWeight: '700', color: '#2D3748' },
  infoText: { fontSize: 12, color: '#718096', marginTop: 4 },
  formCard: { backgroundColor: '#fff', borderRadius: 18, padding: 20, marginHorizontal: 20 },
  label: { fontSize: 13, fontWeight: '600', color: '#4A5568', marginBottom: 6, marginTop: 14, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: { backgroundColor: '#F7F7F7', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#2D3748', borderWidth: 1, borderColor: '#E2E8F0' },
  privacyRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 16, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#F0F0F0' },
  privacyText: { fontSize: 11, color: '#A0AEC0', flex: 1 },
  submitBtn: { backgroundColor: '#A2E3C4', paddingVertical: 16, borderRadius: 28, alignItems: 'center', marginTop: 20 },
  submitText: { fontSize: 16, fontWeight: '700', color: '#1A4D2E' },
  verifiedCard: { alignItems: 'center', paddingTop: 60, paddingHorizontal: 20 },
  verifiedIcon: { width: 96, height: 96, borderRadius: 48, backgroundColor: '#E6FFED', alignItems: 'center', justifyContent: 'center', marginBottom: 20 },
  verifiedTitle: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  verifiedSub: { fontSize: 14, color: '#718096', marginTop: 8, textAlign: 'center' },
});
