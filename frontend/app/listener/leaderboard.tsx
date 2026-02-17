import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, FlatList,
  ActivityIndicator, RefreshControl, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import api from '../../src/api';

type Period = 'weekly' | 'monthly' | 'all_time';

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  name: string;
  avatar_id: string;
  is_online: boolean;
  period_earnings: number;
  period_minutes: number;
  period_calls: number;
  total_earnings: number;
  tier: string;
  average_rating: number;
}

interface LeaderboardData {
  period: string;
  leaderboard: LeaderboardEntry[];
  total_listeners: number;
  current_user: {
    rank: number | null;
    entry: LeaderboardEntry | null;
  };
}

const AVATAR_COLORS: Record<string, string> = {
  avatar_1: '#FF8FA3',
  avatar_2: '#A2E3C4',
  avatar_3: '#85C1E9',
  avatar_4: '#F6E05E',
  avatar_5: '#BB8FCE',
};

const TIER_BADGES: Record<string, { color: string; icon: string; label: string }> = {
  new: { color: '#A0AEC0', icon: 'star-outline', label: 'New' },
  trusted: { color: '#48BB78', icon: 'star-half', label: 'Trusted' },
  elite: { color: '#F6E05E', icon: 'star', label: 'Elite' },
  premium: { color: '#BB8FCE', icon: 'diamond', label: 'Premium' },
};

