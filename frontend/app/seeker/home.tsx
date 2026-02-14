import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, FlatList,
  ActivityIndicator, RefreshControl, Animated, Alert, Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { AVATAR_COLORS, Listener } from '../../src/store';

const { width } = Dimensions.get('window');

export default function SeekerHome() {
  const router = useRouter();
  const [listeners, setListeners] = useState<Listener[]>([]);
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [matchLoading, setMatchLoading] = useState(false);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.1, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [listenersRes, walletRes] = await Promise.all([
        api.get('/listeners/online'),
        api.get('/wallet/balance'),
      ]);
      setListeners(listenersRes.listeners || []);
      setBalance(walletRes.balance || 0);
    } catch (e) {
      console.log('Load error:', e);
    }
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleTalkNow = async () => {
    if (balance < 5) return Alert.alert('Low Balance', 'Please recharge to start a call', [{ text: 'Recharge', onPress: () => router.push('/seeker/wallet') }, { text: 'Cancel' }]);
    setMatchLoading(true);
    try {
      const res = await api.post('/match/talk-now');
      if (res.success && res.listener) {
        router.push({ pathname: '/call', params: { listenerId: res.listener.user_id, listenerName: res.listener.name, listenerAvatar: res.listener.avatar_id, callType: 'voice' } });
      }
    } catch (e: any) {
      Alert.alert('Matching', e.message || 'No listeners available right now');
    }
    setMatchLoading(false);
  };

  const handleSelectListener = (listener: Listener) => {
    if (balance < 5) return Alert.alert('Low Balance', 'Please recharge to start a call', [{ text: 'Recharge', onPress: () => router.push('/seeker/wallet') }, { text: 'Cancel' }]);
    if (listener.in_call) return Alert.alert('Busy', 'This listener is currently in a call');
    router.push({ pathname: '/call', params: { listenerId: listener.user_id, listenerName: listener.name, listenerAvatar: listener.avatar_id, callType: 'voice' } });
  };

  const renderListener = ({ item }: { item: Listener }) => {
    const colors = AVATAR_COLORS[item.avatar_id] || AVATAR_COLORS.avatar_1;
    return (
      <TouchableOpacity
        testID={`listener-card-${item.user_id}`}
        style={styles.listenerCard}
        onPress={() => handleSelectListener(item)}
        activeOpacity={0.85}
      >
        <View style={[styles.avatarCircle, { backgroundColor: colors.bg }]}>
          <Text style={styles.avatarEmoji}>{colors.emoji}</Text>
          <View style={[styles.onlineDot, item.in_call && styles.busyDot]} />
        </View>
        <View style={styles.listenerInfo}>
          <View style={styles.nameRow}>
            <Text style={styles.listenerName}>{item.name}</Text>
            <Ionicons name="shield-checkmark" size={14} color="#A2E3C4" />
            {item.tier === 'elite' && <View style={styles.eliteBadge}><Text style={styles.eliteBadgeText}>Elite</Text></View>}
            {item.tier === 'trusted' && <View style={styles.trustedBadge}><Text style={styles.trustedBadgeText}>Trusted</Text></View>}
          </View>
          <View style={styles.tagRow}>
            {item.languages?.slice(0, 2).map(l => (
              <View key={l} style={styles.miniTag}><Text style={styles.miniTagText}>{l}</Text></View>
            ))}
          </View>
          <View style={styles.tagRow}>
            {item.style_tags?.slice(0, 2).map(t => (
              <View key={t} style={styles.styleTag}><Text style={styles.styleTagText}>{t}</Text></View>
            ))}
          </View>
        </View>
        <View style={styles.ratingCol}>
          <View style={styles.ratingRow}>
            <Ionicons name="star" size={12} color="#F6E05E" />
            <Text style={styles.ratingText}>{item.avg_rating?.toFixed(1)}</Text>
          </View>
          <Text style={styles.callCount}>{item.total_calls} calls</Text>
          <Ionicons name="call" size={18} color="#FF8FA3" style={{ marginTop: 6 }} />
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}><View style={styles.centerLoader}><ActivityIndicator size="large" color="#FF8FA3" /></View></SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="seeker-home-screen">
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Hello there!</Text>
          <Text style={styles.headerTitle}>Find a Listener</Text>
        </View>
        <TouchableOpacity testID="wallet-btn" style={styles.walletPill} onPress={() => router.push('/seeker/wallet')}>
          <Ionicons name="wallet" size={16} color="#FF8FA3" />
          <Text style={styles.walletText}>₹{balance}</Text>
        </TouchableOpacity>
      </View>

      {/* Talk Now Button */}
      <View style={styles.talkNowSection}>
        <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
          <TouchableOpacity
            testID="talk-now-btn"
            style={styles.talkNowBtn}
            onPress={handleTalkNow}
            disabled={matchLoading}
            activeOpacity={0.85}
          >
            {matchLoading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Ionicons name="mic" size={28} color="#fff" />
                <Text style={styles.talkNowText}>Talk Now</Text>
              </>
            )}
          </TouchableOpacity>
        </Animated.View>
        <Text style={styles.talkNowSub}>Auto-match with a listener</Text>
      </View>

      {/* Online Listeners */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Online Listeners</Text>
        <View style={styles.countBadge}>
          <View style={styles.greenDot} />
          <Text style={styles.countText}>{listeners.length} online</Text>
        </View>
      </View>

      <FlatList
        testID="listeners-list"
        data={listeners}
        renderItem={renderListener}
        keyExtractor={item => item.user_id}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} tintColor="#FF8FA3" />}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="moon" size={48} color="#E2E8F0" />
            <Text style={styles.emptyText}>No listeners online right now</Text>
            <Text style={styles.emptySubText}>Pull to refresh or try again shortly</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  centerLoader: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 4 },
  greeting: { fontSize: 13, color: '#718096', fontWeight: '500' },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  walletPill: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#FFF0F3', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20 },
  walletText: { fontSize: 14, fontWeight: '700', color: '#FF8FA3' },
  talkNowSection: { alignItems: 'center', paddingVertical: 16 },
  talkNowBtn: {
    width: 100, height: 100, borderRadius: 50, backgroundColor: '#FF8FA3',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.4, shadowRadius: 16, elevation: 8,
  },
  talkNowText: { fontSize: 12, fontWeight: '700', color: '#fff', marginTop: 2 },
  talkNowSub: { fontSize: 12, color: '#A0AEC0', marginTop: 8 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, marginBottom: 8 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#2D3748' },
  countBadge: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  greenDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#48BB78' },
  countText: { fontSize: 12, color: '#718096', fontWeight: '500' },
  listContent: { paddingHorizontal: 16, paddingBottom: 20 },
  listenerCard: {
    flexDirection: 'row', alignItems: 'center', padding: 14, backgroundColor: '#fff',
    borderRadius: 18, marginBottom: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  avatarCircle: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  avatarEmoji: { fontSize: 26 },
  onlineDot: { position: 'absolute', bottom: 0, right: 0, width: 14, height: 14, borderRadius: 7, backgroundColor: '#48BB78', borderWidth: 2, borderColor: '#fff' },
  busyDot: { backgroundColor: '#F6E05E' },
  listenerInfo: { flex: 1, marginLeft: 12 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  listenerName: { fontSize: 15, fontWeight: '700', color: '#2D3748' },
  eliteBadge: { backgroundColor: '#F6E05E', paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6 },
  eliteBadgeText: { fontSize: 9, fontWeight: '700', color: '#744210' },
  trustedBadge: { backgroundColor: '#D6F5E3', paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6 },
  trustedBadgeText: { fontSize: 9, fontWeight: '700', color: '#1A4D2E' },
  tagRow: { flexDirection: 'row', gap: 4, marginTop: 4 },
  miniTag: { backgroundColor: '#EBF4FF', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  miniTagText: { fontSize: 10, color: '#4A5568', fontWeight: '500' },
  styleTag: { backgroundColor: '#FFF0F3', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  styleTagText: { fontSize: 10, color: '#FF8FA3', fontWeight: '500' },
  ratingCol: { alignItems: 'flex-end' },
  ratingRow: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  ratingText: { fontSize: 12, fontWeight: '700', color: '#2D3748' },
  callCount: { fontSize: 10, color: '#A0AEC0', marginTop: 2 },
  emptyState: { alignItems: 'center', justifyContent: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, fontWeight: '600', color: '#718096', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#A0AEC0', marginTop: 4 },
});
