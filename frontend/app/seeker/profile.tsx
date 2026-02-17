import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { clearUser } from '../../src/store';
import { setLanguage, getLanguage, SUPPORTED_LANGUAGES, t } from '../../src/i18n';

export default function SeekerProfile() {
  const router = useRouter();
  const [currentLang, setCurrentLang] = useState(getLanguage());
  const [showLangPicker, setShowLangPicker] = useState(false);

  const handleLogout = () => {
    Alert.alert(t('logout'), 'Are you sure you want to logout?', [
      { text: 'Cancel' },
      { text: t('logout'), style: 'destructive', onPress: async () => {
        await api.clearToken();
        await clearUser();
        router.replace('/');
      }},
    ]);
  };

  const handleLangChange = (code: string) => {
    setLanguage(code);
    setCurrentLang(code);
    setShowLangPicker(false);
  };

  const currentLangObj = SUPPORTED_LANGUAGES.find(l => l.code === currentLang);

  return (
    <SafeAreaView style={styles.container} testID="seeker-profile-screen">
      <ScrollView>
        <Text style={styles.title}>{t('profile')}</Text>

        {/* Language Selector */}
        <View style={styles.card}>
          <TouchableOpacity testID="language-selector" style={styles.menuItem} onPress={() => setShowLangPicker(!showLangPicker)}>
            <Ionicons name="language" size={22} color="#85C1E9" />
            <Text style={styles.menuText}>Language</Text>
            <Text style={styles.langValue}>{currentLangObj?.native || 'English'}</Text>
            <Ionicons name={showLangPicker ? 'chevron-up' : 'chevron-down'} size={18} color="#A0AEC0" />
          </TouchableOpacity>
          {showLangPicker && (
            <View style={styles.langPicker}>
              {SUPPORTED_LANGUAGES.map(lang => (
                <TouchableOpacity
                  key={lang.code}
                  testID={`lang-option-${lang.code}`}
                  style={[styles.langOption, currentLang === lang.code && styles.langOptionActive]}
                  onPress={() => handleLangChange(lang.code)}
                >
                  <Text style={[styles.langOptionText, currentLang === lang.code && styles.langOptionTextActive]}>
                    {lang.native} ({lang.label})
                  </Text>
                  {currentLang === lang.code && <Ionicons name="checkmark" size={18} color="#FF8FA3" />}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        <View style={styles.card}>
          <TouchableOpacity testID="about-link" style={styles.menuItem}>
            <Ionicons name="information-circle" size={22} color="#85C1E9" />
            <Text style={styles.menuText}>{t('about')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
          <View style={styles.divider} />
          <TouchableOpacity testID="support-link" style={styles.menuItem}>
            <Ionicons name="help-circle" size={22} color="#F6E05E" />
            <Text style={styles.menuText}>{t('support')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
          <View style={styles.divider} />
          <TouchableOpacity testID="logout-btn" style={styles.menuItem} onPress={handleLogout}>
            <Ionicons name="log-out" size={22} color="#F56565" />
            <Text style={[styles.menuText, { color: '#F56565' }]}>{t('logout')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
        </View>

        <View style={styles.safetyCard}>
          <Ionicons name="shield-checkmark" size={18} color="#A2E3C4" />
          <Text style={styles.safetyText}>All calls are encrypted and recorded for safety (15-day retention)</Text>
        </View>

        <Text style={styles.version}>Konnectra v1.1.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0', paddingHorizontal: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748', marginTop: 8, marginBottom: 24 },
  card: { backgroundColor: '#fff', borderRadius: 18, padding: 4, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  menuItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 16, gap: 12 },
  menuText: { flex: 1, fontSize: 15, fontWeight: '500', color: '#2D3748' },
  langValue: { fontSize: 13, color: '#FF8FA3', fontWeight: '600' },
  divider: { height: 1, backgroundColor: '#F0F0F0', marginHorizontal: 16 },
  langPicker: { paddingHorizontal: 12, paddingBottom: 8 },
  langOption: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10 },
  langOptionActive: { backgroundColor: '#FFF0F3' },
  langOptionText: { fontSize: 14, color: '#4A5568' },
  langOptionTextActive: { color: '#FF8FA3', fontWeight: '600' },
  safetyCard: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E6FFED', borderRadius: 12, padding: 12, marginBottom: 16 },
  safetyText: { fontSize: 11, color: '#1A4D2E', flex: 1 },
  version: { textAlign: 'center', color: '#A0AEC0', fontSize: 12, marginTop: 8, marginBottom: 20 },
});
