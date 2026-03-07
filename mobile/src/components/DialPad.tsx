import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface DialPadProps {
  onPress: (digit: string) => void;
  onDelete: () => void;
}

const KEYS = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  ['*', '0', '#'],
];

const SUB_LABELS: Record<string, string> = {
  '2': 'ABC',
  '3': 'DEF',
  '4': 'GHI',
  '5': 'JKL',
  '6': 'MNO',
  '7': 'PQRS',
  '8': 'TUV',
  '9': 'WXYZ',
  '0': '+',
};

export default function DialPad({ onPress, onDelete }: DialPadProps) {
  return (
    <View style={styles.container}>
      {KEYS.map((row, rowIdx) => (
        <View key={rowIdx} style={styles.row}>
          {row.map((digit) => (
            <TouchableOpacity
              key={digit}
              style={styles.key}
              onPress={() => onPress(digit)}
              onLongPress={digit === '0' ? () => onPress('+') : undefined}
            >
              <Text style={styles.digit}>{digit}</Text>
              {SUB_LABELS[digit] ? (
                <Text style={styles.subLabel}>{SUB_LABELS[digit]}</Text>
              ) : null}
            </TouchableOpacity>
          ))}
        </View>
      ))}
      <View style={styles.row}>
        <View style={styles.key} />
        <View style={styles.key} />
        <TouchableOpacity style={styles.key} onPress={onDelete}>
          <Text style={styles.deleteText}>DEL</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 32 },
  row: { flexDirection: 'row', justifyContent: 'center', marginBottom: 12 },
  key: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 12,
  },
  digit: { color: '#F8FAFC', fontSize: 28, fontWeight: '500' },
  subLabel: { color: '#64748B', fontSize: 10, marginTop: -2, letterSpacing: 2 },
  deleteText: { color: '#94A3B8', fontSize: 14, fontWeight: '600' },
});
