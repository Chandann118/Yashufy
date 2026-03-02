import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, FlatList, TextInput } from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Play, Heart, Star, TrendingUp, Zap, Clock, Disc, Search, ArrowRight, Music } from 'lucide-react-native';
import { useDispatch, useSelector } from 'react-redux';
import { setTrack, setPlaying, setQueue, setCurrentIndex } from '../store/playerSlice';
import { playTrack } from '../services/audioService';
import { getThumbnailUrl } from '../utils/imageUtils';
import { fetchStreamWithRetry } from '../services/streamService';
import { warmupManager } from '../services/warmupService';

const CategoryCard = ({ title, color, onPress }) => (
    <TouchableOpacity
        className="w-[48%] h-24 rounded-2xl p-4 mb-4 overflow-hidden shadow-lg"
        style={{ backgroundColor: color }}
        onPress={onPress}
    >
        <Text className="text-white font-black text-xl">{title}</Text>
        <View className="absolute -bottom-2 -right-2 opacity-30">
            <Disc size={70} color="white" />
        </View>
    </TouchableOpacity>
);

const SectionHeader = ({ title, icon: Icon, color, showAll }) => (
    <View className="flex-row items-center justify-between mb-5 mt-8">
        <View className="flex-row items-center">
            <View className="w-8 h-8 rounded-lg items-center justify-center mr-3" style={{ backgroundColor: `${color}20` }}>
                <Icon size={18} color={color} />
            </View>
            <Text className="text-white font-bold text-2xl tracking-tight">{title}</Text>
        </View>
        {showAll && (
            <TouchableOpacity>
                <Text className="text-vortex-saffron font-bold text-xs uppercase tracking-widest">See All</Text>
            </TouchableOpacity>
        )}
    </View>
);

const SongCard = ({ title, artist, image, onPress }) => (
    <TouchableOpacity className="mr-5 w-40" onPress={onPress}>
        <View className="w-40 h-40 bg-vortex-surface rounded-3xl overflow-hidden mb-3 shadow-2xl border border-white/5">
            <Image
                source={{ uri: getThumbnailUrl({ thumbnail: image, title, artist }) }}
                className="w-full h-full"
                contentFit="cover"
                transition={300}
            />
            <View className="absolute bottom-2 right-2 w-10 h-10 bg-vortex-saffron rounded-full items-center justify-center shadow-lg">
                <Play size={18} color="black" fill="black" />
            </View>
        </View>
        <Text className="text-white font-bold text-sm px-1" numberOfLines={1}>{title}</Text>
        <Text className="text-vortex-textSecondary text-xs px-1 mt-0.5" numberOfLines={1}>{artist}</Text>
    </TouchableOpacity>
);

const SpotlightCard = ({ artistInfo, loading }) => {
    if (loading) return (
        <View className="h-56 w-full rounded-3xl bg-vortex-surface mb-8 border border-white/5 items-center justify-center">
            <Text className="text-vortex-textSecondary text-xs">Loading Spotlight...</Text>
        </View>
    );
    if (!artistInfo) return null;

    return (
        <TouchableOpacity className="mb-10 rounded-3xl overflow-hidden bg-vortex-surface border border-white/5 shadow-2xl">
            <Image source={{ uri: artistInfo.fanart || artistInfo.banner }} className="w-full h-56 opacity-60" />
            <View className="p-6 absolute bottom-0 left-0 right-0 bg-black/60">
                <View className="flex-row items-center mb-2">
                    <View className="px-2 py-0.5 bg-vortex-saffron rounded-md mr-2">
                        <Text className="text-black text-[10px] font-black uppercase">Spotlight</Text>
                    </View>
                    <Text className="text-vortex-saffron text-xs font-bold tracking-widest uppercase">Artist of the week</Text>
                </View>
                <Text className="text-white text-3xl font-black mb-2 tracking-tighter">{artistInfo.artistName}</Text>
                <Text className="text-vortex-textSecondary text-xs leading-4 opacity-90" numberOfLines={2}>{artistInfo.bio}</Text>
            </View>
        </TouchableOpacity>
    );
};

