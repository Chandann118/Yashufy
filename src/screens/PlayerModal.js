import React, { useEffect } from 'react';
import { View, Text, TouchableOpacity, Dimensions } from 'react-native';
import { Image } from 'expo-image';
import { useSelector, useDispatch } from 'react-redux';
import Animated, {
    useSharedValue,
    useAnimatedStyle,
    withRepeat,
    withTiming,
    Easing,
    interpolate,
    withSpring
} from 'react-native-reanimated';
import { Play, Pause, SkipForward, SkipBack, ChevronDown, Heart, Share2, Shuffle, Repeat, MoreVertical } from 'lucide-react-native';
import { setPlaying } from '../store/playerSlice';
import { togglePlayback } from '../services/audioService';
import { BlurView } from 'expo-blur';
import { SafeAreaView } from 'react-native-safe-area-context';

const { width } = Dimensions.get('window');
const ALBUM_ART_SIZE = width * 0.8;

export default function PlayerModal({ navigation }) {
    const { currentTrack, isPlaying } = useSelector((state) => state.player);
    const dispatch = useDispatch();

    const rotation = useSharedValue(0);
    const scale = useSharedValue(1);

    useEffect(() => {
        if (isPlaying) {
            rotation.value = withRepeat(
                withTiming(360, { duration: 10000, easing: Easing.linear }),
                -1,
                false
            );
            scale.value = withSpring(1);
        } else {
            rotation.value = 0;
            scale.value = withSpring(0.9);
        }
    }, [isPlaying]);

    const animatedArtStyle = useAnimatedStyle(() => ({
        transform: [
            { rotate: `${rotation.value}deg` },
            { scale: scale.value }
        ],
    }));

    if (!currentTrack) return null;

    return (
        <SafeAreaView className="flex-1 bg-vortex-obsidian">
            {/* Background Image (Blurred) */}
            <Image
                source={{ uri: currentTrack.artwork }}
                className="absolute w-full h-full opacity-30"
                blurRadius={50}
            />

            {/* Header */}
            <View className="flex-row justify-between px-6 py-4 items-center">
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <ChevronDown size={30} color="white" />
                </TouchableOpacity>
                <Text className="text-white text-sm font-bold uppercase tracking-widest">Now Playing</Text>
                <TouchableOpacity>
                    <Share2 size={24} color="white" />
                </TouchableOpacity>
            </View>

            {/* Album Art */}
            <View className="flex-1 items-center justify-center mt-10">
                <Animated.View
                    style={[
                        { width: ALBUM_ART_SIZE, height: ALBUM_ART_SIZE },
                        animatedArtStyle
                    ]}
                    className="rounded-full overflow-hidden shadow-2xl shadow-vortex-saffron border-4 border-vortex-surface"
                >
                    <Image source={{ uri: currentTrack.artwork }} className="w-full h-full" />
                </Animated.View>
            </View>

            {/* Info & Controls */}
            <View className="px-10 pb-16">
                <View className="mb-8">
                    <Text className="text-white text-3xl font-extrabold" numberOfLines={1}>{currentTrack.title}</Text>
                    <Text className="text-vortex-saffron text-lg font-semibold mb-4">{currentTrack.artist}</Text>

                    {/* Progress Bar Placeholder */}
                    <View className="h-1 bg-vortex-surface rounded-full w-full overflow-hidden mt-4">
                        <View className="h-full bg-vortex-blue w-[40%] rounded-full" />
                    </View>
                    <View className="flex-row justify-between mt-2">
                        <Text className="text-vortex-textSecondary text-xs">1:45</Text>
                        <Text className="text-vortex-textSecondary text-xs">4:20</Text>
                    </View>
                </View>

                {/* Main Controls */}
                <View className="flex-row items-center justify-between mb-10">
                    <Shuffle size={20} color="#A0A0A0" />
                    <SkipBack size={32} color="white" fill="white" />
                    <TouchableOpacity
                        className="w-20 h-20 bg-vortex-saffron rounded-full items-center justify-center shadow-lg shadow-vortex-saffron"
                        onPress={async () => {
                            const newPlaying = !isPlaying;
                            dispatch(setPlaying(newPlaying));
                            await togglePlayback(newPlaying);
                        }}
                    >
                        {isPlaying ? <Pause size={40} color="black" fill="black" /> : <Play size={40} color="black" fill="black" />}
                    </TouchableOpacity>
                    <SkipForward size={32} color="white" fill="white" />
                    <Repeat size={20} color="#A0A0A0" />
                </View>

                <View className="flex-row justify-between items-center">
                    <Heart size={24} color="#FF9933" />
                    <Text className="text-vortex-textSecondary text-sm">Lyrics</Text>
                    <MoreVertical size={24} color="white" />
                </View>
            </View>
        </SafeAreaView>
    );
}
