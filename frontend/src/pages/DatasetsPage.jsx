import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { 
  Database, 
  Activity, 
  ShieldCheck, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  BookOpen, 
  Layers, 
  ExternalLink,
  Code2,
  RefreshCw
} from 'lucide-react';

export const DatasetsPage = () => {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Active Tab: 'catalog' | 'fifa' | 'simulator'
  const [activeTab, setActiveTab] = useState('catalog');
  
  // Simulator state
  const [simDataset, setSimDataset] = useState('coco');
  const [simPayload, setSimPayload] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simError, setSimError] = useState('');

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const res = await api.get('/datasets');
      setDatasets(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch datasets');
    } finally {
      setLoading(false);
    }
  };

  const loadSimulatorSample = async (dsId) => {
    setSimDataset(dsId);
    setSimLoading(true);
    setSimError('');
    setSimResult(null);
    try {
      const res = await api.get(`/datasets/${dsId}/sample`);
      setSimPayload(res.data);
    } catch (err) {
      setSimError(err.response?.data?.detail || 'Failed to load sample');
    } finally {
      setSimLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'simulator' && !simPayload) {
      loadSimulatorSample(simDataset);
    }
  }, [activeTab, simPayload, simDataset]);

  const runSimulation = async () => {
    if (!simPayload) return;
    setSimLoading(true);
    setSimError('');
    try {
      const res = await api.post(`/datasets/convert?dataset_id=${simDataset}`, simPayload);
      setSimResult(res.data);
    } catch (err) {
      setSimError(err.response?.data?.detail || 'Conversion failed');
    } finally {
      setSimLoading(false);
    }
  };

  const fifaDataset = datasets.find(d => d.id === 'fifa_reference');

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 bg-blue-100 text-blue-700 rounded-xl">
            <Database size={28} />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
              Datasets & Clinical Reference Frameworks
            </h1>
            <p className="text-gray-600 text-sm mt-0.5">
              Integrated computer vision benchmark topologies, sports movement datasets, and clinical FIFA 11+ risk models.
            </p>
          </div>
        </div>

        {/* Tab navigation */}
        <div className="flex border-b border-gray-200 mt-6 gap-2">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`py-3 px-4 font-semibold text-sm border-b-2 transition flex items-center gap-2 ${
              activeTab === 'catalog'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Layers size={16} /> Dataset Catalog ({datasets.length})
          </button>
          <button
            onClick={() => setActiveTab('fifa')}
            className={`py-3 px-4 font-semibold text-sm border-b-2 transition flex items-center gap-2 ${
              activeTab === 'fifa'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <BookOpen size={16} /> FIFA 11+ Clinical Reference
          </button>
          <button
            onClick={() => setActiveTab('simulator')}
            className={`py-3 px-4 font-semibold text-sm border-b-2 transition flex items-center gap-2 ${
              activeTab === 'simulator'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Code2 size={16} /> Adapter & Pipeline Simulator
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl shadow-sm border">
          <RefreshCw className="animate-spin mx-auto mb-3 text-blue-600" size={32} />
          Loading integrated datasets...
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
          {error}
        </div>
      ) : (
        <>
          {/* TAB 1: DATASET CATALOG */}
          {activeTab === 'catalog' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {datasets.map((ds) => {
                const isClinical = ds.id === 'fifa_reference';
                return (
                  <div 
                    key={ds.id} 
                    className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col justify-between hover:shadow-md transition"
                  >
                    <div>
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <span className={`text-xs uppercase font-bold tracking-wider px-2.5 py-1 rounded-full ${
                            isClinical ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
                          }`}>
                            {ds.category}
                          </span>
                          <h2 className="text-xl font-bold text-gray-900 mt-2">{ds.name}</h2>
                        </div>
                        {ds.keypoint_count && (
                          <span className="text-xs bg-gray-100 text-gray-700 font-semibold px-2.5 py-1 rounded-lg border">
                            {ds.keypoint_count} Keypoints
                          </span>
                        )}
                      </div>

                      <div className="space-y-3 mt-4 text-sm text-gray-600">
                        <div>
                          <p className="font-semibold text-gray-900 mb-1">Purposes & Applications:</p>
                          <ul className="list-disc pl-5 space-y-0.5">
                            {ds.purposes.map((p, idx) => (
                              <li key={idx}>{p}</li>
                            ))}
                          </ul>
                        </div>

                        <div>
                          <p className="font-semibold text-gray-900">Coordinate Specification:</p>
                          <p className="text-gray-700">{ds.coordinate_type}</p>
                        </div>

                        <div>
                          <p className="font-semibold text-gray-900">Role in Platform:</p>
                          <p className="text-gray-700">{ds.clinical_role}</p>
                        </div>
                      </div>
                    </div>

                    <div className="mt-6 pt-4 border-t flex items-center justify-between text-xs text-gray-500">
                      <span>License: <strong className="text-gray-700">{ds.licensing}</strong></span>
                      {ds.reference_link && (
                        <a 
                          href={ds.reference_link} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="text-blue-600 hover:text-blue-800 flex items-center gap-1 font-semibold"
                        >
                          Official Docs <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB 2: FIFA 11+ CLINICAL REFERENCE */}
          {activeTab === 'fifa' && fifaDataset && (
            <div className="space-y-6">
              <div className="bg-gradient-to-r from-emerald-600 to-teal-700 text-white p-6 rounded-2xl shadow-sm">
                <div className="flex items-center gap-3 mb-2">
                  <ShieldCheck size={32} />
                  <h2 className="text-2xl font-bold">FIFA 11+ / F-MARC Injury Prevention Reference</h2>
                </div>
                <p className="text-emerald-50 text-sm max-w-3xl leading-relaxed">
                  The clinical foundation of our injury screening platform. Built on longitudinal epidemiological research by the FIFA Medical Assessment and Research Centre (F-MARC), establishing mathematically defined risk thresholds to predict and prevent non-contact ACL tears, hamstring injuries, and ankle sprains.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {fifaDataset.risk_factors && Object.entries(fifaDataset.risk_factors).map(([key, factor]) => (
                  <div key={key} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-bold text-gray-900 text-lg">{factor.name}</h3>
                        <span className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold px-2 py-0.5 rounded">
                          Clinical Marker
                        </span>
                      </div>
                      <p className="text-gray-600 text-sm mb-4">{factor.description}</p>

                      <div className="bg-gray-50 p-3.5 rounded-lg border text-sm space-y-2 mb-4">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Target Normative Value:</span>
                          <span className="font-bold text-emerald-700">
                            &le; {factor.target_threshold_deg ?? factor.target_threshold_pct}&deg;
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Moderate Risk Range:</span>
                          <span className="font-semibold text-amber-700">
                            {factor.moderate_risk_deg ?? factor.moderate_risk_pct}&deg;
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">High / Critical Threshold:</span>
                          <span className="font-bold text-rose-700">
                            &gt; {factor.high_risk_deg ?? factor.high_risk_pct}&deg;
                          </span>
                        </div>
                      </div>

                      <div className="space-y-2 text-sm">
                        <p><strong className="text-gray-900">Primary Injury Risk:</strong> <span className="text-rose-700 font-medium">{factor.primary_injury_risk}</span></p>
                        <p><strong className="text-gray-900">Intervention Protocol:</strong> <span className="text-gray-700">{factor.intervention_protocol}</span></p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: ADAPTER & SIMULATOR */}
          {activeTab === 'simulator' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <h2 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2">
                  <Code2 className="text-blue-600" size={20} />
                  Multi-Dataset Format Normalizer & Biomechanics Simulator
                </h2>
                <p className="text-sm text-gray-600 mb-6">
                  Select any external dataset format. The platform adapter converts its native keypoint schema into our unified 33-landmark coordinate space, computes live joint angles, and validates against FIFA clinical criteria.
                </p>

                {/* Dataset selector */}
                <div className="flex flex-wrap items-center gap-3 mb-6">
                  {['coco', 'mpii', 'human36m', 'sportspose'].map((id) => (
                    <button
                      key={id}
                      onClick={() => loadSimulatorSample(id)}
                      className={`px-4 py-2 rounded-lg text-sm font-semibold transition border ${
                        simDataset === id
                          ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                          : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      {id.toUpperCase()} Dataset
                    </button>
                  ))}
                  
                  <button
                    onClick={runSimulation}
                    disabled={simLoading || !simPayload}
                    className="ml-auto bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold px-5 py-2 rounded-lg shadow flex items-center gap-2 transition disabled:opacity-50"
                  >
                    <Play size={16} /> Run Converter & Biomechanics Pipeline
                  </button>
                </div>

                {simError && (
                  <div className="p-3 bg-red-50 text-red-700 text-sm rounded mb-4">
                    {simError}
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left: Raw Payload Preview */}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
                      Raw Native Payload ({simDataset.toUpperCase()} Format)
                    </h3>
                    <pre className="bg-slate-900 text-slate-100 p-4 rounded-xl text-xs overflow-auto max-h-96 font-mono border border-slate-800">
                      {simPayload ? JSON.stringify(simPayload, null, 2) : 'Loading payload...'}
                    </pre>
                  </div>

                  {/* Right: Converted Results & FIFA Benchmark */}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
                      Adapter Output & FIFA Clinical Compliance
                    </h3>
                    {simResult ? (
                      <div className="bg-white border rounded-xl p-5 space-y-4 max-h-96 overflow-auto shadow-inner">
                        <div className="flex items-center justify-between pb-3 border-b">
                          <div>
                            <span className="text-xs text-gray-500">Mapped Landmarks</span>
                            <p className="text-lg font-bold text-gray-900">{simResult.converted_landmarks_count} Joints</p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-500">Overall FIFA Status</span>
                            <span className={`block px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                              simResult.fifa_evaluation?.overall_fifa_compliance === 'SATISFACTORY'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}>
                              {simResult.fifa_evaluation?.overall_fifa_compliance}
                            </span>
                          </div>
                        </div>

                        {/* Extracted Biomechanics */}
                        <div>
                          <h4 className="text-xs font-bold uppercase text-gray-700 mb-2">Calculated Joint Kinematics</h4>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="p-2 bg-gray-50 rounded border">
                              <span className="text-gray-500">Left Knee Flexion:</span>
                              <p className="font-bold text-gray-900">{simResult.biomechanics?.left_knee_angle ? `${simResult.biomechanics.left_knee_angle.toFixed(1)}°` : 'N/A'}</p>
                            </div>
                            <div className="p-2 bg-gray-50 rounded border">
                              <span className="text-gray-500">Right Knee Flexion:</span>
                              <p className="font-bold text-gray-900">{simResult.biomechanics?.right_knee_angle ? `${simResult.biomechanics.right_knee_angle.toFixed(1)}°` : 'N/A'}</p>
                            </div>
                            <div className="p-2 bg-gray-50 rounded border">
                              <span className="text-gray-500">Trunk Lean:</span>
                              <p className="font-bold text-gray-900">{simResult.biomechanics?.trunk_lean ? `${simResult.biomechanics.trunk_lean.toFixed(1)}°` : 'N/A'}</p>
                            </div>
                            <div className="p-2 bg-gray-50 rounded border">
                              <span className="text-gray-500">Quality Status:</span>
                              <p className="font-bold text-emerald-700">{simResult.biomechanics?.quality_flag}</p>
                            </div>
                          </div>
                        </div>

                        {/* FIFA Evaluation Factors */}
                        {simResult.fifa_evaluation?.factors && (
                          <div>
                            <h4 className="text-xs font-bold uppercase text-gray-700 mb-2">FIFA 11+ Evaluation</h4>
                            <div className="space-y-2">
                              {simResult.fifa_evaluation.factors.map((f, idx) => (
                                <div key={idx} className="p-2.5 bg-blue-50/50 border border-blue-100 rounded text-xs space-y-1">
                                  <div className="flex justify-between font-semibold">
                                    <span className="text-blue-950">{f.name}</span>
                                    <span className="text-blue-700">{f.risk_level}</span>
                                  </div>
                                  <p className="text-gray-600">Observed: <strong>{f.observed_value}&deg;</strong> (Target: {f.threshold_target})</p>
                                  <p className="text-gray-500 italic">Protocol: {f.intervention_protocol}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-gray-50 border border-dashed rounded-xl p-8 text-center text-sm text-gray-500">
                        Click "Run Converter & Biomechanics Pipeline" above to run this dataset sample through the adapter.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
export default DatasetsPage;
