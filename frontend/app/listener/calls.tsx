import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

export default function ListenerCalls() {
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

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#A2E3C4" /></View></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container} testID="listener-calls-screen">
      <Text style={styles.title}>Call History</Text>
      <FlatList
        data={calls}
        keyExtractor={item => item.id}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
        renderItem={({ item }) => (
          <View style={styles.callRow} testID={`listener-call-${item.id}`}>
            <View style={[styles.callIcon, item.call_type === 'video' ? styles.videoIcon : styles.voiceIcon]}>
              <Ionicons name={item.call_type === 'video' ? 'videocam' : 'call'} size={18} color={item.call_type === 'video' ? '#BB8FCE' : '#A2E3C4'} />
            </View>
            <View style={styles.callInfo}>
              <Text style={styles.callType}>{item.call_type === 'video' ? 'Video Call' : 'Voice Call'}</Text>
              <Text style={styles.callDuration}>{Math.floor(item.duration_seconds / 60)}m {item.duration_seconds % 60}s</Text>
              <Text style={styles.callDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
            </View>
            <Text style={styles.earningText}>
              +₹{Math.round((item.duration_seconds / 60) * (item.call_type === 'video' ? 5 : 3))}
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="call-outline" size={48} color="#E2E8F0" />
            <Text style={styles.emptyText}>No calls yet</Text>
            <Text style={styles.emptySubText}>Go online to start receiving calls</Text>
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
  voiceIcon: { backgroundColor: '#E0F0E3' },
  videoIcon: { backgroundColor: '#F3E8FF' },
  callInfo: { flex: 1, marginLeft: 12 },
  callType: { fontSize: 14, fontWeight: '600', color: '#2D3748' },
  callDuration: { fontSize: 12, color: '#718096', marginTop: 2 },
  callDate: { fontSize: 11, color: '#A0AEC0', marginTop: 2 },
  earningText: { fontSize: 14, fontWeight: '700', color: '#48BB78' },
  emptyState: { alignItems: 'center', paddingTop: 80 },
  emptyText: { fontSize: 16, fontWeight: '600', color: '#718096', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#A0AEC0', marginTop: 4 },
});
