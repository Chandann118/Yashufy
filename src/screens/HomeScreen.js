import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, FlatList } from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Play, Heart, Star, TrendingUp, Zap, Clock, Disc } from 'lucide-react-native';
import { useDispatch, useSelector } from 'react-redux';
import { setTrack, setPlaying } from '../store/playerSlice';
import { playTrack } from '../services/audioService';

const CategoryCard = ({ title, color }) => (
    <TouchableOpacity
        className="w-[48%] h-24 rounded-xl p-3 mb-4 overflow-hidden"
        style={{ backgroundColor: color }}
    >
        <Text className="text-white font-bold text-lg">{title}</Text>
        <View className="absolute -bottom-2 -right-2 opacity-20">
            <Disc size={60} color="white" />
        </View>
    </TouchableOpacity>
);

const SectionHeader = ({ title, icon: Icon, color }) => (
    <View className="flex-row items-center mb-4 mt-6">
        <Icon size={20} color={color} />
        <Text className="text-white font-bold text-xl ml-2">{title}</Text>
    </View>
);

const SongCard = ({ title, artist, image, onPress }) => (
    <TouchableOpacity className="mr-4 w-36" onPress={onPress}>
        <View className="w-36 h-36 bg-vortex-surface rounded-xl overflow-hidden mb-2">
            <Image source={{ uri: image || 'https://via.placeholder.com/150' }} className="w-full h-full" />
        </View>
        <Text className="text-white font-semibold" numberOfLines={1}>{title}</Text>
        <Text className="text-vortex-textSecondary text-xs" numberOfLines={1}>{artist}</Text>
    </TouchableOpacity>
);

const SpotlightCard = ({ artistInfo, loading }) => {
    if (loading) return null;
    if (!artistInfo) return null;

    return (
        <View className="mb-8 rounded-2xl overflow-hidden bg-vortex-surface border border-vortex-surface">
            <Image source={{ uri: artistInfo.fanart || artistInfo.banner }} className="w-full h-48 opacity-70" />
            <View className="p-4 absolute bottom-0 left-0 right-0 bg-black/40">
                <View className="flex-row items-center mb-1">
                    <Star size={16} color="#FF9933" />
                    <Text className="text-vortex-saffron text-xs font-bold ml-1 uppercase tracking-tighter">Artist Spotlight</Text>
                </View>
                <Text className="text-white text-2xl font-black mb-1">{artistInfo.artistName}</Text>
                <Text className="text-vortex-textSecondary text-xs leading-4" numberOfLines={2}>{artistInfo.bio}</Text>
            </View>
        </View>
    );
};

export default function HomeScreen({ navigation }) {
    const [greeting, setGreeting] = useState('Good evening');
    const [trending, setTrending] = useState([]);
    const [recent, setRecent] = useState([]);
    const [spotlight, setSpotlight] = useState(null);
    const [loading, setLoading] = useState(true);
    const [fetchingTrackId, setFetchingTrackId] = useState(null);

    const backendUrl = useSelector(state => state.settings.backendUrl);
    const dispatch = useDispatch();

    useEffect(() => {
        const hour = new Date().getHours();
        if (hour < 12) setGreeting('Good morning');
        else if (hour < 18) setGreeting('Good afternoon');
        else setGreeting('Good evening');

        fetchHomeContent();
    }, [backendUrl]);

    const fetchHomeContent = async () => {
        try {
            const response = await fetch(`${backendUrl}/home`, {
                headers: { 'Bypass-Tunnel-Reminder': 'true' }
            });
            const data = await response.json();
            setTrending(data.trending || []);
            setRecent(data.recently_played || []);

            // Fetch spotlight for a random trending artist or a fallback
            const artistToSpotlight = data.trending?.[0]?.artist || "Arijit Singh";
            const artistRes = await fetch(`${backendUrl}/artist/${encodeURIComponent(artistToSpotlight)}`, {
                headers: { 'Bypass-Tunnel-Reminder': 'true' }
            });
            if (artistRes.ok) {
                const artistData = await artistRes.json();
                setSpotlight({ ...artistData, artistName: artistToSpotlight });
            }
        } catch (error) {
            console.error('Home fetch error:', error);
        } finally {
            setLoading(false);
        }
    };

    const handlePlay = async (item, index, customQueue) => {
        if (fetchingTrackId) return; // Prevent multiple clicks

        try {
            setFetchingTrackId(item.id);
            const queueToUse = customQueue || trending;
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
            <ScrollView className="px-6" showsVerticalScrollIndicator={false}>

                {/* Header */}
                <View className="flex-row justify-between items-center mt-6 mb-8">
                    <View>
                        <Text className="text-vortex-textSecondary text-sm font-medium uppercase tracking-widest">{greeting}</Text>
                        <Text className="text-white text-3xl font-extrabold">नमस्ते, <Text className="text-vortex-saffron">Vortex</Text></Text>
                    </View>
                    <TouchableOpacity className="w-12 h-12 rounded-full border border-vortex-saffron items-center justify-center">
                        <Zap size={24} color="#FF9933" />
                    </TouchableOpacity>
                </View>

                <SpotlightCard artistInfo={spotlight} loading={loading} />

                <SectionHeader title="Recently Played" icon={Clock} color="#FF9933" />
                <FlatList
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    data={recent}
                    keyExtractor={(item) => item.id}
                    renderItem={({ item, index }) => (
                        <SongCard
                            title={item.title}
                            artist={item.artist}
                            image={item.thumbnail}
                            onPress={() => handlePlay(item, index, recent)}
                        />
                    )}
                    ListEmptyComponent={<Text className="text-vortex-textSecondary ml-4">No recent songs</Text>}
                />

                {/* Categories / Moods */}
                <SectionHeader title="Moods & Genres" icon={Star} color="#0070FF" />
                <View className="flex-row flex-wrap justify-between">
                    <CategoryCard title="Chill" color="#1E3A8A" />
                    <CategoryCard title="Workout" color="#7F1D1D" />
                    <CategoryCard title="Focus" color="#064E3B" />
                    <CategoryCard title="Party" color="#4C1D95" />
                </View>

                {/* Trending */}
                <SectionHeader title="Trending Hits" icon={TrendingUp} color="#FF9933" />
                <FlatList
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    data={trending}
                    keyExtractor={(item) => item.id}
                    renderItem={({ item, index }) => (
                        <SongCard
                            title={item.title}
                            artist={item.artist}
                            image={item.thumbnail}
                            onPress={() => handlePlay(item, index, trending)}
                        />
                    )}
                    ListEmptyComponent={<Text className="text-vortex-textSecondary ml-4">Loading trending...</Text>}
                />

                <View className="h-40" />
            </ScrollView>
        </SafeAreaView>
    );
}