export default function HomeScreen({ navigation }) {
    const [greeting, setGreeting] = useState('Good evening');
    const [trending, setTrending] = useState([]);
    const [recent, setRecent] = useState([]);
    const [spotlight, setSpotlight] = useState(null);
    const [loading, setLoading] = useState(true);
    const [fetchingTrackId, setFetchingTrackId] = useState(null);
    const [directUrl, setDirectUrl] = useState('');

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
            if (trending && trending.length > 0) {
                warmupManager.warmUpTracks(trending.slice(0, 5));
            }
        }
    };

    const handlePlay = async (item, index, customQueue) => {
        if (fetchingTrackId) return;

        try {
            setFetchingTrackId(item.id);
            const queueToUse = customQueue || trending;
            const itemIndex = index !== undefined ? index : queueToUse.findIndex(i => i.id === item.id);

            const streamData = await fetchStreamWithRetry(item);

            const track = {
                id: item.id || streamData.id,
                url: streamData.stream_url,
                title: item.title || "Direct Stream",
                artist: item.artist || "Unknown Artist",
                artwork: getThumbnailUrl({ ...item, thumbnail: streamData.thumbnail }),
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
            alert("This song is currently unavailable. Trying to wake up services...");
        } finally {
            setFetchingTrackId(null);
        }
    };

    const handleDirectStream = () => {
        if (!directUrl.trim()) return;

        // If it's a URL, handle as direct stream, else search
        if (directUrl.includes('youtube.com') || directUrl.includes('youtu.be') || directUrl.length === 11) {
            const videoId = directUrl.includes('v=') ? directUrl.split('v=')[1].split('&')[0] : (directUrl.includes('be/') ? directUrl.split('be/')[1] : directUrl);
            handlePlay({ id: videoId, title: "Stream Link", artist: "External Source" });
        } else {
            navigation.navigate('Search', { q: directUrl });
        }
        setDirectUrl('');
    };

    return (
        <SafeAreaView className="flex-1 bg-vortex-obsidian">
            <ScrollView className="px-6" showsVerticalScrollIndicator={false}>

                {/* Header */}
                <View className="flex-row justify-between items-center mt-8 mb-10">
                    <View>
                        <Text className="text-vortex-textSecondary text-xs font-bold uppercase tracking-[4px] mb-1">{greeting}</Text>
                        <View className="flex-row items-center">
                            <Text className="text-white text-4xl font-black italic">Yashu</Text>
                            <Text className="text-vortex-saffron text-4xl font-black ml-1">fy</Text>
                        </View>
                    </View>
                    <TouchableOpacity className="w-14 h-14 rounded-2xl bg-vortex-surface border border-white/10 items-center justify-center shadow-xl">
                        <Image
                            source={require('../../assets/icon.png')}
                            className="w-10 h-10"
                            contentFit="contain"
                        />
                    </TouchableOpacity>
                </View>

                {/* Direct Stream / Instant Search */}
                <View className="bg-vortex-surface p-1 rounded-2xl flex-row items-center mb-10 border border-white/5 shadow-2xl">
                    <View className="pl-4">
                        <Music size={20} color="#FF9933" />
                    </View>
                    <TextInput
                        className="flex-1 text-white font-bold h-12 px-3 text-sm"
                        placeholder="Paste YT link or search any song..."
                        placeholderTextColor="#666"
                        value={directUrl}
                        onChangeText={setDirectUrl}
                    />
                    <TouchableOpacity
                        className="bg-vortex-saffron w-10 h-10 rounded-xl items-center justify-center mr-1"
                        onPress={handleDirectStream}
                    >
                        <ArrowRight size={20} color="black" />
                    </TouchableOpacity>
                </View>

                <SpotlightCard artistInfo={spotlight} loading={loading} />

                <SectionHeader title="Jump Back In" icon={Clock} color="#FF9933" showAll={recent.length > 5} />
                <FlatList
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    data={recent}
                    keyExtractor={(item) => `recent-${item.id}`}
                    renderItem={({ item, index }) => (
                        <SongCard
                            title={item.title}
                            artist={item.artist}
                            image={item.thumbnail}
                            onPress={() => handlePlay(item, index, recent)}
                        />
                    )}
                    ListEmptyComponent={<Text className="text-vortex-textSecondary ml-4 italic">Your listening history starts here...</Text>}
                />

                <SectionHeader title="Moods & Genres" icon={Star} color="#0070FF" />
                <View className="flex-row flex-wrap justify-between">
                    <CategoryCard title="Chill" color="#1E3A8A" onPress={() => navigation.navigate('Search', { category: 'Chill' })} />
                    <CategoryCard title="Workout" color="#7F1D1D" onPress={() => navigation.navigate('Search', { category: 'Workout' })} />
                    <CategoryCard title="Focus" color="#064E3B" onPress={() => navigation.navigate('Search', { category: 'Focus' })} />
                    <CategoryCard title="Party" color="#4C1D95" onPress={() => navigation.navigate('Search', { category: 'Party' })} />
                </View>

                <SectionHeader title="Trending Hits" icon={TrendingUp} color="#FF9933" showAll={true} />
                <FlatList
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    data={trending}
                    keyExtractor={(item) => `trending-${item.id}`}
                    renderItem={({ item, index }) => (
                        <SongCard
                            title={item.title}
                            artist={item.artist}
                            image={item.thumbnail}
                            onPress={() => handlePlay(item, index, trending)}
                        />
                    )}
                    ListEmptyComponent={<View className="flex-row">{[1, 2, 3].map(i => <View key={i} className="mr-5 w-40 h-56 bg-vortex-surface rounded-3xl animate-pulse" />)}</View>}
                />

                <View className="h-40" />
            </ScrollView>
        </SafeAreaView>
    );
}
