import React from 'react';
import { View, Text, FlatList, TouchableOpacity, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Folder, Heart, Plus, ListMusic, List } from 'lucide-react-native';
import { useSelector } from 'react-redux';

const LibraryItem = ({ title, subtitle, icon: Icon, color }) => (
    <TouchableOpacity className="flex-row items-center mb-6 px-6">
        <View className="w-16 h-16 rounded-xl items-center justify-center" style={{ backgroundColor: color || '#1A1A1A' }}>
            {Icon ? <Icon size={30} color="white" /> : <ListMusic size={30} color="white" />}
        </View>
        <View className="ml-4 flex-1">
            <Text className="text-white text-lg font-bold">{title}</Text>
            <Text className="text-vortex-textSecondary text-sm">{subtitle}</Text>
        </View>
    </TouchableOpacity>
);

export default function LibraryScreen() {
    const { likedSongs, playlists } = useSelector((state) => state.library);

    return (
        <SafeAreaView className="flex-1 bg-vortex-obsidian">
            <View className="flex-row justify-between items-center px-6 mt-6 mb-8">
                <Text className="text-white text-3xl font-extrabold">Library</Text>
                <TouchableOpacity>
                    <Plus size={28} color="white" />
                </TouchableOpacity>
            </View>

            <FlatList
                data={[
                    { title: 'Liked Songs', subtitle: `${likedSongs.length} songs`, icon: Heart, color: '#FF9933' },
                    { title: 'My Playlists', subtitle: `${playlists.length} playlists`, icon: ListMusic, color: '#0070FF' },
                    { title: 'Folders', subtitle: '0 folders', icon: Folder, color: '#1A1A1A' },
                    ...playlists.map(p => ({ title: p.name, subtitle: 'Playlist', color: '#1A1A1A' }))
                ]}
                keyExtractor={(item, index) => index.toString()}
                renderItem={({ item }) => (
                    <LibraryItem title={item.title} subtitle={item.subtitle} icon={item.icon} color={item.color} />
                )}
            />
        </SafeAreaView>
    );
}
