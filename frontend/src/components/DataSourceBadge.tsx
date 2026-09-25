

interface DataSourceBadgeProps {
  dataSource: string;
  modelVersion: string;
}

export function DataSourceBadge({ dataSource, modelVersion }: DataSourceBadgeProps) {
  if (dataSource === 'mock') {
    return (
      <span className="inline-flex items-center rounded-md bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-500 ring-1 ring-amber-500/20 ring-inset">
        DEMO DATA — NOT MODEL OUTPUT
      </span>
    );
  } else if (dataSource === 'model_output_files' || dataSource === 'model') {
    return (
      <span className="inline-flex items-center rounded-md bg-green-500/10 px-2 py-1 text-xs font-medium text-green-400 ring-1 ring-green-500/20 ring-inset">
        MODEL OUTPUT: {modelVersion}
      </span>
    );
  }
  return null;
}
