import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, Alert, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { LANGUAGES, INTENT_TAGS, saveUser, getUser } from '../../src/store';

export default function SeekerOnboarding() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [selectedLangs, setSelectedLangs] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);

  const toggleItem = (list: string[], item: string, setter: (v: string[]) => void) => {
    setter(list.includes(item) ? list.filter(i => i !== item) : [...list, item]);
  };

  const submit = async () => {
    if (!name.trim()) return Alert.alert('Error', 'Enter your name');
    if (parseInt(age) < 18) return Alert.alert('Error', 'You must be 18+');
    if (selectedLangs.length === 0) return Alert.alert('Error', 'Select at least one language');
    if (selectedTags.length === 0) return Alert.alert('Error', 'Select at least one interest');
    setLoading(true);
    try {
      await api.post('/seekers/onboard', {
        name: name.trim(), age: parseInt(age),
        languages: selectedLangs, intent_tags: selectedTags,
      });
      const user = await getUser();
      if (user) { user.onboarded = true; user.name = name; await saveUser(user); }
      router.replace('/seeker/home');
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setLoading(false);
  };

  const steps = [
    // Step 0: Name & Age
    <View key="0">
      <Text style={styles.stepTitle}>Tell us about yourself</Text>
      <Text style={styles.stepSub}>We'll use this to find the best listeners for you</Text>
      <Text style={styles.label}>Your Name</Text>
      <TextInput testID="seeker-name-input" style={styles.input} placeholder="Enter your name" placeholderTextColor="#A0AEC0" value={name} onChangeText={setName} />
      <Text style={styles.label}>Your Age</Text>
      <TextInput testID="seeker-age-input" style={styles.input} placeholder="18+" placeholderTextColor="#A0AEC0" keyboardType="number-pad" value={age} onChangeText={setAge} maxLength={2} />
    </View>,
    // Step 1: Languages
    <View key="1">
      <Text style={styles.stepTitle}>Languages you speak</Text>
      <Text style={styles.stepSub}>Select languages you're comfortable with</Text>
      <View style={styles.chipGrid}>
        {LANGUAGES.map(l => (
          <TouchableOpacity key={l} testID={`lang-${l}`} style={[styles.chip, selectedLangs.includes(l) && styles.chipActive]} onPress={() => toggleItem(selectedLangs, l, setSelectedLangs)}>
            <Text style={[styles.chipText, selectedLangs.includes(l) && styles.chipTextActive]}>{l}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>,
    // Step 2: Intent tags
    <View key="2">
      <Text style={styles.stepTitle}>What brings you here?</Text>
      <Text style={styles.stepSub}>Select what you're looking for</Text>
      <View style={styles.chipGrid}>
        {INTENT_TAGS.map(t => (
          <TouchableOpacity key={t} testID={`tag-${t}`} style={[styles.chip, selectedTags.includes(t) && styles.chipActive]} onPress={() => toggleItem(selectedTags, t, setSelectedTags)}>
            <Text style={[styles.chipText, selectedTags.includes(t) && styles.chipTextActive]}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>,
  ];

  return (
    <SafeAreaView style={styles.container} testID="seeker-onboarding-screen">
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.progressRow}>
          {[0, 1, 2].map(i => (
            <View key={i} style={[styles.progressDot, step >= i && styles.progressDotActive]} />
          ))}
        </View>
        {steps[step]}
        <View style={styles.btnRow}>
          {step > 0 && (
            <TouchableOpacity testID="seeker-onboard-back" style={styles.outlineBtn} onPress={() => setStep(step - 1)}>
              <Text style={styles.outlineBtnText}>Back</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            testID="seeker-onboard-next"
            style={[styles.primaryBtn, { flex: step > 0 ? 1 : undefined }]}
            onPress={() => step < 2 ? setStep(step + 1) : submit()}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="#fff" /> : (
              <Text style={styles.btnText}>{step < 2 ? 'Next' : 'Start Exploring'}</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 20, paddingBottom: 40 },
  progressRow: { flexDirection: 'row', gap: 8, marginBottom: 32, justifyContent: 'center' },
  progressDot: { width: 32, height: 4, borderRadius: 2, backgroundColor: '#E2E8F0' },
  progressDotActive: { backgroundColor: '#FF8FA3', width: 48 },
  stepTitle: { fontSize: 24, fontWeight: '700', color: '#2D3748', marginBottom: 6 },
  stepSub: { fontSize: 14, color: '#718096', marginBottom: 28 },
  label: { fontSize: 13, fontWeight: '600', color: '#4A5568', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: { backgroundColor: '#fff', borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, borderWidth: 1, borderColor: '#E2E8F0', color: '#2D3748', marginBottom: 20 },
  chipGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, backgroundColor: '#fff', borderWidth: 1.5, borderColor: '#E2E8F0' },
  chipActive: { backgroundColor: '#FF8FA3', borderColor: '#FF8FA3' },
  chipText: { fontSize: 14, fontWeight: '500', color: '#4A5568' },
  chipTextActive: { color: '#fff' },
  btnRow: { flexDirection: 'row', gap: 12, marginTop: 40 },
  outlineBtn: { paddingVertical: 14, paddingHorizontal: 24, borderRadius: 24, borderWidth: 2, borderColor: '#E2E8F0' },
  outlineBtnText: { fontSize: 15, fontWeight: '600', color: '#718096' },
  primaryBtn: { backgroundColor: '#FF8FA3', paddingVertical: 16, paddingHorizontal: 32, borderRadius: 28, alignItems: 'center', flex: 1 },
  btnText: { fontSize: 16, fontWeight: '700', color: '#fff' },
});
