import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, FlatList,
  ActivityIndicator, Alert, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '../../src/api';

const PACKS = [
  { id: 'pack_99', amount: 99, credits: 99, popular: false, label: 'Starter' },
  { id: 'pack_299', amount: 299, credits: 299, popular: true, label: 'Popular' },
  { id: 'pack_699', amount: 699, credits: 699, popular: false, label: 'Best Value' },
];

export default function WalletScreen() {
  const [balance, setBalance] = useState(0);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [recharging, setRecharging] = useState('');

  const loadData = useCallback(async () => {
    try {
      const [walletRes, txnRes] = await Promise.all([
        api.get('/wallet/balance'),
        api.get('/wallet/transactions'),
      ]);
      setBalance(walletRes.balance || 0);
      setTransactions(txnRes.transactions || []);
    } catch (e) {}
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRecharge = async (packId: string) => {
    setRecharging(packId);
    try {
      const res = await api.post('/wallet/recharge', { pack_id: packId });
      setBalance(res.new_balance);
      Alert.alert('Success', `Recharged successfully! New balance: ₹${res.new_balance}`);
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setRecharging('');
  };

  if (loading) {
    return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color="#FF8FA3" /></View></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.container} testID="wallet-screen">
      <FlatList
        data={transactions}
        keyExtractor={item => item.id}
        refreshControl={<RefreshControl refreshing={false} onRefresh={loadData} tintColor="#FF8FA3" />}
        ListHeaderComponent={
          <>
            <Text style={styles.screenTitle}>Wallet</Text>
            <View style={styles.balanceCard}>
              <Text style={styles.balanceLabel}>Available Balance</Text>
              <Text style={styles.balanceAmount}>₹{Math.round(balance)}</Text>
              <Text style={styles.balanceCredits}>{Math.round(balance)} credits</Text>
              <View style={styles.rateInfo}>
                <View style={styles.rateItem}><Ionicons name="mic" size={14} color="#FF8FA3" /><Text style={styles.rateText}>Voice ₹5/min</Text></View>
                <View style={styles.rateDivider} />
                <View style={styles.rateItem}><Ionicons name="videocam" size={14} color="#BB8FCE" /><Text style={styles.rateText}>Video ₹8/min</Text></View>
              </View>
            </View>
            <Text style={styles.sectionTitle}>Recharge Packs</Text>
            <View style={styles.packsRow}>
              {PACKS.map(pack => (
                <TouchableOpacity
                  key={pack.id}
                  testID={`recharge-${pack.id}`}
                  style={[styles.packCard, pack.popular && styles.packCardPopular]}
                  onPress={() => handleRecharge(pack.id)}
                  disabled={!!recharging}
                >
                  {pack.popular && <View style={styles.popularBadge}><Text style={styles.popularText}>POPULAR</Text></View>}
                  <Text style={[styles.packLabel, pack.popular && styles.packLabelPopular]}>{pack.label}</Text>
                  <Text style={[styles.packAmount, pack.popular && styles.packAmountPopular]}>₹{pack.amount}</Text>
                  <Text style={[styles.packCredits, pack.popular && styles.packCreditsPopular]}>{pack.credits} credits</Text>
                  {recharging === pack.id && <ActivityIndicator size="small" color={pack.popular ? '#fff' : '#FF8FA3'} style={{ marginTop: 6 }} />}
                </TouchableOpacity>
              ))}
            </View>
            <Text style={styles.sectionTitle}>Transaction History</Text>
          </>
        }
        renderItem={({ item }) => (
          <View style={styles.txnRow} testID={`txn-${item.id}`}>
            <View style={[styles.txnIcon, item.type === 'credit' ? styles.txnCredit : styles.txnDebit]}>
              <Ionicons name={item.type === 'credit' ? 'arrow-down' : 'arrow-up'} size={16} color={item.type === 'credit' ? '#48BB78' : '#F56565'} />
            </View>
            <View style={styles.txnInfo}>
              <Text style={styles.txnDesc}>{item.description}</Text>
              <Text style={styles.txnDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
            </View>
            <Text style={[styles.txnAmount, item.type === 'credit' ? styles.txnAmountCredit : styles.txnAmountDebit]}>
              {item.type === 'credit' ? '+' : '-'}₹{Math.round(item.amount)}
            </Text>
          </View>
        )}
        ListEmptyComponent={<Text style={styles.emptyText}>No transactions yet</Text>}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  screenTitle: { fontSize: 22, fontWeight: '700', color: '#2D3748', marginTop: 8, marginBottom: 16 },
  balanceCard: { backgroundColor: '#FF8FA3', borderRadius: 20, padding: 24, alignItems: 'center', marginBottom: 24, shadowColor: '#FF8FA3', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.3, shadowRadius: 16, elevation: 6 },
  balanceLabel: { fontSize: 13, color: '#FFE0E6', fontWeight: '500' },
  balanceAmount: { fontSize: 40, fontWeight: '800', color: '#fff', marginTop: 4 },
  balanceCredits: { fontSize: 14, color: '#FFE0E6', marginTop: 2 },
  rateInfo: { flexDirection: 'row', alignItems: 'center', marginTop: 16, backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12 },
  rateItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  rateDivider: { width: 1, height: 16, backgroundColor: 'rgba(255,255,255,0.3)', marginHorizontal: 12 },
  rateText: { fontSize: 12, color: '#fff', fontWeight: '600' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#2D3748', marginBottom: 12 },
  packsRow: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  packCard: { flex: 1, backgroundColor: '#fff', borderRadius: 16, padding: 14, alignItems: 'center', borderWidth: 1.5, borderColor: '#E2E8F0' },
  packCardPopular: { backgroundColor: '#FF8FA3', borderColor: '#FF8FA3' },
  popularBadge: { position: 'absolute', top: -10, backgroundColor: '#F6E05E', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  popularText: { fontSize: 8, fontWeight: '800', color: '#744210' },
  packLabel: { fontSize: 11, color: '#718096', fontWeight: '600', marginTop: 4 },
  packLabelPopular: { color: '#FFE0E6' },
  packAmount: { fontSize: 22, fontWeight: '800', color: '#2D3748', marginTop: 4 },
  packAmountPopular: { color: '#fff' },
  packCredits: { fontSize: 11, color: '#A0AEC0', marginTop: 2 },
  packCreditsPopular: { color: '#FFE0E6' },
  txnRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  txnIcon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  txnCredit: { backgroundColor: '#E6FFED' },
  txnDebit: { backgroundColor: '#FFF5F5' },
  txnInfo: { flex: 1, marginLeft: 12 },
  txnDesc: { fontSize: 13, fontWeight: '600', color: '#2D3748' },
  txnDate: { fontSize: 11, color: '#A0AEC0', marginTop: 2 },
  txnAmount: { fontSize: 14, fontWeight: '700' },
  txnAmountCredit: { color: '#48BB78' },
  txnAmountDebit: { color: '#F56565' },
  emptyText: { textAlign: 'center', color: '#A0AEC0', marginTop: 20, fontSize: 14 },
});
