interface DataSourceBadgeProps {
  dataSource: string;
  modelVersion: string;
}

export function DataSourceBadge({ dataSource, modelVersion }: DataSourceBadgeProps) {
  if (dataSource === 'mock') {
    return (
      <span className="inline-flex items-center whitespace-nowrap rounded-md bg-amber-500/10 px-2 py-1 text-[10px] font-semibold tracking-wide text-amber-400 ring-1 ring-amber-500/30 ring-inset">
        DEMO DATA — NOT MODEL OUTPUT
      </span>
    );
  }
  if (dataSource === 'model_output_files' || dataSource === 'model') {
    return (
      <span className="inline-flex items-center whitespace-nowrap rounded-md bg-green-500/10 px-2 py-1 text-[10px] font-semibold tracking-wide text-green-400 ring-1 ring-green-500/30 ring-inset">
        {dataSource === 'model' ? 'MODEL' : 'MODEL OUTPUT'}: {modelVersion}
      </span>
    );
  }
  return null;
}
