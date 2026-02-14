import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';
import { AVATAR_COLORS } from '../../src/store';

export default function HistoryScreen() {
  const [calls, setCalls] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/calls/history');
        setCalls(res.calls || []);
      } catch (e) {}
      setLoading(false);
    })();
  }, []);

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#FF8FA3" /></View></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container} testID="history-screen">
      <Text style={styles.title}>Call History</Text>
      <FlatList
        data={calls}
        keyExtractor={item => item.id}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
        renderItem={({ item }) => (
          <View style={styles.callRow} testID={`call-${item.id}`}>
            <View style={[styles.callIcon, item.call_type === 'video' ? styles.videoIcon : styles.voiceIcon]}>
              <Ionicons name={item.call_type === 'video' ? 'videocam' : 'call'} size={18} color={item.call_type === 'video' ? '#BB8FCE' : '#FF8FA3'} />
            </View>
            <View style={styles.callInfo}>
              <Text style={styles.callType}>{item.call_type === 'video' ? 'Video Call' : 'Voice Call'}</Text>
              <Text style={styles.callDuration}>{Math.floor(item.duration_seconds / 60)}m {item.duration_seconds % 60}s</Text>
              <Text style={styles.callDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
            </View>
            <View style={styles.callCost}>
              <Text style={styles.costText}>-₹{Math.round(item.cost)}</Text>
              {item.is_first_call && <View style={styles.discountBadge}><Text style={styles.discountText}>1st Call</Text></View>}
            </View>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="call-outline" size={48} color="#E2E8F0" />
            <Text style={styles.emptyText}>No calls yet</Text>
            <Text style={styles.emptySubText}>Start a conversation from the Home tab</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748', paddingHorizontal: 20, marginTop: 8, marginBottom: 16 },
  callRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  callIcon: { width: 42, height: 42, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  voiceIcon: { backgroundColor: '#FFF0F3' },
  videoIcon: { backgroundColor: '#F3E8FF' },
  callInfo: { flex: 1, marginLeft: 12 },
  callType: { fontSize: 14, fontWeight: '600', color: '#2D3748' },
  callDuration: { fontSize: 12, color: '#718096', marginTop: 2 },
  callDate: { fontSize: 11, color: '#A0AEC0', marginTop: 2 },
  callCost: { alignItems: 'flex-end' },
  costText: { fontSize: 14, fontWeight: '700', color: '#F56565' },
  discountBadge: { backgroundColor: '#E6FFED', paddingHorizontal: 6, paddingVertical: 1, borderRadius: 4, marginTop: 4 },
  discountText: { fontSize: 9, fontWeight: '700', color: '#48BB78' },
  emptyState: { alignItems: 'center', paddingTop: 80 },
  emptyText: { fontSize: 16, fontWeight: '600', color: '#718096', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#A0AEC0', marginTop: 4 },
});
