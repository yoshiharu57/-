import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  SafeAreaView,
  Platform,
  Linking,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { WebView } from 'react-native-webview';

const STREAMLIT_URL = 'https://e2j4hnwswmmt4gqrzsbbdc.streamlit.app/';
const LEDGER_URL = 'https://yoshiharu57.github.io/-/ledger/';

const TABS = [
  { key: 'system', label: '管理システム', icon: '🏗️' },
  { key: 'ledger',  label: '橋梁台帳',    icon: '📋' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState(0);
  const webViewRef = React.useRef(null);

  const openStreamlit = async () => {
    await Linking.openURL(STREAMLIT_URL);
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
            onPress={() => setActiveTab(index)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[styles.tabLabel, activeTab === index && styles.tabLabelActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <View style={styles.content}>
        {activeTab === 0 ? (
          /* 管理システム — ブラウザで開く */
          <View style={styles.launchScreen}>
            <Text style={styles.bridgeEmoji}>🌉</Text>
            <Text style={styles.launchTitle}>橋梁管理システム</Text>
            <Text style={styles.launchDesc}>
              点検記録・健全度管理・書類管理を一元化したシステムです。
            </Text>
            <TouchableOpacity style={styles.openBtn} onPress={openStreamlit}>
              <Text style={styles.openBtnText}>🌐 ブラウザで開く</Text>
            </TouchableOpacity>
            <Text style={styles.launchNote}>
              ※ タップするとスマホのブラウザが起動します
            </Text>
          </View>
        ) : (
          /* 橋梁台帳 — WebView */
          <View style={styles.webViewContainer}>
            <WebView
              ref={webViewRef}
              source={{ uri: LEDGER_URL }}
              style={styles.webView}
              javaScriptEnabled
              domStorageEnabled
              startInLoadingState
              userAgent={
                Platform.OS === 'android'
                  ? 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36'
                  : 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17 Mobile Safari/604.1'
              }
            />
            {/* Nav bar for ledger */}
            <View style={styles.navBar}>
              <TouchableOpacity style={styles.navBtn} onPress={() => webViewRef.current?.goBack()}>
                <Text style={styles.navBtnText}>◀</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.navBtn} onPress={() => webViewRef.current?.reload()}>
                <Text style={styles.navBtnText}>⟳</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.navBtn} onPress={() => webViewRef.current?.goForward()}>
                <Text style={styles.navBtnText}>▶</Text>
              </TouchableOpacity>
              <View style={styles.urlBar}>
                <Text style={styles.urlText} numberOfLines={1}>{LEDGER_URL}</Text>
              </View>
            </View>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const HEADER_BG = '#1e3a5f';

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: HEADER_BG },
  header: {
    backgroundColor: HEADER_BG,
    paddingVertical: 10,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  headerTitle: { color: '#ffffff', fontSize: 18, fontWeight: 'bold' },
  tabBar: { flexDirection: 'row', backgroundColor: '#f1f5f9' },
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
  tabActive: { borderBottomColor: HEADER_BG, backgroundColor: '#ffffff' },
  tabIcon: { fontSize: 16 },
  tabLabel: { fontSize: 14, color: '#64748b', fontWeight: '500' },
  tabLabelActive: { color: HEADER_BG, fontWeight: '700' },
  content: { flex: 1, backgroundColor: '#ffffff' },

  /* 管理システム launch screen */
  launchScreen: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  bridgeEmoji: { fontSize: 72, marginBottom: 16 },
  launchTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: HEADER_BG,
    marginBottom: 12,
    textAlign: 'center',
  },
  launchDesc: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 32,
  },
  openBtn: {
    backgroundColor: HEADER_BG,
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: 12,
    marginBottom: 16,
  },
  openBtnText: { color: '#ffffff', fontSize: 16, fontWeight: 'bold' },
  launchNote: { fontSize: 12, color: '#94a3b8', textAlign: 'center' },

  /* 橋梁台帳 WebView */
  webViewContainer: { flex: 1 },
  webView: { flex: 1 },
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
  navBtnText: { fontSize: 14, color: HEADER_BG, fontWeight: 'bold' },
  urlBar: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  urlText: { fontSize: 11, color: '#64748b' },
});