export default function LeaderboardScreen() {
  const router = useRouter();
  const [period, setPeriod] = useState<Period>('weekly');
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchLeaderboard = useCallback(async () => {
    try {
      const res = await api.get(`/listeners/leaderboard?period=${period}`);
      setData(res);
    } catch (e) {
      console.error('Failed to fetch leaderboard:', e);
    }
    setLoading(false);
    setRefreshing(false);
  }, [period]);

  useEffect(() => {
    setLoading(true);
    fetchLeaderboard();
  }, [period, fetchLeaderboard]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchLeaderboard();
  };

  const renderRankBadge = (rank: number) => {
    if (rank === 1) {
      return (
        <View style={[styles.rankBadge, { backgroundColor: '#FFD700' }]}>
          <Ionicons name="trophy" size={16} color="#fff" />
        </View>
      );
    }
    if (rank === 2) {
      return (
        <View style={[styles.rankBadge, { backgroundColor: '#C0C0C0' }]}>
          <Text style={styles.rankBadgeText}>2</Text>
        </View>
      );
    }
    if (rank === 3) {
      return (
        <View style={[styles.rankBadge, { backgroundColor: '#CD7F32' }]}>
          <Text style={styles.rankBadgeText}>3</Text>
        </View>
      );
    }
    return (
      <View style={[styles.rankBadge, { backgroundColor: '#E2E8F0' }]}>
        <Text style={[styles.rankBadgeText, { color: '#4A5568' }]}>{rank}</Text>
      </View>
    );
  };

  const renderItem = ({ item, index }: { item: LeaderboardEntry; index: number }) => {
    const isCurrentUser = data?.current_user?.entry?.user_id === item.user_id;
    const avatarColor = AVATAR_COLORS[item.avatar_id] || '#A2E3C4';
    const tier = TIER_BADGES[item.tier] || TIER_BADGES.new;
    
    return (
      <Animated.View style={[styles.listItem, isCurrentUser && styles.listItemHighlight]}>
        {/* Rank */}
        {renderRankBadge(item.rank)}
        
        {/* Avatar */}
        <View style={[styles.avatar, { backgroundColor: avatarColor }]}>
          <Text style={styles.avatarText}>{item.name.charAt(0).toUpperCase()}</Text>
          {item.is_online && <View style={styles.onlineIndicator} />}
        </View>
        
        {/* Info */}
        <View style={styles.itemInfo}>
          <View style={styles.nameRow}>
            <Text style={styles.itemName} numberOfLines={1}>{item.name}</Text>
            {isCurrentUser && <Text style={styles.youBadge}>You</Text>}
          </View>
          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Ionicons name="call" size={12} color="#718096" />
              <Text style={styles.statText}>{item.period_calls}</Text>
            </View>
            <View style={styles.statItem}>
              <Ionicons name="time" size={12} color="#718096" />
              <Text style={styles.statText}>{Math.round(item.period_minutes)}m</Text>
            </View>
            {item.average_rating > 0 && (
              <View style={styles.statItem}>
                <Ionicons name="star" size={12} color="#F6E05E" />
                <Text style={styles.statText}>{item.average_rating.toFixed(1)}</Text>
              </View>
            )}
          </View>
        </View>
        
        {/* Earnings */}
        <View style={styles.earningsContainer}>
          <Text style={styles.earningsAmount}>₹{item.period_earnings.toFixed(0)}</Text>
          <View style={[styles.tierBadge, { backgroundColor: tier.color + '20' }]}>
            <Ionicons name={tier.icon as any} size={10} color={tier.color} />
          </View>
        </View>
      </Animated.View>
    );
  };

  const renderHeader = () => (
    <View style={styles.headerContent}>
      {/* Period Tabs */}
      <View style={styles.periodTabs}>
        {(['weekly', 'monthly', 'all_time'] as Period[]).map((p) => (
          <TouchableOpacity
            key={p}
            style={[styles.periodTab, period === p && styles.periodTabActive]}
            onPress={() => setPeriod(p)}
          >
            <Text style={[styles.periodTabText, period === p && styles.periodTabTextActive]}>
              {p === 'weekly' ? 'This Week' : p === 'monthly' ? 'This Month' : 'All Time'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      
      {/* Stats Summary */}
      {data?.current_user?.entry && (
        <View style={styles.myRankCard}>
          <View style={styles.myRankLeft}>
            <Text style={styles.myRankLabel}>Your Rank</Text>
            <View style={styles.myRankValue}>
              <Text style={styles.myRankNumber}>#{data.current_user.rank}</Text>
              <Text style={styles.myRankTotal}>of {data.total_listeners}</Text>
            </View>
          </View>
          <View style={styles.myRankRight}>
            <Text style={styles.myEarningsLabel}>Your Earnings</Text>
            <Text style={styles.myEarningsValue}>₹{data.current_user.entry.period_earnings.toFixed(0)}</Text>
          </View>
        </View>
      )}
      
      {/* Top 3 Podium */}
      {data && data.leaderboard.length >= 3 && (
        <View style={styles.podium}>
          {/* 2nd Place */}
          <View style={styles.podiumSpot}>
            <View style={[styles.podiumAvatar, styles.podiumAvatar2, { backgroundColor: AVATAR_COLORS[data.leaderboard[1]?.avatar_id] || '#A2E3C4' }]}>
              <Text style={styles.podiumAvatarText}>{data.leaderboard[1]?.name?.charAt(0) || '?'}</Text>
            </View>
            <View style={[styles.podiumBar, styles.podiumBar2]}>
              <Ionicons name="medal" size={18} color="#C0C0C0" />
            </View>
            <Text style={styles.podiumName} numberOfLines={1}>{data.leaderboard[1]?.name || 'N/A'}</Text>
            <Text style={styles.podiumEarnings}>₹{data.leaderboard[1]?.period_earnings?.toFixed(0) || 0}</Text>
          </View>
          
          {/* 1st Place */}
          <View style={styles.podiumSpot}>
            <View style={styles.crownContainer}>
              <Ionicons name="trophy" size={24} color="#FFD700" />
            </View>
            <View style={[styles.podiumAvatar, styles.podiumAvatar1, { backgroundColor: AVATAR_COLORS[data.leaderboard[0]?.avatar_id] || '#FF8FA3' }]}>
              <Text style={[styles.podiumAvatarText, { fontSize: 20 }]}>{data.leaderboard[0]?.name?.charAt(0) || '?'}</Text>
            </View>
            <View style={[styles.podiumBar, styles.podiumBar1]}>
              <Ionicons name="medal" size={22} color="#FFD700" />
            </View>
            <Text style={styles.podiumName} numberOfLines={1}>{data.leaderboard[0]?.name || 'N/A'}</Text>
            <Text style={styles.podiumEarnings}>₹{data.leaderboard[0]?.period_earnings?.toFixed(0) || 0}</Text>
          </View>
          
          {/* 3rd Place */}
          <View style={styles.podiumSpot}>
            <View style={[styles.podiumAvatar, styles.podiumAvatar3, { backgroundColor: AVATAR_COLORS[data.leaderboard[2]?.avatar_id] || '#85C1E9' }]}>
              <Text style={styles.podiumAvatarText}>{data.leaderboard[2]?.name?.charAt(0) || '?'}</Text>
            </View>
            <View style={[styles.podiumBar, styles.podiumBar3]}>
              <Ionicons name="medal" size={16} color="#CD7F32" />
            </View>
            <Text style={styles.podiumName} numberOfLines={1}>{data.leaderboard[2]?.name || 'N/A'}</Text>
            <Text style={styles.podiumEarnings}>₹{data.leaderboard[2]?.period_earnings?.toFixed(0) || 0}</Text>
          </View>
        </View>
      )}
      
      <Text style={styles.listTitle}>Full Rankings</Text>
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#2D3748" />
          </TouchableOpacity>
          <Text style={styles.title}>Leaderboard</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#A2E3C4" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="leaderboard-screen">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#2D3748" />
        </TouchableOpacity>
        <Text style={styles.title}>Leaderboard</Text>
        <TouchableOpacity onPress={onRefresh} style={styles.refreshBtn}>
          <Ionicons name="refresh" size={20} color="#718096" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={data?.leaderboard.slice(3) || []} // Skip top 3 shown in podium
        renderItem={renderItem}
        keyExtractor={(item) => item.user_id}
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="podium" size={48} color="#E2E8F0" />
            <Text style={styles.emptyText}>No rankings yet</Text>
            <Text style={styles.emptySubtext}>Start taking calls to climb the leaderboard!</Text>
          </View>
        }
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#A2E3C4" />
        }
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 12, gap: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  refreshBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', marginLeft: 'auto' },
  title: { fontSize: 20, fontWeight: '700', color: '#2D3748' },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  
  // Header Content
  headerContent: { paddingHorizontal: 20 },
  periodTabs: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 14, padding: 4, marginBottom: 16 },
  periodTab: { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  periodTabActive: { backgroundColor: '#A2E3C4' },
  periodTabText: { fontSize: 13, fontWeight: '600', color: '#718096' },
  periodTabTextActive: { color: '#1A4D2E' },
  
  // My Rank Card
  myRankCard: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 18, padding: 16, marginBottom: 20 },
  myRankLeft: { flex: 1 },
  myRankLabel: { fontSize: 12, color: '#718096', fontWeight: '500' },
  myRankValue: { flexDirection: 'row', alignItems: 'baseline', gap: 4, marginTop: 4 },
  myRankNumber: { fontSize: 28, fontWeight: '700', color: '#2D3748' },
  myRankTotal: { fontSize: 13, color: '#A0AEC0' },
  myRankRight: { alignItems: 'flex-end' },
  myEarningsLabel: { fontSize: 12, color: '#718096', fontWeight: '500' },
  myEarningsValue: { fontSize: 24, fontWeight: '700', color: '#48BB78', marginTop: 4 },
  
  // Podium
  podium: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'center', marginBottom: 24, paddingHorizontal: 10 },
  podiumSpot: { alignItems: 'center', flex: 1 },
  crownContainer: { marginBottom: 4 },
  podiumAvatar: { borderRadius: 100, alignItems: 'center', justifyContent: 'center', marginBottom: -15, zIndex: 1, borderWidth: 3, borderColor: '#fff' },
  podiumAvatar1: { width: 60, height: 60 },
  podiumAvatar2: { width: 50, height: 50 },
  podiumAvatar3: { width: 46, height: 46 },
  podiumAvatarText: { fontSize: 18, fontWeight: '700', color: '#fff' },
  podiumBar: { alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 8, borderTopLeftRadius: 8, borderTopRightRadius: 8 },
  podiumBar1: { backgroundColor: '#FFD700', width: 80, height: 80 },
  podiumBar2: { backgroundColor: '#E8E8E8', width: 70, height: 60 },
  podiumBar3: { backgroundColor: '#F4D8C8', width: 65, height: 50 },
  podiumName: { fontSize: 12, fontWeight: '600', color: '#2D3748', marginTop: 8, width: 70, textAlign: 'center' },
  podiumEarnings: { fontSize: 13, fontWeight: '700', color: '#48BB78' },
  
  // List
  listTitle: { fontSize: 14, fontWeight: '600', color: '#4A5568', marginBottom: 12, marginTop: 4 },
  listContent: { paddingBottom: 40 },
  listItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', marginHorizontal: 20, marginBottom: 10, padding: 12, borderRadius: 14, gap: 12 },
  listItemHighlight: { backgroundColor: '#E6FFED', borderWidth: 1, borderColor: '#A2E3C4' },
  
  // Rank Badge
  rankBadge: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  rankBadgeText: { fontSize: 12, fontWeight: '700', color: '#fff' },
  
  // Avatar
  avatar: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', position: 'relative' },
  avatarText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  onlineIndicator: { position: 'absolute', bottom: 0, right: 0, width: 12, height: 12, borderRadius: 6, backgroundColor: '#48BB78', borderWidth: 2, borderColor: '#fff' },
  
  // Item Info
  itemInfo: { flex: 1 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  itemName: { fontSize: 14, fontWeight: '600', color: '#2D3748', maxWidth: 120 },
  youBadge: { backgroundColor: '#A2E3C4', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, fontSize: 10, fontWeight: '700', color: '#1A4D2E' },
  statsRow: { flexDirection: 'row', gap: 10, marginTop: 4 },
  statItem: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  statText: { fontSize: 11, color: '#718096' },
  
  // Earnings
  earningsContainer: { alignItems: 'flex-end' },
  earningsAmount: { fontSize: 16, fontWeight: '700', color: '#48BB78' },
  tierBadge: { marginTop: 4, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 8 },
  
  // Empty State
  emptyContainer: { alignItems: 'center', paddingTop: 40 },
  emptyText: { fontSize: 16, fontWeight: '600', color: '#4A5568', marginTop: 12 },
  emptySubtext: { fontSize: 13, color: '#A0AEC0', marginTop: 4 },
});
