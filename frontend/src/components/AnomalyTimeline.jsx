import React from 'react';
import { AlertTriangle, Clock } from 'lucide-react';

function AnomalyTimeline({ anomalies, onSeek }) {
  // Filter out technical data quality logs to show only kinematic/biomechanical anomalies
  const kinematicAnomalies = (anomalies || []).filter(
    (event) => !event.is_data_quality_issue && event.metric !== 'data_quality'
  );

  if (!kinematicAnomalies || kinematicAnomalies.length === 0) {
    return (
      <div className="space-y-4">
        <div>
          <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <AlertTriangle size={20} className="text-amber-400" />
            <span>Kinematic Anomalies Timeline</span>
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">Time-coded movement deviations detected during video playback.</p>
        </div>
        <div className="p-8 text-center text-slate-400 bg-[#141522] rounded-xl border border-dashed border-white/10 text-xs sm:text-sm">
          No significant movement anomalies detected across this trial. Kinematic trajectory maintained within normative boundaries.
        </div>
      </div>
    );
  }

  const handleEventClick = (timestamp) => {
    if (onSeek) {
      onSeek(timestamp / 1000.0);
    }
  };

  const getDotColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-rose-500 shadow-rose-500/50';
      case 'high': return 'bg-orange-500 shadow-orange-500/50';
      case 'medium': return 'bg-amber-500 shadow-amber-500/50';
      default: return 'bg-purple-500 shadow-purple-500/50';
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <AlertTriangle size={20} className="text-amber-400" />
          <span>Kinematic Anomalies Timeline</span>
        </h3>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">Click any anomaly to seek the video player to that timestamp.</p>
      </div>

      <div className="relative border-l-2 border-white/10 ml-3 space-y-3.5 pt-1">
        {kinematicAnomalies.map((event, index) => (
          <div key={index} className="ml-5 relative">
            <span 
              className={`absolute -left-[27px] top-3.5 w-3.5 h-3.5 rounded-full border-2 border-[#090a0f] ${getDotColor(event.severity)} shadow-sm`}
              title={event.severity}
            />
            <div 
              className="p-4 bg-[#141522] hover:bg-[#1a1b2b] rounded-xl cursor-pointer border border-white/10 hover:border-purple-500/40 transition"
              onClick={() => handleEventClick(event.timestamp_ms)}
            >
              <div className="flex justify-between items-center mb-1.5">
                <span className="font-bold text-sm capitalize text-white">
                  {event.metric.replace(/_/g, ' ')}
                </span>
                <span className="text-xs font-mono bg-[#1c1d2e] text-purple-300 border border-purple-500/20 py-0.5 px-2.5 rounded-lg flex items-center gap-1.5">
                  <Clock size={12} className="text-purple-400" />
                  {(event.timestamp_ms / 1000).toFixed(2)}s
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 mb-2 leading-relaxed">{event.explanation}</p>
              <div className="text-xs text-slate-400 flex justify-between border-t border-white/5 pt-2">
                <span>Observed: <strong className="text-white">{event.observed_value}</strong></span>
                <span className="text-slate-400">Rule: {event.reference_rule}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AnomalyTimeline;
