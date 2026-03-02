import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Alert, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useSelector } from 'react-redux';
import { Bug, CheckCircle2, XCircle, RefreshCw, Terminal, Activity, Globe, Wifi } from 'lucide-react-native';

const StatusCard = ({ title, status, details, icon: Icon, color }) => (
    <View style={styles.card}>
        <View style={styles.cardHeader}>
            <View style={[styles.iconContainer, { backgroundColor: `${color}20` }]}>
                <Icon size={20} color={color} />
            </View>
            <Text style={styles.cardTitle}>{title}</Text>
            <View style={[styles.badge, { backgroundColor: status === 'ok' ? '#4ADE8020' : '#F8717120' }]}>
                <Text style={[styles.badgeText, { color: status === 'ok' ? '#4ADE80' : '#F87171' }]}>
                    {status === 'ok' ? 'ONLINE' : 'ERROR'}
                </Text>
            </View>
        </View>
        {details && <Text style={styles.detailsText}>{details}</Text>}
    </View>
);

export default function DebugScreen() {
    const backendUrl = useSelector(state => state.settings.backendUrl);
    const [pingStatus, setPingStatus] = useState('loading');
    const [ytStatus, setYtStatus] = useState('loading');
    const [pingDetails, setPingDetails] = useState('');
    const [ytDetails, setYtDetails] = useState('');
    const [refreshing, setRefreshing] = useState(false);

    const runDiagnostics = async () => {
        setRefreshing(true);
        setPingStatus('loading');
        setYtStatus('loading');

        // 1. Test Ping
        try {
            const start = Date.now();
            const res = await fetch(`${backendUrl}/ping`, { headers: { 'Bypass-Tunnel-Reminder': 'true' } });
            const end = Date.now();
            if (res.ok) {
                const data = await res.json();
                setPingStatus('ok');
                setPingDetails(`Latency: ${end - start}ms\nTimestamp: ${new Date(data.timestamp * 1000).toLocaleString()}`);
            } else {
                setPingStatus('error');
                setPingDetails(`HTTP ${res.status}: ${res.statusText}`);
            }
        } catch (e) {
            setPingStatus('error');
            setPingDetails(e.message);
        }

        // 2. Test YouTube Extraction
        try {
            const res = await fetch(`${backendUrl}/test-youtube`, { headers: { 'Bypass-Tunnel-Reminder': 'true' } });
            if (res.ok) {
                const data = await res.json();
                setYtStatus('ok');
                const methods = Object.entries(data.results)
                    .map(([name, r]) => `${name.toUpperCase()}: ${r.success ? '✅' : '❌'}${r.time ? ` (${Math.round(r.time * 1000)}ms)` : ''}`)
                    .join('\n');
                setYtDetails(`Total Time: ${Math.round(data.total_time * 1000)}ms\n\n${methods}`);
            } else {
                setYtStatus('error');
                setYtDetails(`HTTP ${res.status}: ${res.statusText}\nMake sure backend is updated with /test-youtube endpoint.`);
            }
        } catch (e) {
            setYtStatus('error');
            setYtDetails(e.message);
        }

        setRefreshing(false);
    };

    useEffect(() => {
        runDiagnostics();
    }, [backendUrl]);

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <View style={styles.headerText}>
                    <Bug size={24} color="#FF9933" />
                    <Text style={styles.title}>System Diagnostics</Text>
                </View>
                <TouchableOpacity onPress={runDiagnostics} disabled={refreshing}>
                    {refreshing ? <ActivityIndicator color="#FF9933" /> : <RefreshCw size={24} color="#FF9933" />}
                </TouchableOpacity>
            </View>

            <ScrollView contentContainerStyle={styles.scrollContent}>
                <View style={styles.urlCard}>
                    <Globe size={16} color="#A0A0A0" />
                    <Text style={styles.urlText}>{backendUrl}</Text>
                </View>

                <StatusCard
                    title="Backend Connectivity"
                    status={pingStatus}
                    details={pingDetails}
                    icon={Wifi}
                    color="#0070FF"
                />

                <StatusCard
                    title="YouTube Extraction"
                    status={ytStatus}
                    details={ytDetails}
                    icon={Terminal}
                    color="#FF9933"
                />

                <View style={styles.infoBox}>
                    <Activity size={18} color="#666" />
                    <Text style={styles.infoText}>
                        If extraction fails but connectivity is OK, YouTube might be blocking the Render IP.
                        The backend will automatically try fallback methods (Piped, Invidious).
                    </Text>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#050505' },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 24,
        paddingVertical: 20,
        borderBottomWidth: 1,
        borderBottomColor: '#111'
    },
    headerText: { flexDirection: 'row', alignItems: 'center' },
    title: { color: '#FFF', fontSize: 20, fontWeight: '900', marginLeft: 12 },
    scrollContent: { padding: 24 },
    urlCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        padding: 12,
        borderRadius: 12,
        marginBottom: 24,
        borderWidth: 1,
        borderColor: '#222'
    },
    urlText: { color: '#A0A0A0', fontSize: 12, marginLeft: 8, fontStyle: 'italic' },
    card: {
        backgroundColor: '#0A0A0A',
        borderRadius: 20,
        padding: 20,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: '#111'
    },
    cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
    iconContainer: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyCenter: 'center', paddingTop: 8 },
    cardTitle: { color: '#FFF', fontSize: 16, fontWeight: 'bold', flex: 1, marginLeft: 12 },
    badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
    badgeText: { fontSize: 10, fontWeight: '900' },
    detailsText: { color: '#A0A0A0', fontSize: 13, lineHeight: 20, fontFamily: 'monospace' },
    infoBox: {
        flexDirection: 'row',
        backgroundColor: '#111',
        padding: 16,
        borderRadius: 16,
        marginTop: 24,
        alignItems: 'flex-start'
    },
    infoText: { color: '#666', fontSize: 12, lineHeight: 18, marginLeft: 12, flex: 1 }
});
