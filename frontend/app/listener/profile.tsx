import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { clearUser } from '../../src/store';
import { setLanguage, getLanguage, SUPPORTED_LANGUAGES, t } from '../../src/i18n';

export default function ListenerProfile() {
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
    <SafeAreaView style={styles.container} testID="listener-profile-screen">
      <ScrollView>
        <Text style={styles.title}>{t('settings')}</Text>

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
                  {currentLang === lang.code && <Ionicons name="checkmark" size={18} color="#A2E3C4" />}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* KYC Section */}
        <View style={styles.card}>
          <TouchableOpacity testID="kyc-link" style={styles.menuItem} onPress={() => router.push('/listener/kyc')}>
            <Ionicons name="shield-checkmark" size={22} color="#A2E3C4" />
            <Text style={styles.menuText}>{t('kyc_verification')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <TouchableOpacity testID="listener-about-link" style={styles.menuItem}>
            <Ionicons name="information-circle" size={22} color="#85C1E9" />
            <Text style={styles.menuText}>{t('about')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
          <View style={styles.divider} />
          <TouchableOpacity testID="listener-support-link" style={styles.menuItem}>
            <Ionicons name="help-circle" size={22} color="#F6E05E" />
            <Text style={styles.menuText}>{t('support')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
          <View style={styles.divider} />
          <TouchableOpacity testID="listener-logout-btn" style={styles.menuItem} onPress={handleLogout}>
            <Ionicons name="log-out" size={22} color="#F56565" />
            <Text style={[styles.menuText, { color: '#F56565' }]}>{t('logout')}</Text>
            <Ionicons name="chevron-forward" size={18} color="#A0AEC0" />
          </TouchableOpacity>
        </View>

        <View style={styles.safetyCard}>
          <Ionicons name="shield-checkmark" size={18} color="#A2E3C4" />
          <Text style={styles.safetyText}>All calls are encrypted and recorded for safety (15-day retention)</Text>
        </View>

        <Text style={styles.version}>VoiceMatch v1.1.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0', paddingHorizontal: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748', marginTop: 8, marginBottom: 24 },
  card: { backgroundColor: '#fff', borderRadius: 18, padding: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  menuItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 16, gap: 12 },
  menuText: { flex: 1, fontSize: 15, fontWeight: '500', color: '#2D3748' },
  divider: { height: 1, backgroundColor: '#F0F0F0', marginHorizontal: 16 },
});
