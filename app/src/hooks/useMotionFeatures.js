import { useEffect, useRef, useState } from "react";
import { Accelerometer, Gyroscope } from "expo-sensors";

// Real device accelerometer + gyroscope via expo-sensors. Computes the
// coarse WalkGuardEventRequest features (accel_magnitude, accel_variance,
// gyro_magnitude) the backend expects -- from a real sliding window of real
// sensor samples, never simulated numbers.
export function useMotionFeatures({ updateIntervalMs = 200, windowSize = 25 } = {}) {
  const [features, setFeatures] = useState({
    accel_magnitude: 0,
    accel_variance: 0,
    gyro_magnitude: 0,
    impact_detected: false,
    baseline_accel_magnitude: 9.81,
  });
  const [available, setAvailable] = useState(null);

  const accelWindow = useRef([]);
  const gyroLatest = useRef({ x: 0, y: 0, z: 0 });
  const baseline = useRef(null);
  const sampleCount = useRef(0);

  useEffect(() => {
    let accelSub, gyroSub;
    let mounted = true;

    (async () => {
      const accelAvail = await Accelerometer.isAvailableAsync();
      const gyroAvail = await Gyroscope.isAvailableAsync();
      if (!mounted) return;
      setAvailable(accelAvail && gyroAvail);
      if (!accelAvail) return;

      Accelerometer.setUpdateInterval(updateIntervalMs);
      Gyroscope.setUpdateInterval(updateIntervalMs);

      gyroSub = Gyroscope.addListener((g) => {
        gyroLatest.current = g;
      });

      accelSub = Accelerometer.addListener((a) => {
        // magnitude in "g" units from expo-sensors -> convert to m/s^2
        const magG = Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
        const magMs2 = magG * 9.80665;

        const win = accelWindow.current;
        win.push(magMs2);
        if (win.length > windowSize) win.shift();

        sampleCount.current += 1;
        // establish a resting baseline from the first ~2s of real samples
        if (baseline.current === null && sampleCount.current >= 10) {
          baseline.current = win.reduce((s, v) => s + v, 0) / win.length;
        }

        const mean = win.reduce((s, v) => s + v, 0) / win.length;
        const variance =
          win.reduce((s, v) => s + (v - mean) * (v - mean), 0) / Math.max(1, win.length);

        const g2 = gyroLatest.current;
        const gyroMag = Math.sqrt(g2.x * g2.x + g2.y * g2.y + g2.z * g2.z);

        const impact = baseline.current !== null && Math.abs(magMs2 - baseline.current) > 15;

        if (mounted) {
          setFeatures({
            accel_magnitude: magMs2,
            accel_variance: variance,
            gyro_magnitude: gyroMag,
            impact_detected: impact,
            baseline_accel_magnitude: baseline.current ?? 9.81,
          });
        }
      });
    })();

    return () => {
      mounted = false;
      accelSub && accelSub.remove();
      gyroSub && gyroSub.remove();
    };
  }, [updateIntervalMs, windowSize]);

  return { features, available };
}
