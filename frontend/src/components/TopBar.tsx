import React, { useState } from 'react';
import { Waves, Map as MapIcon, Fish, AlertTriangle, ChevronDown } from 'lucide-react';
import { DataSourceBadge } from './DataSourceBadge';
import { Metadata } from '../types';
import { formatDate, formatTimestamp } from '../i18n';

export type TabId = 'explorer' | 'fisheries';

interface TopBarProps {
  metadata: Metadata;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  productDate: string | null;
  tabLabels: Record<TabId, string>;
}

export const TopBar: React.FC<TopBarProps> = ({ metadata, activeTab, onTabChange, productDate, tabLabels }) => {
  const [showInvalid, setShowInvalid] = useState(false);
  const info = productDate ? metadata.per_date?.[productDate] : undefined;
  // Dates without an OceanEmbed product (e.g. a PFZ date in files mode): default validity of +1 day
  const validUpto =
    info?.valid_upto ??
    (productDate ? new Date(Date.parse(productDate) + 86400000).toISOString().slice(0, 10) : null);
  const invalid = metadata.invalid_model_files ?? [];

  const tabs: { id: TabId; icon: React.ReactNode }[] = [
    { id: 'explorer', icon: <MapIcon size={13} /> },
    { id: 'fisheries', icon: <Fish size={13} /> },
  ];

  return (
    <div className="relative z-[1100] flex-shrink-0">
      <div
        className="h-11 flex items-center gap-4 px-4 border-b border-[#4fd1c5]/15"
        style={{ backgroundColor: 'rgba(8, 14, 25, 0.97)' }}
      >
        <div className="flex items-center gap-2 pr-2">
          <Waves size={16} className="text-[#4fd1c5]" />
          <span className="text-xs font-bold tracking-wide text-white">OceanEmbed</span>
        </div>

        {/* Tabs (room reserved for a future Disaster tab) */}
        <nav className="flex items-center gap-1" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-medium flex items-center gap-1.5 transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-[#4fd1c5]/20 to-[#38bdf8]/15 text-[#4fd1c5] border border-[#4fd1c5]/35'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] border border-transparent'
              }`}
            >
              {tab.icon}
              {tabLabels[tab.id]}
            </button>
          ))}
        </nav>

        {/* Date-validity stamp */}
        <div className="flex-1 flex justify-center min-w-0">
          {productDate && (
            <div className="text-[10.5px] font-mono text-slate-400 truncate">
              Product date: <span className="text-white">{formatDate(productDate)}</span>
              <span className="text-slate-600 mx-1.5">·</span>
              Valid upto: <span className="text-white">{formatDate(validUpto)}</span>
              <span className="text-slate-600 mx-1.5">·</span>
              Generated: <span className="text-slate-300">{formatTimestamp(info?.generated_at)}</span>
            </div>
          )}
        </div>

        {invalid.length > 0 && (
          <button
            type="button"
            onClick={() => setShowInvalid(!showInvalid)}
            className="flex items-center gap-1 text-[10px] font-medium text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-md px-2 py-1"
          >
            <AlertTriangle size={12} />
            {invalid.length} model file{invalid.length > 1 ? 's' : ''} rejected
            <ChevronDown size={11} className={showInvalid ? 'rotate-180' : ''} />
          </button>
        )}

        <DataSourceBadge dataSource={metadata.data_source || 'mock'} modelVersion={metadata.model_version || 'unknown'} />
      </div>

      {/* Validation error banner for rejected model output files */}
      {invalid.length > 0 && showInvalid && (
        <div className="absolute left-0 right-0 top-11 px-4 py-2 bg-rose-950/95 border-b border-rose-500/30 text-[11px] font-mono text-rose-200 max-h-48 overflow-y-auto">
          {invalid.map((f) => (
            <div key={f.file} className="py-0.5">
              <b>{f.file}</b>: {f.errors.join('; ')}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
