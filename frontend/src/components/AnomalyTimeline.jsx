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
          <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-500" />
            <span>Kinematic Anomalies Timeline</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">Time-coded movement deviations detected during video playback.</p>
        </div>
        <div className="p-6 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs">
          No significant movement anomalies detected across this trial.
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
      case 'critical': return 'bg-rose-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-amber-500';
      default: return 'bg-blue-500';
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <AlertTriangle size={18} className="text-amber-500" />
          <span>Kinematic Anomalies Timeline</span>
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">Click any anomaly to seek the video player to that timestamp.</p>
      </div>

      <div className="relative border-l-2 border-slate-200 ml-3 space-y-3 pt-1">
        {kinematicAnomalies.map((event, index) => (
          <div key={index} className="ml-5 relative">
            <span 
              className={`absolute -left-[27px] top-2.5 w-3.5 h-3.5 rounded-full border-2 border-white ${getDotColor(event.severity)} shadow-xs`}
              title={event.severity}
            />
            <div 
              className="p-3.5 bg-slate-50 hover:bg-slate-100/80 rounded-xl cursor-pointer border border-slate-200 transition"
              onClick={() => handleEventClick(event.timestamp_ms)}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-xs capitalize text-slate-800">
                  {event.metric.replace(/_/g, ' ')}
                </span>
                <span className="text-[11px] font-mono bg-white text-slate-700 border border-slate-200 py-0.5 px-2 rounded-md flex items-center gap-1">
                  <Clock size={11} className="text-slate-400" />
                  {(event.timestamp_ms / 1000).toFixed(2)}s
                </span>
              </div>
              <p className="text-xs text-slate-600 mb-1.5 leading-relaxed">{event.explanation}</p>
              <div className="text-[11px] text-slate-500 flex justify-between border-t border-slate-200/60 pt-1.5 mt-1">
                <span>Observed: <strong className="text-slate-700">{event.observed_value}</strong></span>
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
