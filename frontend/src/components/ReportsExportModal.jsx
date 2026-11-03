import { useState, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  FileSpreadsheet, 
  X, 
  ShieldCheck, 
  Activity, 
  RefreshCw,
  Sparkles,
  Gauge,
  Heart
} from 'lucide-react';
import api from '../api/client';

export const ReportsExportModal = ({ isOpen, onClose, athleteId, athleteName, videos = [], videoId = '' }) => {
  const [selectedVideoId, setSelectedVideoId] = useState(videoId || '');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (videoId) setSelectedVideoId(videoId);
  }, [videoId]);

  useEffect(() => {
    if (!isOpen || !athleteId) return;

    const fetchReportPreview = async () => {
      try {
        setLoading(true);
        setError(null);
        let url = `/reports/${athleteId}/data?report_type=comprehensive`;
        if (selectedVideoId) {
          url += `&video_id=${selectedVideoId}`;
        }
        const res = await api.get(url);
        setReportData(res.data);
      } catch (err) {
        console.error('Failed to load report preview:', err);
        setError(err.response?.data?.detail || 'Failed to generate consolidated report preview.');
      } finally {
        setLoading(false);
      }
    };

    fetchReportPreview();
  }, [isOpen, athleteId, selectedVideoId]);

  if (!isOpen) return null;

  const handleDownloadPdf = async () => {
    try {
      setExportingPdf(true);
      let url = `/reports/${athleteId}/export/pdf?report_type=comprehensive`;
      if (selectedVideoId) url += `&video_id=${selectedVideoId}`;

      const response = await api.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `AthletiQ_Comprehensive_Report_${athleteId}.pdf`;
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

  const handleDownloadExcel = async () => {
    try {
      setExportingExcel(true);
      let url = `/reports/${athleteId}/export/excel?report_type=comprehensive`;
      if (selectedVideoId) url += `&video_id=${selectedVideoId}`;

      const response = await api.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `AthletiQ_Analysis_Data_${athleteId}.xlsx`;
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-[#0c0d14] rounded-2xl shadow-2xl border border-white/10 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#12131d] text-white flex items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/40 flex items-center justify-center text-purple-300 shadow-sm">
              <FileText size={20} />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold tracking-tight text-white">
                Consolidated Movement & Risk Screening Report
              </h2>
              <p className="text-xs sm:text-sm text-slate-400">
                {athleteName ? `Athlete: ${athleteName} (#${athleteId})` : `Athlete #${athleteId}`} &bull; Single Unified Biomechanical Export
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Controls Bar */}
        <div className="px-6 py-3.5 bg-[#141522] border-b border-white/10 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xs sm:text-sm font-semibold text-slate-300">Movement Trial:</span>
            {videos.length > 0 ? (
              <select
                value={selectedVideoId}
                onChange={(e) => setSelectedVideoId(e.target.value)}
                className="text-xs sm:text-sm border border-white/15 rounded-xl px-3 py-1.5 bg-[#1c1d2e] text-white focus:outline-none focus:ring-2 focus:ring-purple-500 font-medium"
              >
                <option value="">Latest Completed Trial</option>
                {videos.map((v) => (
                  <option key={v.id} value={v.id}>
                    Trial #{v.id} ({v.movement_type || 'General'})
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-slate-400 italic">Latest available analysis</span>
            )}
          </div>

          {/* Export Action Buttons */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleDownloadPdf}
              disabled={exportingPdf || loading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-purple-600 text-white hover:bg-purple-500 transition disabled:opacity-50 shadow-md shadow-purple-600/25"
            >
              <Download size={15} className={exportingPdf ? 'animate-bounce' : ''} />
              {exportingPdf ? 'Generating PDF...' : 'Download Full Report (PDF)'}
            </button>

            <button
              onClick={handleDownloadExcel}
              disabled={exportingExcel || loading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-[#1a1b28] border border-emerald-500/30 text-emerald-300 hover:bg-[#232435] transition disabled:opacity-50"
            >
              <FileSpreadsheet size={15} className="text-emerald-400" />
              {exportingExcel ? 'Exporting...' : 'Export Data (Excel)'}
            </button>
          </div>
        </div>

        {/* Preview Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-20 text-center">
              <RefreshCw size={32} className="mx-auto text-purple-400 animate-spin mb-3" />
              <p className="text-sm font-semibold text-slate-200">Synthesizing Consolidated Screening Report...</p>
              <p className="text-xs text-slate-400 mt-1">Aggregating kinematics, pose keypoints, and corrective protocols</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs sm:text-sm">
              <p className="font-bold mb-1 text-rose-200">Failed to generate report preview</p>
              <p>{error}</p>
            </div>
          ) : reportData ? (
            <div className="space-y-6">
              {/* Scorecard Hero Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                <div className="p-4 rounded-xl border border-white/10 bg-[#141522]">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Injury Risk Score</span>
                  <div className="text-2xl font-black text-purple-400 mt-1">
                    {reportData.summary.primary_metric}
                  </div>
                  <span className="text-xs font-medium text-slate-300 mt-0.5 block">{reportData.summary.status}</span>
                </div>

                <div className="p-4 rounded-xl border border-white/10 bg-[#141522]">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Movement Quality</span>
                  <div className="text-2xl font-black text-white mt-1">
                    {reportData.summary.movement_quality || 'Optimal'}
                  </div>
                  <span className="text-xs font-medium text-slate-400 mt-0.5 block">Technique grade</span>
                </div>

                <div className="p-4 rounded-xl border border-white/10 bg-[#141522]">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Health Readiness</span>
                  <div className="text-2xl font-black text-emerald-400 mt-1">
                    {reportData.summary.health_score || '88.0 / 100'}
                  </div>
                  <span className="text-xs font-medium text-slate-400 mt-0.5 block">Readiness index</span>
                </div>

                <div className="p-4 rounded-xl border border-white/10 bg-[#141522]">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Bio Efficiency</span>
                  <div className="text-2xl font-black text-indigo-400 mt-1">
                    {reportData.summary.bio_efficiency || '86.0 / 100'}
                  </div>
                  <span className="text-xs font-medium text-slate-400 mt-0.5 block">Force transfer</span>
                </div>
              </div>

              {/* Report Summary Callout */}
              <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-xs sm:text-sm text-purple-200 flex items-start gap-3">
                <ShieldCheck size={18} className="text-purple-400 shrink-0 mt-0.5" />
                <p className="leading-relaxed font-normal">
                  {reportData.summary.highlight}
                </p>
              </div>

              {/* Sections */}
              {reportData.sections.map((sec, idx) => (
                <div key={idx} className="bg-[#12131d] rounded-xl border border-white/10 overflow-hidden shadow-sm">
                  <div className="px-5 py-3.5 bg-[#171826] border-b border-white/10">
                    <h4 className="text-xs sm:text-sm font-bold text-white uppercase tracking-wider">
                      {sec.title}
                    </h4>
                    {sec.description && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        {sec.description}
                      </p>
                    )}
                  </div>

                  {sec.table_headers && sec.table_rows && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs sm:text-sm">
                        <thead className="bg-[#1c1d2e] text-slate-300 font-semibold text-xs uppercase tracking-wider">
                          <tr>
                            {sec.table_headers.map((th, thIdx) => (
                              <th key={thIdx} className="px-4 py-2.5">
                                {th}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300">
                          {sec.table_rows.map((row, rIdx) => (
                            <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-[#12131d]' : 'bg-[#141522]'}>
                              {row.map((cell, cIdx) => (
                                <td key={cIdx} className="px-4 py-2.5">
                                  {cIdx === 0 ? (
                                    <span className="font-semibold text-white">{cell}</span>
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

              {/* Corrective Protocols Preview */}
              {reportData.recommendations && reportData.recommendations.length > 0 && (
                <div className="bg-[#12131d] rounded-xl border border-white/10 p-5 shadow-sm">
                  <h4 className="text-xs sm:text-sm font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
                    <Sparkles size={16} className="text-emerald-400" />
                    Targeted Corrective Action Plan
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {reportData.recommendations.slice(0, 4).map((rec, rIdx) => (
                      <div key={rIdx} className="p-3.5 rounded-xl border border-white/5 bg-[#171826]">
                        <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block mb-1">
                          {rec.category} &bull; {rec.target_region}
                        </span>
                        <h5 className="text-sm font-bold text-white">{rec.title}</h5>
                        <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                          {rec.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-[#12131d] border-t border-white/10 flex items-center justify-between text-xs sm:text-sm text-slate-400">
          <span>
            AthletiQ Sports Screening Engine &bull; Confidential Assessment
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold text-slate-300 hover:text-white hover:bg-white/10 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
