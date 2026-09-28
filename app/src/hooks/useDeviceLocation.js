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
  const [attempt, setAttempt] = useState(0);
  const subRef = useRef(null);

  const start = useCallback(() => setStarted(true), []);
  // Re-runs the effect below even though `started` is already true, so a
  // failed/timed-out attempt can be retried without a full remount.
  const retry = useCallback(() => {
    setError(null);
    setAttempt((a) => a + 1);
  }, []);

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
        // getCurrentPositionAsync has no built-in timeout. On web (especially
        // Windows Chrome), if OS-level Location Services are off, the browser's
        // geolocation call can hang forever with no error at all -- observed
        // directly on the deployed Vercel build. Race it against a real
        // timeout so the user gets an actionable message instead of an
        // infinite "Waiting for your location..." spinner.
        const initial = await Promise.race([
          Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error("TIMEOUT")), 15000)
          ),
        ]);
        if (mounted) setLocation(initial);
      } catch (e) {
        if (!mounted) return;
        if (String(e).includes("TIMEOUT")) {
          setError(
            "Couldn't get your location after 15s. Check that Location Services are turned on " +
              "for this device/browser, then try again."
          );
        } else {
          setError(String(e));
        }
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
  }, [started, watch, attempt]);

  return { location, error, permissionGranted, start, retry, awaitingStart: requireManualStart && !started };
}
