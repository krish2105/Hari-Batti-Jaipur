// Placeholder screen. The real rider/driver app (countdown, voice speed advice) is built in P6.
// Safety: the app will never say "go"; speed advice is capped at the limit minus 5 km/h.
import { StatusBar } from "expo-status-bar";
import { StyleSheet, Text, View } from "react-native";
import { DATA_SOURCE_LABELS } from "@haribatti/core";
import { sourceBadgeColours } from "@haribatti/ui";

export default function App() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>HariBatti</Text>
      <Text>Mansarovar corridor, J01–J08. Placeholder — built in P6.</Text>
      <Text style={[styles.badge, { backgroundColor: sourceBadgeColours.SIM }]}>{DATA_SOURCE_LABELS.SIM}</Text>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24 },
  title: { fontSize: 28, fontWeight: "700" },
  badge: { color: "#fff", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, overflow: "hidden" },
});
