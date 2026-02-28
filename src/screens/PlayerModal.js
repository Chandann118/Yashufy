import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, Dimensions } from 'react-native';
import { Image } from 'expo-image';
import { useSelector, useDispatch } from 'react-redux';
import Slider from '@react-native-community/slider';
import Animated, {
    useSharedValue,
    useAnimatedStyle,
    withRepeat,
    withTiming,
    Easing,
    withSpring
} from 'react-native-reanimated';
import { Play, Pause, SkipForward, SkipBack, ChevronDown, Heart, Share2, Shuffle, Repeat, MoreVertical } from 'lucide-react-native';
import { setPlaying, setTrack, toggleShuffle, toggleRepeatMode, setCurrentIndex } from '../store/playerSlice';
import { togglePlayback, seekTo, getPlaybackInstance, playTrack } from '../services/audioService';
import { fetchStreamWithRetry } from '../services/streamService';
import { getThumbnailUrl } from '../utils/imageUtils';
import { SafeAreaView } from 'react-native-safe-area-context';

const { width } = Dimensions.get('window');
const ALBUM_ART_SIZE = width * 0.8;

export default function PlayerModal({ navigation }) {
    const { currentTrack, isPlaying, queue, currentIndex, isShuffle, repeatMode } = useSelector((state) => state.player);
    const { backendUrl } = useSelector((state) => state.settings);
    const dispatch = useDispatch();

    const [position, setPosition] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isSliding, setIsSliding] = useState(false);
    const [isFetching, setIsFetching] = useState(false);

    const rotation = useSharedValue(0);
    const scale = useSharedValue(1);

    useEffect(() => {
        if (isPlaying) {
            rotation.value = withRepeat(
                withTiming(360, { duration: 15000, easing: Easing.linear }),
                -1,
                false
            );
            scale.value = withSpring(1);
        } else {
            scale.value = withSpring(0.9);
        }
    }, [isPlaying]);

    useEffect(() => {
        const instance = getPlaybackInstance();
        if (instance) {
            instance.setOnPlaybackStatusUpdate((status) => {
                if (status.isLoaded && !isSliding) {
                    setPosition(status.positionMillis);
                    setDuration(status.durationMillis || 0);
                    if (status.didJustFinish) {
                        handleNext();
                    }
                }
            });
        }
    }, [currentTrack, isSliding, repeatMode, currentIndex, queue]);

    const handlePlayIndex = async (index) => {
        if (isFetching || !queue[index]) return;

        try {
            setIsFetching(true);
            const item = queue[index];
            const streamData = await fetchStreamWithRetry(item);

            const track = {
                id: item.id,
                url: streamData.stream_url,
                title: item.title,
                artist: item.artist,
                artwork: getThumbnailUrl({ ...item, thumbnail: streamData.thumbnail }),
                duration: item.duration || streamData.duration,
            };

            dispatch(setTrack(track));
            dispatch(setCurrentIndex(index));
            dispatch(setPlaying(true));

            await playTrack(track);
        } catch (error) {
            console.error('Playback error:', error);
        } finally {
            setIsFetching(false);
        }
    };

    const handleNext = () => {
        if (repeatMode === 'one') {
            seekTo(0);
            return;
        }
        let nextIndex = currentIndex + 1;
        if (isShuffle) {
            nextIndex = Math.floor(Math.random() * queue.length);
        } else if (nextIndex >= queue.length) {
            if (repeatMode === 'all') {
                nextIndex = 0;
            } else {
                dispatch(setPlaying(false));
                return;
            }
        }
        handlePlayIndex(nextIndex);
    };

    const handlePrevious = () => {
        let prevIndex = currentIndex - 1;
        if (prevIndex < 0) {
            if (repeatMode === 'all') {
                prevIndex = queue.length - 1;
            } else {
                prevIndex = 0;
            }
        }
        handlePlayIndex(prevIndex);
    };

    const animatedArtStyle = useAnimatedStyle(() => ({
        transform: [
            { rotate: `${rotation.value}deg` },
            { scale: scale.value }
        ],
    }));

    const formatTime = (millis) => {
        if (!millis) return "0:00";
        const totalSeconds = millis / 1000;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = Math.floor(totalSeconds % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    if (!currentTrack) return null;

    return (
        <SafeAreaView className="flex-1 bg-vortex-obsidian">
            {/* Background Image */}
            <Image
                source={{ uri: currentTrack.artwork }}
                className="absolute w-full h-full opacity-20"
                blurRadius={40}
            />

            {/* Header */}
            <View className="flex-row justify-between px-6 py-4 items-center">
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <ChevronDown size={30} color="white" />
                </TouchableOpacity>
                <Text className="text-white text-xs font-bold uppercase tracking-widest opacity-70">
                    {isFetching ? "Preparing track..." : "Now Playing"}
                </Text>
                <TouchableOpacity>
                    <Share2 size={24} color="white" />
                </TouchableOpacity>
            </View>

            {/* Album Art */}
            <View className="flex-1 items-center justify-center">
                <Animated.View
                    style={[
                        { width: ALBUM_ART_SIZE, height: ALBUM_ART_SIZE },
                        animatedArtStyle
                    ]}
                    className="rounded-full overflow-hidden shadow-2xl shadow-black border-2 border-vortex-surface"
                >
                    <Image source={{ uri: currentTrack.artwork }} className="w-full h-full" />
                </Animated.View>
            </View>

            {/* Info & Controls */}
            <View className="px-8 pb-10">
                <View className="mb-6">
                    <Text className="text-white text-2xl font-bold" numberOfLines={1}>{currentTrack.title}</Text>
                    <Text className="text-vortex-saffron text-lg font-medium mb-4 opacity-90">{currentTrack.artist}</Text>

                    {/* Progress Slider */}
                    <Slider
                        style={{ width: '100%', height: 40 }}
                        minimumValue={0}
                        maximumValue={duration || 1000}
                        value={position}
                        minimumTrackTintColor="#FF9933"
                        maximumTrackTintColor="#333333"
                        thumbTintColor="#FF9933"
                        onSlidingStart={() => setIsSliding(true)}
                        onSlidingComplete={async (value) => {
                            await seekTo(value);
                            setIsSliding(false);
                        }}
                    />
                    <View className="flex-row justify-between -mt-2">
                        <Text className="text-vortex-textSecondary text-xs font-medium">{formatTime(position)}</Text>
                        <Text className="text-vortex-textSecondary text-xs font-medium">{formatTime(duration)}</Text>
                    </View>
                </View>

                {/* Main Controls */}
                <View className="flex-row items-center justify-between mb-8">
                    <TouchableOpacity onPress={() => dispatch(toggleShuffle())}>
                        <Shuffle size={24} color={isShuffle ? "#FF9933" : "#A0A0A0"} />
                    </TouchableOpacity>
                    <TouchableOpacity onPress={handlePrevious}>
                        <SkipBack size={36} color="white" fill="white" />
                    </TouchableOpacity>
                    <TouchableOpacity
                        className="w-20 h-20 bg-vortex-saffron rounded-full items-center justify-center shadow-lg shadow-vortex-saffron"
                        disabled={isFetching}
                        onPress={async () => {
                            const newPlaying = !isPlaying;
                            dispatch(setPlaying(newPlaying));
                            await togglePlayback(newPlaying);
                        }}
                    >
                        {isPlaying ? <Pause size={40} color="black" fill="black" /> : <Play size={40} color="black" fill="black" />}
                    </TouchableOpacity>
                    <TouchableOpacity onPress={handleNext}>
                        <SkipForward size={36} color="white" fill="white" />
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => dispatch(toggleRepeatMode())}>
                        <View className="relative">
                            <Repeat size={24} color={repeatMode !== 'off' ? "#FF9933" : "#A0A0A0"} />
                            {repeatMode === 'one' && <Text style={{ position: 'absolute', top: 6, left: 9, fontSize: 8, color: '#FF9933', fontWeight: 'bold' }}>1</Text>}
                        </View>
                    </TouchableOpacity>
                </View>

                <View className="flex-row justify-between items-center opacity-80">
                    <TouchableOpacity><Heart size={26} color="#FF9933" /></TouchableOpacity>
                    <Text className="text-vortex-textSecondary text-sm font-semibold">LYRICS</Text>
                    <TouchableOpacity><MoreVertical size={24} color="white" /></TouchableOpacity>
                </View>
            </View>
        </SafeAreaView>
    );
}
