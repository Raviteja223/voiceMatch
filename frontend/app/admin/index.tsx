import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity, FlatList,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<any>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'stats' | 'reports'>('stats');

  useEffect(() => {
    (async () => {
      try {
        const [dashRes, modRes] = await Promise.all([
          api.get('/admin/dashboard'),
          api.get('/admin/moderation-queue'),
        ]);
        setStats(dashRes);
        setReports(modRes.reports || []);
      } catch (e) {}
      setLoading(false);
    })();
  }, []);

  if (loading) return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#BB8FCE" /></View></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container} testID="admin-dashboard-screen">
      <View style={styles.header}>
        <TouchableOpacity testID="admin-back-btn" onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#2D3748" />
        </TouchableOpacity>
        <Text style={styles.title}>Admin Panel</Text>
      </View>

      <View style={styles.tabRow}>
        <TouchableOpacity testID="tab-stats" style={[styles.tab, tab === 'stats' && styles.tabActive]} onPress={() => setTab('stats')}>
          <Text style={[styles.tabText, tab === 'stats' && styles.tabTextActive]}>Dashboard</Text>
        </TouchableOpacity>
        <TouchableOpacity testID="tab-reports" style={[styles.tab, tab === 'reports' && styles.tabActive]} onPress={() => setTab('reports')}>
          <Text style={[styles.tabText, tab === 'reports' && styles.tabTextActive]}>Moderation ({reports.length})</Text>
        </TouchableOpacity>
      </View>

      {tab === 'stats' && stats && (
        <ScrollView contentContainerStyle={styles.statsScroll}>
          <View style={styles.statsGrid}>
            <StatCard icon="people" color="#FF8FA3" label="Total Users" value={stats.total_users} />
            <StatCard icon="person" color="#85C1E9" label="Seekers" value={stats.total_seekers} />
            <StatCard icon="headset" color="#A2E3C4" label="Listeners" value={stats.total_listeners} />
            <StatCard icon="radio" color="#48BB78" label="Online Now" value={stats.online_listeners} />
            <StatCard icon="call" color="#F6E05E" label="Total Calls" value={stats.total_calls} />
            <StatCard icon="pulse" color="#FF8FA3" label="Active Calls" value={stats.active_calls} />
            <StatCard icon="cash" color="#A2E3C4" label="Revenue" value={`₹${Math.round(stats.revenue)}`} />
            <StatCard icon="flag" color="#F56565" label="Reports" value={stats.total_reports} />
          </View>

          <View style={styles.metricsCard}>
            <Text style={styles.metricsTitle}>Key Metrics</Text>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Report Rate Target</Text>
              <Text style={styles.metricValue}>&lt;4%</Text>
            </View>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Avg Call Duration Target</Text>
              <Text style={styles.metricValue}>8-12 min</Text>
            </View>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Repeat Rate Target</Text>
              <Text style={styles.metricValue}>&gt;35%</Text>
            </View>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Listener Churn Target</Text>
              <Text style={styles.metricValue}>&lt;20% monthly</Text>
            </View>
          </View>
        </ScrollView>
      )}

      {tab === 'reports' && (
        <FlatList
          data={reports}
          keyExtractor={item => item.id}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
          renderItem={({ item }) => (
            <View style={styles.reportCard} testID={`report-${item.id}`}>
              <View style={styles.reportHeader}>
                <Ionicons name="flag" size={18} color="#F56565" />
                <Text style={styles.reportReason}>{item.reason}</Text>
                <View style={styles.pendingBadge}><Text style={styles.pendingText}>{item.status}</Text></View>
              </View>
              {item.details && <Text style={styles.reportDetails}>{item.details}</Text>}
              <Text style={styles.reportDate}>{new Date(item.created_at).toLocaleString()}</Text>
              <View style={styles.reportActions}>
                <TouchableOpacity style={styles.warnBtn}><Text style={styles.warnText}>Warn</Text></TouchableOpacity>
                <TouchableOpacity style={styles.suspendBtn}><Text style={styles.suspendText}>Suspend</Text></TouchableOpacity>
                <TouchableOpacity style={styles.dismissBtn}><Text style={styles.dismissText}>Dismiss</Text></TouchableOpacity>
              </View>
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Ionicons name="shield-checkmark" size={48} color="#A2E3C4" />
              <Text style={styles.emptyText}>No pending reports</Text>
              <Text style={styles.emptySubText}>All clear!</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

function StatCard({ icon, color, label, value }: { icon: string; color: string; label: string; value: any }) {
  return (
    <View style={styles.statCard}>
      <Ionicons name={icon as any} size={22} color={color} />
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 8, gap: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  tabRow: { flexDirection: 'row', paddingHorizontal: 20, marginBottom: 16, gap: 10 },
  tab: { flex: 1, paddingVertical: 10, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', borderWidth: 1, borderColor: '#E2E8F0' },
  tabActive: { backgroundColor: '#BB8FCE', borderColor: '#BB8FCE' },
  tabText: { fontSize: 13, fontWeight: '600', color: '#718096' },
  tabTextActive: { color: '#fff' },
  statsScroll: { paddingHorizontal: 20, paddingBottom: 20 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  statCard: { width: '48%', backgroundColor: '#fff', borderRadius: 14, padding: 16, alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  statValue: { fontSize: 22, fontWeight: '800', color: '#2D3748', marginTop: 8 },
  statLabel: { fontSize: 11, color: '#A0AEC0', fontWeight: '500', marginTop: 2 },
  metricsCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginTop: 16 },
  metricsTitle: { fontSize: 15, fontWeight: '700', color: '#2D3748', marginBottom: 12 },
  metricRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  metricLabel: { fontSize: 13, color: '#718096' },
  metricValue: { fontSize: 13, fontWeight: '700', color: '#2D3748' },
  reportCard: { backgroundColor: '#fff', borderRadius: 14, padding: 14, marginBottom: 10, borderLeftWidth: 3, borderLeftColor: '#F56565' },
  reportHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  reportReason: { flex: 1, fontSize: 14, fontWeight: '600', color: '#2D3748' },
  pendingBadge: { backgroundColor: '#FFF5F5', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  pendingText: { fontSize: 10, fontWeight: '700', color: '#F56565', textTransform: 'uppercase' },
  reportDetails: { fontSize: 12, color: '#718096', marginTop: 6 },
  reportDate: { fontSize: 11, color: '#A0AEC0', marginTop: 6 },
  reportActions: { flexDirection: 'row', gap: 8, marginTop: 10 },
  warnBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, backgroundColor: '#FFF5F5' },
  warnText: { fontSize: 11, fontWeight: '600', color: '#ED8936' },
  suspendBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, backgroundColor: '#FFF5F5' },
  suspendText: { fontSize: 11, fontWeight: '600', color: '#F56565' },
  dismissBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, backgroundColor: '#F0FFF4' },
  dismissText: { fontSize: 11, fontWeight: '600', color: '#48BB78' },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, fontWeight: '600', color: '#718096', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#A0AEC0', marginTop: 4 },
});
