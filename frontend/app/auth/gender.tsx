import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { saveUser, getUser } from '../../src/store';

export default function GenderScreen() {
  const router = useRouter();
  const [selected, setSelected] = useState<'male' | 'female' | ''>('');
  const [loading, setLoading] = useState(false);

  const handleContinue = async () => {
    if (!selected) return;
    setLoading(true);
    try {
      const res = await api.post('/auth/set-gender', { gender: selected });
      api.setToken(res.token);
      await saveUser(res.user);
      const role = res.user.role;
      router.replace(role === 'seeker' ? '/onboarding/seeker' : '/onboarding/listener');
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setLoading(false);
  };

  return (
    <SafeAreaView style={styles.container} testID="gender-screen">
      <View style={styles.content}>
        <View style={styles.topSection}>
          <View style={styles.iconCircle}>
            <Ionicons name="people" size={40} color="#FF8FA3" />
          </View>
          <Text style={styles.title}>Tell us about yourself</Text>
          <Text style={styles.subtitle}>This helps us personalize your experience</Text>
        </View>

        <View style={styles.optionsSection}>
          <Text style={styles.label}>I am</Text>
          <View style={styles.optionRow}>
            <TouchableOpacity
              testID="gender-male-btn"
              style={[styles.optionCard, selected === 'male' && styles.optionCardActiveMale]}
              onPress={() => setSelected('male')}
              activeOpacity={0.85}
            >
              <View style={[styles.optionIcon, selected === 'male' && styles.optionIconActiveMale]}>
                <Ionicons name="man" size={36} color={selected === 'male' ? '#fff' : '#85C1E9'} />
              </View>
              <Text style={[styles.optionTitle, selected === 'male' && styles.optionTitleActive]}>Male</Text>
              <Text style={[styles.optionDesc, selected === 'male' && styles.optionDescActive]}>Find a listener</Text>
              {selected === 'male' && (
                <View style={styles.checkBadge}>
                  <Ionicons name="checkmark-circle" size={22} color="#85C1E9" />
                </View>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              testID="gender-female-btn"
              style={[styles.optionCard, selected === 'female' && styles.optionCardActiveFemale]}
              onPress={() => setSelected('female')}
              activeOpacity={0.85}
            >
              <View style={[styles.optionIcon, selected === 'female' && styles.optionIconActiveFemale]}>
                <Ionicons name="woman" size={36} color={selected === 'female' ? '#fff' : '#FF8FA3'} />
              </View>
              <Text style={[styles.optionTitle, selected === 'female' && styles.optionTitleActive]}>Female</Text>
              <Text style={[styles.optionDesc, selected === 'female' && styles.optionDescActive]}>Become a listener</Text>
              {selected === 'female' && (
                <View style={styles.checkBadge}>
                  <Ionicons name="checkmark-circle" size={22} color="#FF8FA3" />
                </View>
              )}
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.bottomSection}>
          <TouchableOpacity
            testID="gender-continue-btn"
            style={[styles.primaryBtn, !selected && styles.btnDisabled]}
            onPress={handleContinue}
            disabled={!selected || loading}
          >
            {loading ? <ActivityIndicator color="#fff" /> : (
              <Text style={styles.btnText}>Continue</Text>
            )}
          </TouchableOpacity>
          <View style={styles.infoRow}>
            <Ionicons name="shield-checkmark" size={14} color="#A2E3C4" />
            <Text style={styles.infoText}>Your information is safe with us</Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  content: { flex: 1, paddingHorizontal: 24, justifyContent: 'space-between', paddingVertical: 20 },
  topSection: { alignItems: 'center', paddingTop: 20 },
  iconCircle: {
    width: 80, height: 80, borderRadius: 40, backgroundColor: '#FFE0E6',
    alignItems: 'center', justifyContent: 'center', marginBottom: 20,
  },
  title: { fontSize: 26, fontWeight: '700', color: '#2D3748' },
  subtitle: { fontSize: 14, color: '#718096', marginTop: 6 },
  optionsSection: { flex: 1, justifyContent: 'center' },
  label: { fontSize: 13, fontWeight: '600', color: '#4A5568', marginBottom: 14, textTransform: 'uppercase', letterSpacing: 0.5, textAlign: 'center' },
  optionRow: { flexDirection: 'row', gap: 14 },
  optionCard: {
    flex: 1, backgroundColor: '#fff', borderRadius: 20, padding: 20,
    alignItems: 'center', borderWidth: 2, borderColor: '#E2E8F0',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1,
  },
  optionCardActiveMale: { borderColor: '#85C1E9', backgroundColor: '#EBF5FB' },
  optionCardActiveFemale: { borderColor: '#FF8FA3', backgroundColor: '#FFF0F3' },
  optionIcon: {
    width: 68, height: 68, borderRadius: 34, backgroundColor: '#F7F7F7',
    alignItems: 'center', justifyContent: 'center', marginBottom: 12,
  },
  optionIconActiveMale: { backgroundColor: '#85C1E9' },
  optionIconActiveFemale: { backgroundColor: '#FF8FA3' },
  optionTitle: { fontSize: 18, fontWeight: '700', color: '#2D3748' },
  optionTitleActive: { color: '#2D3748' },
  optionDesc: { fontSize: 12, color: '#A0AEC0', marginTop: 4 },
  optionDescActive: { color: '#718096' },
  checkBadge: { position: 'absolute', top: 10, right: 10 },
  bottomSection: { alignItems: 'center', gap: 12 },
  primaryBtn: {
    backgroundColor: '#FF8FA3', paddingVertical: 16, borderRadius: 28,
    alignItems: 'center', width: '100%',
    shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6,
  },
  btnDisabled: { opacity: 0.4 },
  btnText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  infoText: { fontSize: 12, color: '#A0AEC0' },
});
