import React, { createContext, useContext, useMemo, useState } from 'react';

export type AppLanguage = 'en' | 'hi' | 'ta' | 'te' | 'kn' | 'ml';

const translations: Record<AppLanguage, Record<string, string>> = {
  en: {
    welcome: 'Welcome',
    getStarted: 'Get Started',
    signInWithPhone: 'Sign in with your phone number',
    sendOtp: 'Send OTP',
    verifyContinue: 'Verify & Continue',
  },
  hi: {
    welcome: 'स्वागत है',
    getStarted: 'शुरू करें',
    signInWithPhone: 'अपने फोन नंबर से साइन इन करें',
    sendOtp: 'ओटीपी भेजें',
    verifyContinue: 'सत्यापित करें और जारी रखें',
  },
  ta: {
    welcome: 'வரவேற்கிறோம்',
    getStarted: 'தொடங்குங்கள்',
    signInWithPhone: 'உங்கள் தொலைபேசி எண்ணுடன் உள்நுழைக',
    sendOtp: 'OTP அனுப்பு',
    verifyContinue: 'சரிபார்த்து தொடரவும்',
  },
  te: {
    welcome: 'స్వాగతం',
    getStarted: 'ప్రారంభించండి',
    signInWithPhone: 'మీ ఫోన్ నంబర్‌తో సైన్ ఇన్ చేయండి',
    sendOtp: 'OTP పంపండి',
    verifyContinue: 'ధృవీకరించి కొనసాగించండి',
  },
  kn: {
    welcome: 'ಸ್ವಾಗತ',
    getStarted: 'ಪ್ರಾರಂಭಿಸಿ',
    signInWithPhone: 'ನಿಮ್ಮ ಫೋನ್ ಸಂಖ್ಯೆಯಿಂದ ಸೈನ್ ಇನ್ ಮಾಡಿ',
    sendOtp: 'OTP ಕಳುಹಿಸಿ',
    verifyContinue: 'ಪರಿಶೀಲಿಸಿ ಮುಂದುವರಿಸಿ',
  },
  ml: {
    welcome: 'സ്വാഗതം',
    getStarted: 'തുടങ്ങുക',
    signInWithPhone: 'നിങ്ങളുടെ ഫോൺ നമ്പർ ഉപയോഗിച്ച് സൈൻ ഇൻ ചെയ്യുക',
    sendOtp: 'OTP അയയ്ക്കുക',
    verifyContinue: 'സ്ഥിരീകരിച്ച് തുടരുക',
  },
};

const I18nContext = createContext<{
  language: AppLanguage;
  setLanguage: (lang: AppLanguage) => void;
  t: (key: string) => string;
}>({
  language: 'en',
  setLanguage: () => {},
  t: (key: string) => key,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<AppLanguage>('en');

  const value = useMemo(() => ({
    language,
    setLanguage,
    t: (key: string) => translations[language][key] || translations.en[key] || key,
  }), [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
