/**
 * In-memory cache + background preloading for map overlay images.
 *
 * Changing the date used to download a new image every time, which takes about a
 * second on a hosted server far away. Images are now kept in memory (as object
 * URLs), and once the visible day is shown the other days for the same depth and
 * layer are preloaded in the background, nearest days first. Scrubbing the time
 * slider or pressing Play then shows images that are already in the browser.
 */

export interface LoadedImage {
  url: string; // object URL, valid until evicted
  vmin: number | null; // colour range the server used (temperature layer)
  vmax: number | null;
}

const MAX_ENTRIES = 250; // about 50 KB each as WebP
const PREFETCH_CONCURRENCY = 3;

const cache = new Map<string, Promise<LoadedImage>>(); // insertion order = LRU order
const resolved = new Map<string, LoadedImage>();
const pinned = new Set<string>(); // currently on screen, never evicted

function touch(key: string) {
  const p = cache.get(key);
  if (p) {
    cache.delete(key);
    cache.set(key, p);
  }
}

function evict() {
  for (const key of cache.keys()) {
    if (cache.size <= MAX_ENTRIES) break;
    if (pinned.has(key)) continue;
    const img = resolved.get(key);
    if (img) URL.revokeObjectURL(img.url);
    resolved.delete(key);
    cache.delete(key);
  }
}

/** Download (or reuse) one image. `url` is the cache key. */
export function loadImage(url: string): Promise<LoadedImage> {
  const hit = cache.get(url);
  if (hit) {
    touch(url);
    return hit;
  }
  const p = fetch(url).then(async (res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const vmin = parseFloat(res.headers.get('X-Vmin') ?? '');
    const vmax = parseFloat(res.headers.get('X-Vmax') ?? '');
    const img: LoadedImage = {
      url: URL.createObjectURL(await res.blob()),
      vmin: isFinite(vmin) ? vmin : null,
      vmax: isFinite(vmax) ? vmax : null,
    };
    resolved.set(url, img);
    return img;
  });
  p.catch(() => cache.delete(url)); // allow a retry after a failure
  cache.set(url, p);
  evict();
  return p;
}

/** Mark the image on screen so eviction never revokes it. */
export function pinImage(url: string) {
  pinned.clear();
  pinned.add(url);
}

let prefetchGeneration = 0;

/**
 * Preload `urls` in the background with limited concurrency. A newer call cancels
 * the remaining work of an older one (e.g. when the depth or layer changes).
 */
export function prefetchImages(urls: string[]) {
  const generation = ++prefetchGeneration;
  const queue = urls.filter((u) => !cache.has(u));
  const worker = async () => {
    while (queue.length && generation === prefetchGeneration) {
      const next = queue.shift()!;
      try {
        await loadImage(next);
      } catch {
        /* skipped; it will be fetched on demand */
      }
    }
  };
  for (let i = 0; i < PREFETCH_CONCURRENCY; i++) void worker();
}

/** Dates ordered by distance from `center` (nearest first), for preloading. */
export function nearestFirst(dates: string[], center: string, limit = 120): string[] {
  const i0 = Math.max(0, dates.indexOf(center));
  const out: string[] = [];
  for (let d = 1; out.length < Math.min(limit, dates.length - 1) && d < dates.length; d++) {
    if (i0 + d < dates.length) out.push(dates[i0 + d]);
    if (i0 - d >= 0) out.push(dates[i0 - d]);
  }
  return out.slice(0, limit);
}
