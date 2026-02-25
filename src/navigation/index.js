import React from 'react';
import { View } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Home, Search, Library, User } from 'lucide-react-native';

// Screens
import HomeScreen from '../screens/HomeScreen';
import SearchScreen from '../screens/SearchScreen';
import LibraryScreen from '../screens/LibraryScreen';
import ProfileScreen from '../screens/ProfileScreen';
import PlayerModal from '../screens/PlayerModal';
import MiniPlayer from '../components/MiniPlayer';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function TabNavigator() {
    return (
        <View style={{ flex: 1 }}>
            <Tab.Navigator
                screenOptions={{
                    headerShown: false,
                    tabBarStyle: {
                        backgroundColor: '#050505',
                        borderTopWidth: 0,
                        height: 90,
                        paddingBottom: 30,
                    },
                    tabBarActiveTintColor: '#FF9933',
                    tabBarInactiveTintColor: '#A0A0A0',
                }}
            >
                <Tab.Screen
                    name="Home"
                    component={HomeScreen}
                    options={{ tabBarIcon: ({ color }) => <Home color={color} size={24} /> }}
                />
                <Tab.Screen
                    name="Search"
                    component={SearchScreen}
                    options={{ tabBarIcon: ({ color }) => <Search color={color} size={24} /> }}
                />
                <Tab.Screen
                    name="Library"
                    component={LibraryScreen}
                    options={{ tabBarIcon: ({ color }) => <Library color={color} size={24} /> }}
                />
                <Tab.Screen
                    name="Settings"
                    component={ProfileScreen}
                    options={{ tabBarIcon: ({ color }) => <Settings color={color} size={24} /> }}
                />
            </Tab.Navigator>
            <MiniPlayer />
        </View>
    );
}

export default function RootNavigator() {
    return (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
            <Stack.Screen name="Tabs" component={TabNavigator} />
            <Stack.Screen
                name="Player"
                component={PlayerModal}
                options={{ presentation: 'modal' }}
            />
        </Stack.Navigator>
    );
}
