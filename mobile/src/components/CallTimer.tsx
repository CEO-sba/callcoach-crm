import React, { useState, useEffect, useRef } from 'react';
import { Text, StyleSheet } from 'react-native';

interface CallTimerProps {
  startTime: number;
  style?: object;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const pad = (n: number) => n.toString().padStart(2, '0');

  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }
  return `${pad(minutes)}:${pad(seconds)}`;
}

export default function CallTimer({ startTime, style }: CallTimerProps) {
  const [elapsed, setElapsed] = useState(Date.now() - startTime);
  const intervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setElapsed(Date.now() - startTime);
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [startTime]);

  return <Text style={[styles.timer, style]}>{formatDuration(elapsed)}</Text>;
}

const styles = StyleSheet.create({
  timer: {
    color: '#F8FAFC',
    fontSize: 48,
    fontWeight: '300',
    fontVariant: ['tabular-nums'],
  },
});
