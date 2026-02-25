import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, Alert, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useDispatch, useSelector } from 'react-redux';
import { setBackendUrl, setDiscoveryUrl } from '../store/settingsSlice';
import { Settings, Globe, Save, Zap, ChevronDown, ChevronUp } from 'lucide-react-native';

export default function ProfileScreen() {
    const settings = useSelector(state => state.settings);
    const [url, setUrl] = useState(settings.backendUrl);
    const [discoveryUrl, setDiscoveryUrlLocal] = useState(settings.discoveryUrl || '');
    const [syncing, setSyncing] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const dispatch = useDispatch();

    const handleSave = () => {
        if (!url.startsWith('http')) {
            Alert.alert('Invalid URL', 'Please enter a URL starting with http:// or https://');
            return;
        }
        dispatch(setBackendUrl(url));
        Alert.alert('Success', 'Backend URL saved!');
    };

    const handleSaveDiscovery = () => {
        if (discoveryUrl && !discoveryUrl.startsWith('http')) {
            Alert.alert('Invalid URL', 'Please enter a valid URL for Discovery');
            return;
        }
        dispatch(setDiscoveryUrl(discoveryUrl));
        Alert.alert('Success', 'Discovery URL saved!');
    };

    const handleSync = async () => {
        if (!discoveryUrl) {
            Alert.alert('Error', 'Please enter a Discovery URL first.');
            return;
        }
        setSyncing(true);
        try {
            const response = await fetch(discoveryUrl);
            const text = await response.text();
            const latestUrl = text.trim();
            if (latestUrl.startsWith('http')) {
                dispatch(setBackendUrl(latestUrl));
                setUrl(latestUrl);
                Alert.alert('Synced!', `Updated to: ${latestUrl}`);
            } else {
                Alert.alert('Error', 'Invalid URL in discovery file.');
            }
        } catch (error) {
            Alert.alert('Sync Failed', 'Could not reach discovery server.');
        } finally {
            setSyncing(false);
        }
    };

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
            >
                {/* Header */}
                <View style={styles.header}>
                    <View style={styles.headerIconContainer}>
                        <Settings size={32} color="#FF9933" />
                    </View>
                    <View style={styles.headerTextContainer}>
                        <Text style={styles.headerTitle}>Settings</Text>
                        <Text style={styles.headerSubtitle}>App & Connection</Text>
                    </View>
                </View>

                {/* Main Settings Card */}
                <View style={styles.card}>
                    <Text style={styles.cardTitle}>App Preferences</Text>

                    <View style={styles.settingRow}>
                        <Text style={styles.settingLabel}>Audio Quality</Text>
                        <Text style={styles.settingValue}>High (320kbps)</Text>
                    </View>

                    <View style={styles.settingRow}>
                        <Text style={styles.settingLabel}>Production Mode</Text>
                        <View style={styles.toggleActive} />
                    </View>

                    {/* Advanced Toggle Button */}
                    <Pressable
                        style={({ pressed }) => [
                            styles.advancedToggle,
                            { opacity: pressed ? 0.7 : 1 }
                        ]}
                        onPress={() => setShowAdvanced(!showAdvanced)}
                        hitSlop={20}
                    >
                        <Text style={styles.advancedToggleText}>
                            {showAdvanced ? "Hide Developer Settings" : "Advanced Connection Settings"}
                        </Text>
                        {showAdvanced ? <ChevronUp size={16} color="#666" /> : <ChevronDown size={16} color="#666" />}
                    </Pressable>
                </View>

                {showAdvanced && (
                    <>
                        {/* Auto-Discovery Card */}
                        <View style={[styles.card, styles.advancedCard]}>
                            <View style={styles.cardHeader}>
                                <Zap size={20} color="#FF9933" />
                                <Text style={styles.cardSectionTitle}>Auto-Discovery (Recommended)</Text>
                            </View>
                            <Text style={styles.description}>For automated updates for you and your friends.</Text>

                            <TextInput
                                style={styles.input}
                                placeholder="Gist Raw URL"
                                placeholderTextColor="#666"
                                value={discoveryUrl}
                                onChangeText={setDiscoveryUrlLocal}
                                autoCapitalize="none"
                            />

                            <View style={styles.buttonRow}>
                                <Pressable
                                    style={({ pressed }) => [styles.secondaryButton, { opacity: pressed ? 0.7 : 1 }]}
                                    onPress={handleSaveDiscovery}
                                    hitSlop={10}
                                >
                                    <Text style={styles.secondaryButtonText}>Save Link</Text>
                                </Pressable>
                                <Pressable
                                    style={({ pressed }) => [styles.primaryButton, { opacity: pressed ? 0.7 : 1 }]}
                                    onPress={handleSync}
                                    disabled={syncing}
                                    hitSlop={10}
                                >
                                    <Text style={styles.primaryButtonText}>{syncing ? 'Syncing...' : 'Sync Now'}</Text>
                                </Pressable>
                            </View>
                        </View>

                        {/* Manual Connection Card */}
                        <View style={styles.card}>
                            <View style={styles.cardHeader}>
                                <Globe size={20} color="#FF9933" />
                                <Text style={styles.cardSectionTitle}>Manual Server URL</Text>
                            </View>

                            <TextInput
                                style={styles.input}
                                value={url}
                                onChangeText={setUrl}
                                autoCapitalize="none"
                                autoCorrect={false}
                            />

                            <Pressable
                                style={({ pressed }) => [styles.saveButton, { opacity: pressed ? 0.7 : 1 }]}
                                onPress={handleSave}
                                hitSlop={10}
                            >
                                <Save size={20} color="black" />
                                <Text style={styles.saveButtonText}>Apply URL Manually</Text>
                            </Pressable>
                        </View>
                    </>
                )}

                <View style={styles.footer}>
                    <Text style={styles.footerText}>Vortex Music v1.0.0 (Production)</Text>
                    <Text style={styles.footerTextSub}>Built by Antigravity AI</Text>
                </View>
                <View style={{ height: 100 }} />
            </ScrollView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
    },
    scrollContent: {
        paddingHorizontal: 24,
        paddingTop: 40,
        flexGrow: 1,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 32,
    },
    headerIconContainer: {
        width: 64,
        height: 64,
        backgroundColor: 'rgba(255, 153, 51, 0.15)',
        borderRadius: 32,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1,
        borderColor: 'rgba(255, 153, 51, 0.2)',
    },
    headerTextContainer: {
        marginLeft: 16,
    },
    headerTitle: {
        color: '#FFFFFF',
        fontSize: 32,
        fontWeight: '900',
    },
    headerSubtitle: {
        color: '#A0A0A0',
        fontSize: 14,
    },
    card: {
        backgroundColor: '#111',
        padding: 24,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.05)',
        marginBottom: 20,
    },
    advancedCard: {
        borderColor: 'rgba(255, 153, 51, 0.3)',
    },
    cardTitle: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 20,
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    cardSectionTitle: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: 'bold',
        marginLeft: 10,
    },
    description: {
        color: '#A0A0A0',
        fontSize: 12,
        marginBottom: 16,
    },
    settingRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 14,
        borderBottomWidth: 1,
        borderBottomColor: 'rgba(255,255,255,0.05)',
    },
    settingLabel: {
        color: '#FFFFFF',
        fontSize: 16,
    },
    settingValue: {
        color: '#FF9933',
        fontWeight: '500',
    },
    toggleActive: {
        width: 44,
        height: 22,
        backgroundColor: '#FF9933',
        borderRadius: 11,
    },
    advancedToggle: {
        marginTop: 20,
        paddingVertical: 16,
        backgroundColor: 'rgba(255,255,255,0.03)',
        borderRadius: 12,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.05)',
    },
    advancedToggleText: {
        color: '#A0A0A0',
        fontSize: 13,
        fontWeight: '600',
        marginRight: 8,
    },
    input: {
        backgroundColor: '#050505',
        color: '#FFFFFF',
        padding: 16,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#333',
        fontSize: 16,
        marginBottom: 16,
    },
    buttonRow: {
        flexDirection: 'row',
    },
    primaryButton: {
        flex: 1,
        backgroundColor: '#FF9933',
        padding: 14,
        borderRadius: 12,
        alignItems: 'center',
        marginLeft: 8,
    },
    primaryButtonText: {
        color: '#000000',
        fontWeight: 'bold',
        fontSize: 16,
    },
    secondaryButton: {
        flex: 1,
        backgroundColor: '#222',
        padding: 14,
        borderRadius: 12,
        alignItems: 'center',
        marginRight: 8,
    },
    secondaryButtonText: {
        color: '#FFFFFF',
        fontWeight: 'bold',
        fontSize: 16,
    },
    saveButton: {
        backgroundColor: '#FF9933',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        borderRadius: 12,
        marginTop: 8,
    },
    saveButtonText: {
        color: '#000000',
        fontWeight: 'bold',
        fontSize: 18,
        marginLeft: 10,
    },
    footer: {
        marginTop: 20,
        alignItems: 'center',
    },
    footerText: {
        color: '#666',
        fontSize: 12,
    },
    footerTextSub: {
        color: '#444',
        fontSize: 11,
        marginTop: 4,
    }
});
