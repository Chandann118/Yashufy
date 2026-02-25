import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useDispatch, useSelector } from 'react-redux';
import { setBackendUrl, setDiscoveryUrl } from '../store/settingsSlice';
import { Settings, Globe, Save, Zap } from 'lucide-react-native';

export default function ProfileScreen() {
    const settings = useSelector(state => state.settings);
    const [url, setUrl] = useState(settings.backendUrl);
    const [discoveryUrl, setDiscoveryUrlLocal] = useState(settings.discoveryUrl || '');
    const [syncing, setSyncing] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const dispatch = useDispatch();

    const handleSave = () => {
        if (!url.startsWith('http')) {
            Alert.alert('Invalid URL', 'Please enter a valid URL starting with http:// or https://');
            return;
        }
        dispatch(setBackendUrl(url));
        Alert.alert('Success', 'Backend URL saved!');
    };

    const handleSaveDiscovery = () => {
        if (discoveryUrl && !discoveryUrl.startsWith('http')) {
            Alert.alert('Invalid URL', 'Please enter a valid URL for the Discovery Service');
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
                Alert.alert('Synced!', `Backend URL updated to: ${latestUrl}`);
            } else {
                Alert.alert('Error', 'The discovery file does not contain a valid URL.');
            }
        } catch (error) {
            Alert.alert('Sync Failed', 'Could not reach the discovery server.');
        } finally {
            setSyncing(false);
        }
    };

    return (
        <SafeAreaView className="flex-1 bg-vortex-obsidian">
            <ScrollView className="px-6 mt-10" showsVerticalScrollIndicator={false}>
                <View className="flex-row items-center mb-8">
                    <View className="w-16 h-16 bg-vortex-saffron/20 rounded-full items-center justify-center border border-vortex-saffron/30">
                        <Settings size={32} color="#FF9933" />
                    </View>
                    <View className="ml-4">
                        <Text className="text-white text-3xl font-extrabold">Settings</Text>
                        <Text className="text-vortex-textSecondary text-sm">Configure your experience</Text>
                    </View>
                </View>

                {/* Main App Settings */}
                <View className="bg-vortex-surface p-6 rounded-2xl border border-white/5 mb-6">
                    <Text className="text-white text-lg font-bold mb-4">App Settings</Text>

                    <View className="flex-row justify-between items-center py-3 border-b border-white/5">
                        <Text className="text-white">Audio Quality</Text>
                        <Text className="text-vortex-saffron">High (320kbps)</Text>
                    </View>

                    <View className="flex-row justify-between items-center py-3 border-b border-white/5">
                        <Text className="text-white">Dark Mode</Text>
                        <View className="w-10 h-5 bg-vortex-saffron rounded-full" />
                    </View>

                    <TouchableOpacity
                        className="mt-6 py-4 bg-white/5 rounded-xl border border-white/10 items-center justify-center"
                        onPress={() => {
                            console.log('Toggling advanced settings');
                            setShowAdvanced(!showAdvanced);
                        }}
                    >
                        <Text className="text-vortex-textSecondary text-sm font-medium">
                            {showAdvanced ? "Hide Developer Settings" : "Advanced Connection Settings"}
                        </Text>
                    </TouchableOpacity>
                </View>

                {showAdvanced && (
                    <>
                        {/* Discovery Mode */}
                        <View className="bg-vortex-surface p-6 rounded-2xl border border-vortex-saffron/30 mb-6">
                            <View className="flex-row items-center mb-4">
                                <Zap size={20} color="#FF9933" />
                                <Text className="text-white text-lg font-semibold ml-2">Developer Discovery</Text>
                            </View>
                            <TextInput
                                className="bg-vortex-obsidian text-white p-4 rounded-xl border border-[#333] focus:border-vortex-saffron mb-4"
                                placeholder="Gist Raw URL"
                                placeholderTextColor="#666"
                                value={discoveryUrl}
                                onChangeText={setDiscoveryUrlLocal}
                                autoCapitalize="none"
                            />
                            <View className="flex-row justify-between">
                                <TouchableOpacity
                                    className="bg-[#333] p-3 rounded-xl flex-1 mr-2 items-center"
                                    onPress={handleSaveDiscovery}
                                >
                                    <Text className="text-white font-bold">Save</Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                    className="bg-vortex-saffron p-3 rounded-xl flex-1 ml-2 items-center"
                                    onPress={handleSync}
                                    disabled={syncing}
                                >
                                    <Text className="text-black font-bold">{syncing ? 'Syncing...' : 'Sync Now'}</Text>
                                </TouchableOpacity>
                            </View>
                        </View>

                        {/* Manual Connection */}
                        <View className="bg-vortex-surface p-6 rounded-2xl border border-white/5 mb-10">
                            <View className="flex-row items-center mb-4">
                                <Globe size={20} color="#FF9933" />
                                <Text className="text-white text-lg font-semibold ml-2">Manual Server URL</Text>
                            </View>

                            <TextInput
                                className="bg-vortex-obsidian text-white p-4 rounded-xl border border-[#333] focus:border-vortex-saffron"
                                value={url}
                                onChangeText={setUrl}
                                autoCapitalize="none"
                                autoCorrect={false}
                            />

                            <TouchableOpacity
                                className="bg-[#222] mt-4 p-4 rounded-xl flex-row justify-center items-center border border-[#333]"
                                onPress={handleSave}
                            >
                                <Save size={20} color="#FF9933" />
                                <Text className="text-white font-bold text-lg ml-2">Save Server</Text>
                            </TouchableOpacity>
                        </View>
                    </>
                )}

                <View className="mt-10 items-center">
                    <Text className="text-vortex-textSecondary text-xs">Vortex Music v1.0.0 (Production)</Text>
                    <Text className="text-vortex-textSecondary text-xs mt-1">Built by Antigravity AI</Text>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
}
