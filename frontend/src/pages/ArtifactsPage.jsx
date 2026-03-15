export default function ArtifactsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="text-display-md inde-gradient-text mb-3">Innovation Artifacts</div>
      <p className="text-body-md text-zinc-500 mb-6 max-w-md">
        Generated artifacts, experiments, and evidence collected throughout your innovation journey.
      </p>
      <span className="inline-flex items-center px-3 py-1 rounded-badge bg-inde-500/10 text-inde-400 text-caption font-mono">
        Coming in v3.7.4.2
      </span>
    </div>
  );
}
