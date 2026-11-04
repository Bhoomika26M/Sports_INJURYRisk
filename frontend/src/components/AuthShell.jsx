export function Logo({ size = 36 }) {
  return (
    <span className="inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 shadow-lg shadow-blue-900/30" style={{ width: size, height: size }}>
      <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6} fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 12h4l2-6 4 12 2-6h6" />
      </svg>
    </span>
  );
}

const POINTS = [
  [150, 52], [118, 96], [182, 96], [100, 150], [200, 150], [92, 200], [208, 200],
  [128, 190], [172, 190], [122, 262], [178, 262], [118, 330], [182, 330], [108, 350], [192, 350],
];
const BONES = [[1, 2], [1, 3], [3, 5], [5, 7], [2, 4], [4, 6], [1, 8], [2, 9], [8, 9], [8, 10], [10, 12], [12, 14], [9, 11], [11, 13], [13, 15]];

function Skeleton() {
  return (
    <svg viewBox="0 0 300 400" className="h-full max-h-80 w-auto opacity-90" aria-hidden="true">
      {BONES.map(([a, b]) => (
        <line key={`${a}-${b}`} x1={POINTS[a - 1][0]} y1={POINTS[a - 1][1]} x2={POINTS[b - 1][0]} y2={POINTS[b - 1][1]} stroke="rgba(125,211,252,0.55)" strokeWidth="3" strokeLinecap="round" />
      ))}
      {POINTS.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === 0 ? 11 : 6} fill="#22d3ee" stroke="white" strokeWidth="2" />
      ))}
    </svg>
  );
}

const FEATURES = [
  "Joint tracking from an ordinary training video",
  "Injury risk scored from 0 to 100",
  "Corrective exercises and recovery plans",
];

export default function AuthShell({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-blue-800 p-12 text-white lg:flex lg:flex-col">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <Logo size={40} />
          <span className="text-lg font-bold tracking-tight">InjuryRisk AI</span>
        </div>
        <div className="relative flex flex-1 items-center justify-between gap-8">
          <div className="max-w-sm">
            <h2 className="text-4xl font-bold leading-tight tracking-tight">Move better.<br />Stay in the game.</h2>
            <ul className="mt-8 space-y-3 text-sm text-blue-100">
              {FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-cyan-400/20 text-cyan-300">
                    <svg viewBox="0 0 20 20" width="12" height="12" fill="currentColor"><path d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z" /></svg>
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <Skeleton />
        </div>
        <p className="relative text-xs text-blue-200/70">Decision support for coaches, physiotherapists and athletes. Not a medical diagnosis.</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <Logo />
            <span className="text-lg font-bold tracking-tight text-slate-900">InjuryRisk AI</span>
          </div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
