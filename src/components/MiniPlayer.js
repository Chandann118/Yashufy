import React from 'react';
import { View, Text, TouchableOpacity, Pressable } from 'react-native';
import { Image } from 'expo-image';
import { useSelector, useDispatch } from 'react-redux';
import { Play, Pause, SkipForward, Heart } from 'lucide-react-native';
import { setPlaying } from '../store/playerSlice';
import { togglePlayback } from '../services/audioService';
import { useNavigation } from '@react-navigation/native';
import Animated, { FadeInDown, FadeOutDown } from 'react-native-reanimated';
import { BlurView } from 'expo-blur';

export default function MiniPlayer() {
    const { currentTrack, isPlaying } = useSelector((state) => state.player);
    const dispatch = useDispatch();
    const navigation = useNavigation();

    if (!currentTrack) return null;

    return (
        <Animated.View
            entering={FadeInDown}
            exiting={FadeOutDown}
            className="absolute bottom-[90px] left-2 right-2 h-16 bg-vortex-surface/95 rounded-xl border border-vortex-saffron/20 flex-row items-center px-3 z-50 overflow-hidden"
            style={{ elevation: 10, shadowColor: '#FF9933', shadowOpacity: 0.2, shadowRadius: 10 }}
        >
            <BlurView intensity={20} className="absolute inset-0" />

            <Pressable
                className="flex-row items-center flex-1"
                onPress={() => navigation.navigate('Player')}
            >
                <Image source={{ uri: currentTrack.artwork }} className="w-12 h-12 rounded-lg" />
                <View className="ml-3 flex-1">
                    <Text className="text-white font-bold text-sm" numberOfLines={1}>{currentTrack.title}</Text>
                    <Text className="text-vortex-saffron text-xs font-medium" numberOfLines={1}>{currentTrack.artist}</Text>
                </View>
            </Pressable>

            <View className="flex-row items-center space-x-4">
                <TouchableOpacity className="p-2">
                    <Heart size={20} color="#A0A0A0" />
                </TouchableOpacity>
                <TouchableOpacity
                    className="p-2 bg-vortex-obsidian rounded-full"
                    onPress={async () => {
                        const newPlaying = !isPlaying;
                        dispatch(setPlaying(newPlaying));
                        await togglePlayback(newPlaying);
                    }}
                >
                    {isPlaying ? <Pause size={24} color="#FF9933" fill="#FF9933" /> : <Play size={24} color="#FF9933" fill="#FF9933" />}
                </TouchableOpacity>
                <TouchableOpacity className="p-2">
                    <SkipForward size={24} color="white" />
                </TouchableOpacity>
            </View>

            {/* Progress Bar (Mini) */}
            <View className="absolute bottom-0 left-0 h-[2px] bg-vortex-blue w-[40%] rounded-full" />
        </Animated.View>
    );
}
