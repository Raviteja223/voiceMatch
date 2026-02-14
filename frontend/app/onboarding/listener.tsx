import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, Alert, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { LANGUAGES, STYLE_TAGS, TOPIC_TAGS, AVATAR_COLORS, saveUser, getUser } from '../../src/store';

const BOUNDARY_QUESTIONS = [
  'I am comfortable discussing personal topics',
  'I can handle emotional conversations',
  'I prefer light and fun topics',
  'I am okay with career/study advice',
  'I am open to spiritual/philosophical talks',
];

const AVATARS = Object.entries(AVATAR_COLORS).map(([id, data]) => ({ id, ...data }));

export default function ListenerOnboarding() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState('');
  const [selectedLangs, setSelectedLangs] = useState<string[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<string[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [boundaryAnswers, setBoundaryAnswers] = useState<number[]>([0, 0, 0, 0, 0]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);

  const toggleItem = (list: string[], item: string, setter: (v: string[]) => void) => {
    setter(list.includes(item) ? list.filter(i => i !== item) : [...list, item]);
  };

  const toggleBoundary = (idx: number) => {
    const next = [...boundaryAnswers];
    next[idx] = next[idx] === 1 ? 0 : 1;
    setBoundaryAnswers(next);
  };

  const submit = async () => {
    if (!name.trim() || !selectedAvatar || selectedLangs.length === 0) {
      return Alert.alert('Error', 'Please complete all required fields');
    }
    setLoading(true);
    try {
      await api.post('/listeners/onboard', {
        name: name.trim(), age: parseInt(age) || 20,
        languages: selectedLangs, avatar_id: selectedAvatar,
        style_tags: selectedStyle, topic_tags: selectedTopics,
        boundary_answers: boundaryAnswers,
      });
      const user = await getUser();
      if (user) { user.onboarded = true; user.name = name; await saveUser(user); }
      router.replace('/listener/dashboard');
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setLoading(false);
  };

  const steps = [
    // Step 0: Name, Age & Avatar
    <View key="0">
      <Text style={styles.stepTitle}>Create your profile</Text>
      <Text style={styles.stepSub}>Choose a display name and avatar</Text>
      <Text style={styles.label}>Display Name</Text>
      <TextInput testID="listener-name-input" style={styles.input} placeholder="Your display name" placeholderTextColor="#A0AEC0" value={name} onChangeText={setName} />
      <Text style={styles.label}>Age</Text>
      <TextInput testID="listener-age-input" style={styles.input} placeholder="18+" placeholderTextColor="#A0AEC0" keyboardType="number-pad" value={age} onChangeText={setAge} maxLength={2} />
      <Text style={styles.label}>Choose Avatar</Text>
      <View style={styles.avatarGrid}>
        {AVATARS.map(av => (
          <TouchableOpacity key={av.id} testID={`avatar-${av.id}`} style={[styles.avatarItem, selectedAvatar === av.id && { borderColor: av.accent, borderWidth: 3 }]} onPress={() => setSelectedAvatar(av.id)}>
            <View style={[styles.avatarCircle, { backgroundColor: av.bg }]}>
              <Text style={styles.avatarEmoji}>{av.emoji}</Text>
            </View>
            {selectedAvatar === av.id && <Ionicons name="checkmark-circle" size={20} color={av.accent} style={styles.avatarCheck} />}
          </TouchableOpacity>
        ))}
      </View>
    </View>,
    // Step 1: Languages
    <View key="1">
      <Text style={styles.stepTitle}>Languages you speak</Text>
      <Text style={styles.stepSub}>Seekers will be matched based on language</Text>
      <View style={styles.chipGrid}>
        {LANGUAGES.map(l => (
          <TouchableOpacity key={l} testID={`listener-lang-${l}`} style={[styles.chip, selectedLangs.includes(l) && styles.chipActive]} onPress={() => toggleItem(selectedLangs, l, setSelectedLangs)}>
            <Text style={[styles.chipText, selectedLangs.includes(l) && styles.chipTextActive]}>{l}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>,
    // Step 2: Style & Topics
    <View key="2">
      <Text style={styles.stepTitle}>Your style & topics</Text>
      <Text style={styles.stepSub}>What describes your conversation style?</Text>
      <Text style={styles.label}>Style</Text>
      <View style={styles.chipGrid}>
        {STYLE_TAGS.map(t => (
          <TouchableOpacity key={t} testID={`style-${t}`} style={[styles.chip, selectedStyle.includes(t) && styles.chipActiveGreen]} onPress={() => toggleItem(selectedStyle, t, setSelectedStyle)}>
            <Text style={[styles.chipText, selectedStyle.includes(t) && styles.chipTextActive]}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <Text style={[styles.label, { marginTop: 20 }]}>Topics</Text>
      <View style={styles.chipGrid}>
        {TOPIC_TAGS.map(t => (
          <TouchableOpacity key={t} testID={`topic-${t}`} style={[styles.chip, selectedTopics.includes(t) && styles.chipActiveYellow]} onPress={() => toggleItem(selectedTopics, t, setSelectedTopics)}>
            <Text style={[styles.chipText, selectedTopics.includes(t) && styles.chipTextActive]}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>,
    // Step 3: Boundary Assessment
    <View key="3">
      <Text style={styles.stepTitle}>Boundary Check</Text>
      <Text style={styles.stepSub}>Help us understand your comfort zones</Text>
      {BOUNDARY_QUESTIONS.map((q, i) => (
        <TouchableOpacity key={i} testID={`boundary-${i}`} style={styles.boundaryRow} onPress={() => toggleBoundary(i)}>
          <View style={[styles.checkbox, boundaryAnswers[i] === 1 && styles.checkboxActive]}>
            {boundaryAnswers[i] === 1 && <Ionicons name="checkmark" size={16} color="#fff" />}
          </View>
          <Text style={styles.boundaryText}>{q}</Text>
        </TouchableOpacity>
      ))}
    </View>,
  ];

  return (
    <SafeAreaView style={styles.container} testID="listener-onboarding-screen">
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.progressRow}>
          {[0, 1, 2, 3].map(i => (
            <View key={i} style={[styles.progressDot, step >= i && styles.progressDotActive]} />
          ))}
        </View>
        {steps[step]}
        <View style={styles.btnRow}>
          {step > 0 && (
            <TouchableOpacity testID="listener-onboard-back" style={styles.outlineBtn} onPress={() => setStep(step - 1)}>
              <Text style={styles.outlineBtnText}>Back</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            testID="listener-onboard-next"
            style={[styles.primaryBtn, { flex: step > 0 ? 1 : undefined }]}
            onPress={() => step < 3 ? setStep(step + 1) : submit()}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="#fff" /> : (
              <Text style={styles.btnText}>{step < 3 ? 'Next' : 'Start Listening'}</Text>
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
  progressDot: { width: 24, height: 4, borderRadius: 2, backgroundColor: '#E2E8F0' },
  progressDotActive: { backgroundColor: '#A2E3C4', width: 40 },
  stepTitle: { fontSize: 24, fontWeight: '700', color: '#2D3748', marginBottom: 6 },
  stepSub: { fontSize: 14, color: '#718096', marginBottom: 28 },
  label: { fontSize: 13, fontWeight: '600', color: '#4A5568', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: { backgroundColor: '#fff', borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, borderWidth: 1, borderColor: '#E2E8F0', color: '#2D3748', marginBottom: 20 },
  avatarGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  avatarItem: { width: 72, height: 72, borderRadius: 20, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#E2E8F0' },
  avatarCircle: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  avatarEmoji: { fontSize: 24 },
  avatarCheck: { position: 'absolute', bottom: -2, right: -2 },
  chipGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, backgroundColor: '#fff', borderWidth: 1.5, borderColor: '#E2E8F0' },
  chipActive: { backgroundColor: '#FF8FA3', borderColor: '#FF8FA3' },
  chipActiveGreen: { backgroundColor: '#A2E3C4', borderColor: '#A2E3C4' },
  chipActiveYellow: { backgroundColor: '#F6E05E', borderColor: '#F6E05E' },
  chipText: { fontSize: 14, fontWeight: '500', color: '#4A5568' },
  chipTextActive: { color: '#fff' },
  boundaryRow: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  checkbox: { width: 24, height: 24, borderRadius: 6, borderWidth: 2, borderColor: '#E2E8F0', alignItems: 'center', justifyContent: 'center' },
  checkboxActive: { backgroundColor: '#A2E3C4', borderColor: '#A2E3C4' },
  boundaryText: { fontSize: 14, color: '#4A5568', flex: 1 },
  btnRow: { flexDirection: 'row', gap: 12, marginTop: 40 },
  outlineBtn: { paddingVertical: 14, paddingHorizontal: 24, borderRadius: 24, borderWidth: 2, borderColor: '#E2E8F0' },
  outlineBtnText: { fontSize: 15, fontWeight: '600', color: '#718096' },
  primaryBtn: { backgroundColor: '#A2E3C4', paddingVertical: 16, paddingHorizontal: 32, borderRadius: 28, alignItems: 'center', flex: 1 },
  btnText: { fontSize: 16, fontWeight: '700', color: '#1A4D2E' },
});
