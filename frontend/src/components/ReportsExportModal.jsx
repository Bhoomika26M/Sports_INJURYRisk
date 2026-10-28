import { useState, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  FileSpreadsheet, 
  X, 
  CheckCircle, 
  AlertTriangle, 
  ShieldCheck, 
  Activity, 
  Calendar, 
  Video as VideoIcon,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import api from '../api/client';

const REPORT_TYPES = [
  {
    id: 'injury_risk',
    label: 'Injury Risk Screening',
    description: 'Weighted risk scoring & ACL, Hamstring, Ankle, Shoulder, Lumbar, and Overuse probabilities.',
    color: 'from-blue-600 to-indigo-600',
    badge: 'bg-blue-50 text-blue-700 border-blue-200'
  },
  {
    id: 'biomechanical',
    label: 'Biomechanical Assessment',
    description: 'Knee valgus ratio, dynamic knee alignment, trunk lean, hip stability, landing shock & stride.',
    color: 'from-emerald-600 to-teal-600',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200'
  },
  {
    id: 'movement_analysis',
    label: 'Movement Anomaly & Quality',
    description: 'Kinematic deviations, technique score & grade, motion inconsistency (CV%), jerk & fatigue drift.',
    color: 'from-purple-600 to-indigo-600',
    badge: 'bg-purple-50 text-purple-700 border-purple-200'
  },
  {
    id: 'athlete_performance',
    label: 'Athlete Performance',
    description: 'Overall health score, biomechanical efficiency, movement quality, and physical baselines.',
    color: 'from-cyan-600 to-blue-600',
    badge: 'bg-cyan-50 text-cyan-700 border-cyan-200'
  },
  {
    id: 'rehabilitation',
    label: 'Rehabilitation & Correctives',
    description: 'Targeted exercises, mobility improvement suggestions, strengthening, recovery & load mods.',
    color: 'from-teal-600 to-emerald-600',
    badge: 'bg-teal-50 text-teal-700 border-teal-200'
  }
];

export const ReportsExportModal = ({ isOpen, onClose, athleteId, athleteName, videos = [] }) => {
  const [selectedType, setSelectedType] = useState('injury_risk');
  const [selectedVideoId, setSelectedVideoId] = useState('');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [error, setError] = useState(null);

  // Fetch report data preview whenever type or video changes
  useEffect(() => {
    if (!isOpen || !athleteId) return;

    const fetchReportPreview = async () => {
      try {
        setLoading(true);
        setError(null);
        let url = `/reports/${athleteId}/data?report_type=${selectedType}`;
        if (selectedVideoId) {
          url += `&video_id=${selectedVideoId}`;
        }
        const res = await api.get(url);
        setReportData(res.data);
      } catch (err) {
        console.error('Failed to load report preview:', err);
        setError(err.response?.data?.detail || 'Failed to generate report data preview.');
      } finally {
        setLoading(false);
      }
    };

    fetchReportPreview();
  }, [isOpen, athleteId, selectedType, selectedVideoId]);

  if (!isOpen) return null;

  // Download PDF file
  const handleDownloadPdf = async () => {
    try {
      setExportingPdf(true);
      let url = `/reports/${athleteId}/export/pdf?report_type=${selectedType}`;
      if (selectedVideoId) url += `&video_id=${selectedVideoId}`;

      const response = await api.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `AthletiQ_${selectedType}_Report_${athleteId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('PDF export error:', err);
      alert('Failed to export PDF report. Please try again.');
    } finally {
      setExportingPdf(false);
    }
  };

  // Download Excel file
  const handleDownloadExcel = async () => {
    try {
      setExportingExcel(true);
      let url = `/reports/${athleteId}/export/excel?report_type=${selectedType}`;
      if (selectedVideoId) url += `&video_id=${selectedVideoId}`;

      const response = await api.get(url, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `AthletiQ_${selectedType}_Report_${athleteId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Excel export error:', err);
      alert('Failed to export Excel report. Please try again.');
    } finally {
      setExportingExcel(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <FileText size={20} />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold tracking-tight">
                Reports & Clinical Export System
              </h2>
              <p className="text-xs text-slate-400">
                {athleteName ? `Athlete: ${athleteName} (#${athleteId})` : `Athlete #${athleteId}`} · Multi-format Biomechanical Export
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Controls Bar */}
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          {/* Report Type Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {REPORT_TYPES.map((rt) => (
              <button
                key={rt.id}
                onClick={() => setSelectedType(rt.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  selectedType === rt.id
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                }`}
              >
                {rt.label}
              </button>
            ))}
          </div>

          {/* Video Selector & Export Buttons */}
          <div className="flex items-center gap-2 ml-auto">
            {videos.length > 0 && (
              <select
                value={selectedVideoId}
                onChange={(e) => setSelectedVideoId(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
              >
                <option value="">Latest Completed Trial</option>
                {videos.map((v) => (
                  <option key={v.id} value={v.id}>
                    Trial #{v.id} ({v.movement_type || 'General'})
                  </option>
                ))}
              </select>
            )}

            {/* Export Buttons */}
            <button
              onClick={handleDownloadPdf}
              disabled={exportingPdf || loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-600 text-white hover:bg-rose-700 transition disabled:opacity-50 shadow-xs"
            >
              <Download size={14} className={exportingPdf ? 'animate-bounce' : ''} />
              {exportingPdf ? 'Exporting...' : 'Download PDF'}
            </button>

            <button
              onClick={handleDownloadExcel}
              disabled={exportingExcel || loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 transition disabled:opacity-50 shadow-xs"
            >
              <FileSpreadsheet size={14} className={exportingExcel ? 'animate-bounce' : ''} />
              {exportingExcel ? 'Exporting...' : 'Download Excel'}
            </button>
          </div>
        </div>

        {/* Preview Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-24 text-center">
              <RefreshCw size={32} className="mx-auto text-blue-600 animate-spin mb-3" />
              <p className="text-sm font-semibold text-slate-700">Synthesizing Clinical Report...</p>
              <p className="text-xs text-slate-400 mt-1">Aggregating kinematics, risk weights, and recommendations</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">
              <p className="font-bold mb-1">Failed to generate report</p>
              <p>{error}</p>
            </div>
          ) : reportData ? (
            <div className="space-y-6">
              {/* Report Header Card */}
              <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                      {reportData.metadata.report_type.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {reportData.metadata.report_id}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900">
                    {reportData.summary.title}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Athlete: <span className="font-semibold text-slate-800">{reportData.metadata.athlete_name}</span> · 
                    Sport: <span className="font-semibold text-slate-800">{reportData.metadata.sport}</span> · 
                    Trial: <span className="font-semibold text-slate-800">{reportData.metadata.movement_type}</span>
                  </p>
                </div>

                {/* Scorecard Pill */}
                <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      {reportData.summary.primary_label}
                    </span>
                    <span className="text-xl font-extrabold text-blue-600">
                      {reportData.summary.primary_metric}
                    </span>
                  </div>
                  <div className="border-l border-slate-200 pl-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Status
                    </span>
                    <span className="text-xs font-bold text-slate-800">
                      {reportData.summary.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Sections */}
              {reportData.sections.map((sec, idx) => (
                <div key={idx} className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
                  <div className="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      {sec.title}
                    </h4>
                    {sec.description && (
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {sec.description}
                      </p>
                    )}
                  </div>

                  {sec.table_headers && sec.table_rows && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900 text-white font-semibold text-[11px]">
                          <tr>
                            {sec.table_headers.map((th, thIdx) => (
                              <th key={thIdx} className="px-4 py-2.5">
                                {th}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {sec.table_rows.map((row, rIdx) => (
                            <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                              {row.map((cell, cIdx) => (
                                <td key={cIdx} className="px-4 py-2.5">
                                  {cIdx === 0 ? (
                                    <span className="font-semibold text-slate-900">{cell}</span>
                                  ) : (
                                    <span>{cell}</span>
                                  )}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}

              {/* Recommendations Preview if present */}
              {reportData.recommendations && reportData.recommendations.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <Sparkles size={14} className="text-emerald-600" />
                    Corrective Protocols & Actions
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {reportData.recommendations.slice(0, 4).map((rec, rIdx) => (
                      <div key={rIdx} className="p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">
                            {rec.category} · {rec.target_region}
                          </span>
                        </div>
                        <h5 className="text-xs font-bold text-slate-900 line-clamp-1">{rec.title}</h5>
                        <p className="text-[11px] text-slate-600 mt-1 line-clamp-2 leading-relaxed">
                          {rec.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Medical / Screening Disclaimer Footer */}
              <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200/60 text-[11px] text-amber-900 leading-relaxed">
                <span className="font-bold">LEGAL & CLINICAL SCREENING NOTICE: </span>
                {reportData.metadata.disclaimer}
              </div>
            </div>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Export formats: PDF (print-ready vector document) & Excel (.xlsx multi-sheet)
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
