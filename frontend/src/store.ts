import AsyncStorage from '@react-native-async-storage/async-storage';

export type UserRole = 'seeker' | 'listener' | 'admin';

export interface User {
  id: string;
  phone: string;
  role: UserRole;
  onboarded: boolean;
  name?: string;
}

export interface Listener {
  user_id: string;
  name: string;
  age: number;
  languages: string[];
  avatar_id: string;
  style_tags: string[];
  topic_tags: string[];
  is_online: boolean;
  in_call?: boolean;
  tier: string;
  total_calls: number;
  total_minutes: number;
  avg_rating: number;
}

export interface Call {
  id: string;
  seeker_id: string;
  listener_id: string;
  call_type: string;
  rate_per_min: number;
  is_first_call: boolean;
  status: string;
  started_at: string;
  ended_at?: string;
  duration_seconds: number;
  cost: number;
}

export const AVATAR_COLORS: Record<string, { bg: string; accent: string; emoji: string }> = {
  avatar_1: { bg: '#FFE0E6', accent: '#FF8FA3', emoji: '👩' },
  avatar_2: { bg: '#E0F0E3', accent: '#A2E3C4', emoji: '👩‍🦰' },
  avatar_3: { bg: '#FFF3CD', accent: '#F6E05E', emoji: '👩‍🎤' },
  avatar_4: { bg: '#E8DAEF', accent: '#BB8FCE', emoji: '👩‍🎨' },
  avatar_5: { bg: '#D6EAF8', accent: '#85C1E9', emoji: '👩‍💼' },
  avatar_6: { bg: '#FDEBD0', accent: '#F0B27A', emoji: '👩‍🔬' },
  avatar_7: { bg: '#D5F5E3', accent: '#82E0AA', emoji: '👩‍🏫' },
  avatar_8: { bg: '#FADBD8', accent: '#F1948A', emoji: '👩‍⚕️' },
};

export const LANGUAGES = ['Hindi', 'English', 'Tamil', 'Telugu', 'Bengali', 'Marathi', 'Kannada', 'Gujarati'];
export const INTENT_TAGS = ['Just Talk', 'Career Advice', 'Stress Relief', 'Fun Chat', 'Motivation', 'Loneliness', 'Relationship Talk', 'Life Guidance'];
export const STYLE_TAGS = ['Friendly', 'Calm', 'Funny', 'Caring', 'Motivating', 'Spiritual'];
export const TOPIC_TAGS = ['Life', 'Career', 'Relationships', 'Stress', 'Fun Chat', 'Movies', 'Music', 'Travel', 'Health', 'Study'];

export const saveUser = async (user: User) => {
  await AsyncStorage.setItem('user', JSON.stringify(user));
};

export const getUser = async (): Promise<User | null> => {
  const s = await AsyncStorage.getItem('user');
  return s ? JSON.parse(s) : null;
};

export const clearUser = async () => {
  await AsyncStorage.multiRemove(['user', 'auth_token']);
};
