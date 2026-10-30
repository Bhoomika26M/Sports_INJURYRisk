import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeftRight, Activity, AlertCircle, Pause, Play } from 'lucide-react';
import { api } from '../api/client';

const metricRows = [
  ['Knee valgus left (max)', 'knee_valgus_left_max', '°'],
  ['Knee valgus right (max)', 'knee_valgus_right_max', '°'],
  ['Lateral trunk lean (max)', 'trunk_lean_lateral_max', '°'],
  ['Movement symmetry', 'movement_symmetry_score', '/100'],
  ['Range of motion', 'range_of_motion_score', '/100'],
];

function displayValue(value, suffix = '') {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))
    ? `${Number(value).toFixed(1)}${suffix}`
    : 'Not analyzed';
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00';
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
}

export default function VideoComparisonView({ videos = [] }) {
  const analyzed = useMemo(() => videos.filter((video) => video.status === 'analyzed' && video.processed_video_path), [videos]);
  const [leftId, setLeftId] = useState('');
  const [rightId, setRightId] = useState('');
  const [leftData, setLeftData] = useState(null);
  const [rightData, setRightData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [playError, setPlayError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [leftDuration, setLeftDuration] = useState(0);
  const [rightDuration, setRightDuration] = useState(0);
  const leftPlayer = useRef(null);
  const rightPlayer = useRef(null);
  const syncLock = useRef(false);

  useEffect(() => {
    if (analyzed.length > 0) {
      setLeftId((current) => {
        const stillValid = analyzed.some(v => String(v.id) === String(current));
        return stillValid ? current : String(analyzed[0].id);
      });
      setRightId((current) => {
        const fallback = analyzed.length > 1 ? String(analyzed[1].id) : String(analyzed[0].id);
        const stillValid = analyzed.some(v => String(v.id) === String(current));
        return (stillValid && current !== String(analyzed[0].id)) ? current : fallback;
      });
    }
  }, [analyzed]);

  useEffect(() => {
    let cancelled = false;
    async function loadComparisons() {
      setError('');
      setLeftData(null);
      setRightData(null);
      if (!leftId || !rightId) return;
      setLoading(true);
      try {
        const [leftBiomechanics, leftRisk, rightBiomechanics, rightRisk] = await Promise.all([
          api.getBiomechanics(leftId), api.getInjuryRisk(leftId),
          api.getBiomechanics(rightId), api.getInjuryRisk(rightId),
        ]);
        if (!cancelled) {
          setLeftData({ biomechanics: leftBiomechanics, risk: leftRisk });
          setRightData({ biomechanics: rightBiomechanics, risk: rightRisk });
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load comparison metrics.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadComparisons();
    return () => { cancelled = true; };
  }, [leftId, rightId]);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setLeftDuration(0);
    setRightDuration(0);
    setPlayError('');
    [leftPlayer.current, rightPlayer.current].forEach((player) => {
      if (player) {
        player.pause();
        player.currentTime = 0;
      }
    });
  }, [leftId, rightId]);

  const selectedVideo = (id) => videos.find((video) => String(video.id) === String(id));
  const coverageLabel = (data) => {
    const frames = data?.biomechanics?.time_series_data || [];
    if (!frames.length) return 'Unavailable';
    const detected = frames.filter((frame) => frame?.detected).length;
    return `${Math.round((detected / frames.length) * 100)}% (${detected}/${frames.length})`;
  };
  const leftVideo = selectedVideo(leftId);
  const rightVideo = selectedVideo(rightId);
  const duration = leftDuration > 0 && rightDuration > 0
    ? Math.min(leftDuration, rightDuration)
    : Math.min(Number(leftVideo?.duration_seconds) || 0, Number(rightVideo?.duration_seconds) || 0);

  const syncPlayers = (time) => {
    const boundedTime = Math.max(0, Math.min(time, duration || time));
    setCurrentTime(boundedTime);
    syncLock.current = true;
    [leftPlayer.current, rightPlayer.current].forEach((player) => {
      if (player && Math.abs(player.currentTime - boundedTime) > 0.08) player.currentTime = boundedTime;
    });
    window.setTimeout(() => { syncLock.current = false; }, 0);
  };

  const togglePlayback = async () => {
    const p1 = leftPlayer.current;
    const p2 = rightPlayer.current;
    if (!p1 || !p2) return;
    if (!leftVideo?.processed_video_path || !rightVideo?.processed_video_path) {
      setPlayError('Both sessions must have a completed pose overlay video to play.');
      return;
    }
    setPlayError('');
    if (isPlaying) {
      p1.pause();
      p2.pause();
      setIsPlaying(false);
      return;
    }
    if (duration > 0 && currentTime >= duration) {
      syncPlayers(0);
    } else {
      syncPlayers(currentTime);
    }
    try {
      await Promise.all([p1.play(), p2.play()]);
      setIsPlaying(true);
    } catch {
      p1.pause();
      p2.pause();
      setIsPlaying(false);
      setPlayError('Synchronized playback could not start. Please ensure both overlay videos are reachable.');
    }
  };

  const handleLeftTimeUpdate = () => {
    if (syncLock.current || !leftPlayer.current) return;
    const time = leftPlayer.current.currentTime;
    if (duration > 0 && time >= duration) {
      [leftPlayer.current, rightPlayer.current].forEach((player) => player?.pause());
      setCurrentTime(duration);
      setIsPlaying(false);
      return;
    }
    setCurrentTime(time);
    const right = rightPlayer.current;
    if (right && Math.abs(right.currentTime - time) > 0.12) right.currentTime = Math.min(time, right.duration || time);
  };

  const handleSeek = (event) => {
    syncPlayers(Number(event.target.value));
  };

  const selected = (videoId) => String(videoId) === String(leftId) || String(videoId) === String(rightId);

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-teal-50 p-2.5 text-teal-800"><ArrowLeftRight className="h-5 w-5" /></div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Movement Comparison</h1>
            <p className="mt-1 text-sm text-slate-600">Compare two analyzed sessions side by side. The shared controls keep both overlay videos at the same playback time.</p>
          </div>
        </div>
      </div>

      {analyzed.length < 2 ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Upload and analyze at least two videos to compare them here. Videos without a completed pose overlay are not included.
        </div>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {[
              { label: 'Session A', id: leftId, setId: setLeftId, otherId: rightId, video: leftVideo, playerRef: leftPlayer, durationSetter: setLeftDuration, timeUpdate: handleLeftTimeUpdate },
              { label: 'Session B', id: rightId, setId: setRightId, otherId: leftId, video: rightVideo, playerRef: rightPlayer, durationSetter: setRightDuration, timeUpdate: () => {} },
            ].map(({ label, id, setId, otherId, video, playerRef, durationSetter, timeUpdate }) => (
              <article key={label} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="p-4">
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-600">{label}</label>
                  <select value={id} onChange={(event) => setId(event.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
                    {analyzed.map((option) => <option key={option.id} value={option.id} disabled={String(option.id) === String(otherId)}>{option.title} — {option.activity_type}</option>)}
                  </select>
                </div>
                {video && (
                  <>
                    <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-200">
                      <video
                        key={video.id}
                        ref={playerRef}
                        muted
                        controls
                        playsInline
                        preload="auto"
                        className="h-full w-full object-contain"
                        src={`/api/videos/${video.id}/processed_stream`}
                        onLoadedMetadata={(event) => {
                          durationSetter(event.currentTarget.duration);
                          if (event.currentTarget.currentTime === 0) {
                            try { event.currentTarget.currentTime = 0.01; } catch {}
                          }
                        }}
                        onTimeUpdate={timeUpdate}
                        onEnded={() => {
                          leftPlayer.current?.pause();
                          rightPlayer.current?.pause();
                          setIsPlaying(false);
                        }}
                        onError={() => {
                          setPlayError(`Pose overlay video is unavailable for ${label} (${video.title}). Please ensure analysis has run successfully.`);
                        }}
                      />
                      <span className="absolute left-3 top-3 rounded-md bg-slate-900/80 px-2 py-1 text-[11px] font-medium text-white shadow-xs">
                        Pose overlay
                      </span>
                    </div>
                    <div className="p-4">
                      <p className="font-semibold text-slate-900">{video.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{video.activity_type} · {video.duration_seconds}s · {video.resolution}</p>
                    </div>
                  </>
                )}
              </article>
            ))}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" onClick={togglePlayback} className="inline-flex items-center gap-2 rounded-lg bg-teal-800 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-900">
                {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                {isPlaying ? 'Pause both' : 'Play both'}
              </button>
              <span className="min-w-28 font-mono text-xs text-slate-600">{formatTime(currentTime)} / {formatTime(duration)}</span>
              <input aria-label="Seek both comparison videos" type="range" min="0" max={duration || 0} step="0.01" value={Math.min(currentTime, duration || currentTime)} onChange={handleSeek} disabled={!duration} className="min-w-48 flex-1 accent-teal-700" />
              <span className="text-xs text-slate-500">Synchronized playback</span>
            </div>
            {playError && <p role="alert" className="mt-3 text-sm text-rose-700">{playError}</p>}
          </div>

          {error && <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"><AlertCircle className="h-4 w-4" />{error}</div>}
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3"><Activity className="h-4 w-4 text-teal-700" /><h2 className="font-semibold text-slate-900">Measured comparison</h2></div>
            {loading ? <p className="p-4 text-sm text-slate-600">Loading results…</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-600"><tr><th className="px-4 py-3">Measure</th><th className="px-4 py-3">Session A</th><th className="px-4 py-3">Session B</th></tr></thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr><th className="px-4 py-3 font-medium text-slate-700">Rule-based risk score</th><td className="px-4 py-3">{displayValue(leftData?.risk?.overall_injury_risk_score, '/100')}</td><td className="px-4 py-3">{displayValue(rightData?.risk?.overall_injury_risk_score, '/100')}</td></tr>
                    <tr><th className="px-4 py-3 font-medium text-slate-700">Pose detection coverage</th><td className="px-4 py-3">{coverageLabel(leftData)}</td><td className="px-4 py-3">{coverageLabel(rightData)}</td></tr>
                    <tr><th className="px-4 py-3 font-medium text-slate-700">Risk category</th><td className="px-4 py-3">{leftData?.risk?.risk_category || 'Not analyzed'}</td><td className="px-4 py-3">{rightData?.risk?.risk_category || 'Not analyzed'}</td></tr>
                    {metricRows.map(([label, key, suffix]) => <tr key={key}><th className="px-4 py-3 font-medium text-slate-700">{label}</th><td className="px-4 py-3">{displayValue(leftData?.biomechanics?.metrics?.[key], suffix)}</td><td className="px-4 py-3">{displayValue(rightData?.biomechanics?.metrics?.[key], suffix)}</td></tr>)}
                  </tbody>
                </table>
              </div>
            )}
            <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">Compare pose coverage before interpreting scores. These rule-based estimates are descriptive software outputs, not a diagnosis or validated injury prediction.</p>
          </div>
        </>
      )}
    </section>
  );
}