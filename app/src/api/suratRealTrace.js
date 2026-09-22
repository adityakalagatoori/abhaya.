// Real recorded GPS trace (Surat, India, 2018-08-29) used as the RouteGuard
// "live ride" vehicle position feed, since there is no real ride-hailing
// integration for the demo. These are real recorded coordinates from
// data/gps_traces/surat_real_trace.csv, replayed at (scaled) real intervals
// -- never fabricated. WalkGuard and turn-by-turn navigation use the actual
// live device GPS instead (see src/hooks/useDeviceLocation.js).
export const SURAT_REAL_TRACE = [
  { lat: 21.2401752, lon: 72.8472829, t: "2018-08-29T03:05:06Z" },
  { lat: 21.2401900, lon: 72.8472807, t: "2018-08-29T03:05:07Z" },
  { lat: 21.2402048, lon: 72.8472746, t: "2018-08-29T03:05:08Z" },
  { lat: 21.2402248, lon: 72.8472718, t: "2018-08-29T03:05:10Z" },
  { lat: 21.2403258, lon: 72.8472494, t: "2018-08-29T03:05:18Z" },
  { lat: 21.2403444, lon: 72.8472450, t: "2018-08-29T03:05:19Z" },
  { lat: 21.2404465, lon: 72.8471980, t: "2018-08-29T03:05:23Z" },
  { lat: 21.2406025, lon: 72.8470977, t: "2018-08-29T03:05:27Z" },
  { lat: 21.2407754, lon: 72.8469736, t: "2018-08-29T03:05:31Z" },
  { lat: 21.2409775, lon: 72.8467928, t: "2018-08-29T03:05:34Z" },
  { lat: 21.2411580, lon: 72.8466369, t: "2018-08-29T03:05:36Z" },
  { lat: 21.2412458, lon: 72.8465522, t: "2018-08-29T03:05:37Z" },
  { lat: 21.2413273, lon: 72.8464646, t: "2018-08-29T03:05:38Z" },
  { lat: 21.2414963, lon: 72.8463133, t: "2018-08-29T03:05:40Z" },
  { lat: 21.2416617, lon: 72.8461637, t: "2018-08-29T03:05:42Z" },
  { lat: 21.2418267, lon: 72.8460106, t: "2018-08-29T03:05:44Z" },
  { lat: 21.2419726, lon: 72.8458832, t: "2018-08-29T03:05:46Z" },
  { lat: 21.2421763, lon: 72.8457210, t: "2018-08-29T03:05:49Z" },
  { lat: 21.2424275, lon: 72.8456752, t: "2018-08-29T03:05:52Z" },
  { lat: 21.2427614, lon: 72.8454856, t: "2018-08-29T03:05:56Z" },
  { lat: 21.2430632, lon: 72.8453000, t: "2018-08-29T03:06:00Z" },
  { lat: 21.2434533, lon: 72.8450457, t: "2018-08-29T03:06:05Z" },
  { lat: 21.2438167, lon: 72.8448284, t: "2018-08-29T03:06:10Z" },
  { lat: 21.2440709, lon: 72.8446300, t: "2018-08-29T03:06:15Z" },
  { lat: 21.2442557, lon: 72.8444919, t: "2018-08-29T03:06:20Z" },
  { lat: 21.2444207, lon: 72.8443600, t: "2018-08-29T03:06:23Z" },
  { lat: 21.2446147, lon: 72.8442420, t: "2018-08-29T03:06:26Z" },
  { lat: 21.2448411, lon: 72.8441104, t: "2018-08-29T03:06:29Z" },
  { lat: 21.2450665, lon: 72.8439604, t: "2018-08-29T03:06:32Z" },
  { lat: 21.2452774, lon: 72.8438309, t: "2018-08-29T03:06:35Z" },
  { lat: 21.2454581, lon: 72.8437081, t: "2018-08-29T03:06:38Z" },
  { lat: 21.2456243, lon: 72.8435882, t: "2018-08-29T03:06:41Z" },
  { lat: 21.2457763, lon: 72.8434600, t: "2018-08-29T03:06:44Z" },
  { lat: 21.2459480, lon: 72.8433266, t: "2018-08-29T03:06:47Z" },
  { lat: 21.2461081, lon: 72.8432253, t: "2018-08-29T03:06:49Z" },
  { lat: 21.2461980, lon: 72.8431707, t: "2018-08-29T03:06:50Z" },
  { lat: 21.2462830, lon: 72.8431267, t: "2018-08-29T03:06:51Z" },
  { lat: 21.2463730, lon: 72.8430794, t: "2018-08-29T03:06:52Z" },
  { lat: 21.2464626, lon: 72.8430617, t: "2018-08-29T03:06:53Z" },
  { lat: 21.2466506, lon: 72.8430315, t: "2018-08-29T03:06:55Z" },
  { lat: 21.2467566, lon: 72.8430487, t: "2018-08-29T03:06:56Z" },
  { lat: 21.2470053, lon: 72.8430462, t: "2018-08-29T03:06:58Z" },
  { lat: 21.2472798, lon: 72.8430646, t: "2018-08-29T03:07:00Z" },
  { lat: 21.2475482, lon: 72.8430885, t: "2018-08-29T03:07:02Z" },
  { lat: 21.2478249, lon: 72.8431225, t: "2018-08-29T03:07:04Z" },
  { lat: 21.2480998, lon: 72.8431606, t: "2018-08-29T03:07:06Z" },
  { lat: 21.2483714, lon: 72.8431959, t: "2018-08-29T03:07:08Z" },
  { lat: 21.2486522, lon: 72.8432315, t: "2018-08-29T03:07:10Z" },
  { lat: 21.2489269, lon: 72.8432790, t: "2018-08-29T03:07:12Z" },
  { lat: 21.2491649, lon: 72.8433102, t: "2018-08-29T03:07:14Z" },
  { lat: 21.2493887, lon: 72.8433326, t: "2018-08-29T03:07:16Z" },
  { lat: 21.2496052, lon: 72.8433268, t: "2018-08-29T03:07:18Z" },
  { lat: 21.2496965, lon: 72.8433114, t: "2018-08-29T03:07:19Z" },
  { lat: 21.2498917, lon: 72.8432599, t: "2018-08-29T03:07:21Z" },
];

// Replays the trace at real relative timestamps, scaled by `speedFactor`
// (e.g. 8x so a ~2.25 min real recording plays out in ~17s for the demo).
// onPoint(point, index) is called for each sample, onComplete() once after
// the last point (so the UI can offer "Continue" instead of leaving the ride
// silently finished with no next step -- see plan item #2). Returns a stop() fn.
export function replayGpsTrace(onPoint, { speedFactor = 6, onComplete } = {}) {
  let stopped = false;
  const timers = [];
  const t0 = new Date(SURAT_REAL_TRACE[0].t).getTime();
  SURAT_REAL_TRACE.forEach((pt, i) => {
    const dtMs = (new Date(pt.t).getTime() - t0) / speedFactor;
    const isLast = i === SURAT_REAL_TRACE.length - 1;
    const timer = setTimeout(() => {
      if (stopped) return;
      onPoint(pt, i);
      if (isLast && onComplete) onComplete();
    }, dtMs);
    timers.push(timer);
  });
  return () => {
    stopped = true;
    timers.forEach(clearTimeout);
  };
}
