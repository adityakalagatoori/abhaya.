import { useCallback, useEffect, useRef, useState } from "react";
import * as Location from "expo-location";

// Real device GPS via expo-location. Requests real foreground permission
// and streams real coordinates -- no simulated/hardcoded positions.
//
// requireManualStart: when true, the OS permission prompt does NOT fire
// automatically on mount. Instead, `start()` is returned so the caller can
// show an explanatory "why we need this" card first and only trigger the
// real permission dialog when the user taps a button -- see plan item #8
// (permission priming). Defaults to false so existing call sites that don't
// care about priming keep working exactly as before.
export function useDeviceLocation({
  watch = false,
  distanceInterval = 5,
  timeInterval = 2000,
  requireManualStart = false,
} = {}) {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);
  const [permissionGranted, setPermissionGranted] = useState(null);
  const [started, setStarted] = useState(!requireManualStart);
  const subRef = useRef(null);

  const start = useCallback(() => setStarted(true), []);

  useEffect(() => {
    if (!started) return undefined;
    let mounted = true;

    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (!mounted) return;
      setPermissionGranted(status === "granted");
      if (status !== "granted") {
        setError("Location permission denied");
        return;
      }

      try {
        const initial = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        });
        if (mounted) setLocation(initial);
      } catch (e) {
        if (mounted) setError(String(e));
      }

      if (watch) {
        subRef.current = await Location.watchPositionAsync(
          { accuracy: Location.Accuracy.High, distanceInterval, timeInterval },
          (loc) => {
            if (mounted) setLocation(loc);
          }
        );
      }
    })();

    return () => {
      mounted = false;
      if (subRef.current) subRef.current.remove();
    };
  }, [started, watch]);

  return { location, error, permissionGranted, start, awaitingStart: requireManualStart && !started };
}
