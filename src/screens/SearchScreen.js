import React, { useState } from 'react';
import { View, Text, TextInput, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Search, Play, Heart, MoreVertical } from 'lucide-react-native';
import { useDispatch } from 'react-redux';
import { setTrack, setPlaying, setQueue, setCurrentIndex } from '../store/playerSlice';
import { playTrack } from '../services/audioService';
import { useSelector } from 'react-redux';

export default function SearchScreen({ navigation }) {
    const backendUrl = useSelector(state => state.settings.backendUrl);
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fetchingTrackId, setFetchingTrackId] = useState(null);
    const dispatch = useDispatch();

    const handleSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        try {
            const response = await fetch(`${backendUrl}/search?q=${encodeURIComponent(query)}`, {
                headers: { 'Bypass-Tunnel-Reminder': 'true' }
            });
            const data = await response.json();
            setResults(data);
        } catch (error) {
            console.error('Search error:', error);
        } finally {
            setLoading(false);
        }
    };

    const handlePlay = async (item, index, customQueue) => {
        if (fetchingTrackId) return;

        try {
            setFetchingTrackId(item.id);
            const queueToUse = customQueue || results;
            const itemIndex = index !== undefined ? index : queueToUse.findIndex(i => i.id === item.id);

            const streamResponse = await fetch(`${backendUrl}/stream?id=${item.id}&title=${encodeURIComponent(item.title)}&artist=${encodeURIComponent(item.artist)}&duration_total=${item.duration || ''}`, {
                headers: { 'Bypass-Tunnel-Reminder': 'true' }
            });

            if (!streamResponse.ok) throw new Error('Failed to fetch stream');

            const streamData = await streamResponse.json();

            const track = {
                id: item.id,
                url: streamData.stream_url,
                title: item.title,
                artist: item.artist,
                artwork: streamData.thumbnail || item.thumbnail,
                duration: item.duration || streamData.duration,
            };

            dispatch(setTrack(track));
            dispatch(setQueue(queueToUse));
            dispatch(setCurrentIndex(itemIndex));
            dispatch(setPlaying(true));

            await playTrack(track, (status) => {
                if (status.didJustFinish) {
                    dispatch(setPlaying(false));
                }
            });

            navigation.navigate('Tabs', { screen: 'Home' });
            navigation.navigate('Player');
        } catch (error) {
            console.error('Playback error:', error);
            alert("Streaming service is slow or busy. Please try another song.");
        } finally {
            setFetchingTrackId(null);
        }
    };

    return (
        <SafeAreaView className="flex-1 bg-vortex-obsidian">
            <View className="px-6 mt-6">
                <Text className="text-white text-3xl font-extrabold mb-6">Discovery</Text>

                {/* Search Bar */}
                <View className="flex-row items-center bg-vortex-surface rounded-full px-4 py-2 border border-vortex-surface focus:border-vortex-saffron">
                    <Search size={20} color="#A0A0A0" />
                    <TextInput
                        className="flex-1 ml-2 text-white text-base"
                        placeholder="What do you want to listen to?"
                        placeholderTextColor="#A0A0A0"
                        value={query}
                        onChangeText={setQuery}
                        onSubmitEditing={handleSearch}
                    />
                </View>

                {loading && (
                    <View className="mt-10">
                        <ActivityIndicator color="#FF9933" size="large" />
                    </View>
                )}

                {/* Results List */}
                <FlatList
                    className="mt-6"
                    data={results}
                    keyExtractor={(item) => item.id}
                    showsVerticalScrollIndicator={false}
                    renderItem={({ item, index }) => (
                        <TouchableOpacity
                            className="flex-row items-center mb-6"
                            onPress={() => handlePlay(item, index, results)}
                        >
                            <View className="relative">
                                <Image source={{ uri: item.thumbnail }} className="w-16 h-16 rounded-lg" />
                                {item.source && (
                                    <View className="absolute -bottom-1 -right-1 bg-vortex-saffron px-1.5 py-0.5 rounded-md">
                                        <Text className="text-black text-[8px] font-bold uppercase">{item.source}</Text>
                                    </View>
                                )}
                            </View>
                            <View className="flex-1 ml-4 justify-center">
                                <Text className="text-white font-semibold text-lg" numberOfLines={1}>{item.title}</Text>
                                <View className="flex-row items-center">
                                    <Text className="text-vortex-textSecondary text-sm" numberOfLines={1}>{item.artist}</Text>
                                    {item.duration && (
                                        <Text className="text-vortex-textSecondary text-xs ml-2">• {Math.floor(item.duration / 60)}:{(item.duration % 60).toString().padStart(2, '0')}</Text>
                                    )}
                                </View>
                            </View>
                            <TouchableOpacity className="p-2">
                                <Play size={24} color="#FF9933" />
                            </TouchableOpacity>
                        </TouchableOpacity>
                    )}
                    ListEmptyComponent={!loading && query && (
                        <Text className="text-vortex-textSecondary text-center mt-10">No results found for "{query}"</Text>
                    )}
                />
            </View>
        </SafeAreaView>
    );
}
