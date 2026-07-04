import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { WebView } from 'react-native-webview';

const TABS = [
  {
    key: 'system',
    label: '管理システム',
    icon: '🏗️',
    url: 'https://e2j4hnwswmmt4gqrzsbbdc.streamlit.app/',
  },
  {
    key: 'ledger',
    label: '橋梁台帳',
    icon: '📋',
    url: 'https://yoshiharu57.github.io/-/ledger/',
  },
];

export default function App() {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const webViewRefs = useRef([]);

  const currentTab = TABS[activeTab];

  const handleTabPress = (index) => {
    if (index !== activeTab) {
      setActiveTab(index);
      setLoading(true);
    }
  };

  const handleNavBack = () => {
    webViewRefs.current[activeTab]?.goBack();
  };

  const handleNavForward = () => {
    webViewRefs.current[activeTab]?.goForward();
  };

  const handleReload = () => {
    setLoading(true);
    webViewRefs.current[activeTab]?.reload();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🌉 橋梁管理システム</Text>
      </View>

      {/* Tab Bar */}
      <View style={styles.tabBar}>
        {TABS.map((tab, index) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === index && styles.tabActive]}
            onPress={() => handleTabPress(index)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[styles.tabLabel, activeTab === index && styles.tabLabelActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* WebViews (rendered for both tabs to preserve state) */}
      <View style={styles.webViewContainer}>
        {TABS.map((tab, index) => (
          <WebView
            key={tab.key}
            ref={(ref) => { webViewRefs.current[index] = ref; }}
            source={{ uri: tab.url }}
            style={[styles.webView, activeTab !== index && styles.hidden]}
            onLoadStart={() => { if (activeTab === index) setLoading(true); }}
            onLoadEnd={() => { if (activeTab === index) setLoading(false); }}
            onError={() => { if (activeTab === index) setLoading(false); }}
            javaScriptEnabled
            domStorageEnabled
            allowsInlineMediaPlayback
            mediaPlaybackRequiresUserAction={false}
            userAgent={
              Platform.OS === 'android'
                ? 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36'
                : 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17 Mobile Safari/604.1'
            }
          />
        ))}

        {/* Loading overlay */}
        {loading && (
          <View style={styles.loadingOverlay}>
            <Text style={styles.loadingEmoji}>🌉</Text>
            <ActivityIndicator size="large" color="#1e3a5f" style={{ marginTop: 16 }} />
            <Text style={styles.loadingText}>読み込み中...</Text>
          </View>
        )}
      </View>

      {/* Navigation Bar */}
      <View style={styles.navBar}>
        <TouchableOpacity style={styles.navBtn} onPress={handleNavBack}>
          <Text style={styles.navBtnText}>◀</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.navBtn} onPress={handleReload}>
          <Text style={styles.navBtnText}>⟳</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.navBtn} onPress={handleNavForward}>
          <Text style={styles.navBtnText}>▶</Text>
        </TouchableOpacity>
        <View style={styles.urlBar}>
          <Text style={styles.urlText} numberOfLines={1}>{currentTab.url}</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const HEADER_BG = '#1e3a5f';
const TAB_BG = '#f1f5f9';
const TAB_ACTIVE_BG = '#1e3a5f';

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: HEADER_BG,
  },
  header: {
    backgroundColor: HEADER_BG,
    paddingVertical: 10,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  headerTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: TAB_BG,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    gap: 6,
    borderBottomWidth: 3,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: HEADER_BG,
    backgroundColor: '#ffffff',
  },
  tabIcon: {
    fontSize: 16,
  },
  tabLabel: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '500',
  },
  tabLabelActive: {
    color: HEADER_BG,
    fontWeight: '700',
  },
  webViewContainer: {
    flex: 1,
    position: 'relative',
  },
  webView: {
    flex: 1,
  },
  hidden: {
    position: 'absolute',
    width: 0,
    height: 0,
    opacity: 0,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#f8fafc',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingEmoji: {
    fontSize: 56,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#64748b',
  },
  navBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f1f5f9',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingHorizontal: 8,
    paddingVertical: 6,
    gap: 4,
  },
  navBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#e2e8f0',
  },
  navBtnText: {
    fontSize: 14,
    color: '#1e3a5f',
    fontWeight: 'bold',
  },
  urlBar: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  urlText: {
    fontSize: 11,
    color: '#64748b',
  },
});
