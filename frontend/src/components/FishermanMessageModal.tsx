import React, { useState } from 'react';
import { MessageSquare, Copy, Check, X } from 'lucide-react';
import { TFunc } from '../i18n';

interface FishermanMessageModalProps {
  text: string;
  landmark: string;
  maxChars: number;
  t: TFunc;
  isDraft: boolean;
  onClose: () => void;
}

/** Demo SMS/WhatsApp-style advisory. Nothing is sent anywhere. */
export const FishermanMessageModal: React.FC<FishermanMessageModalProps> = ({ text, landmark, maxChars, t, isDraft, onClose }) => {
  const [copied, setCopied] = useState(false);
  const n = Array.from(text).length;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="fixed inset-0 z-[3000] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in" onClick={onClose}>
      <div
        className="copernicus-panel p-5 flex flex-col gap-3 text-slate-200"
        style={{ width: 420, backgroundColor: 'rgba(12, 20, 35, 0.98)' }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={t('modal.title')}
      >
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold text-white">
            <MessageSquare size={15} className="text-[#4fd1c5]" />
            {t('modal.title')} — {landmark}
          </span>
          <button type="button" onClick={onClose} className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10" title={t('btn.close')}>
            <X size={15} />
          </button>
        </div>

        <div className="rounded-2xl rounded-tl-sm bg-[#134e4a]/60 border border-[#4fd1c5]/25 px-4 py-3 text-[13px] leading-relaxed text-slate-100 select-text whitespace-pre-wrap">
          {text}
        </div>

        <div className="flex items-center justify-between text-[10.5px]">
          <span className={n > maxChars ? 'text-rose-300 font-semibold' : 'text-slate-500'}>
            {t('modal.chars', { n })} / {maxChars}
          </span>
          {isDraft && <span className="text-amber-300">{t('fish.draft_note')}</span>}
        </div>
        <div className="text-[10px] text-slate-500">{t('modal.note')}</div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={copy}
            className="px-3 py-1.5 rounded-lg text-[11px] font-medium flex items-center gap-1.5 bg-gradient-to-r from-[#4fd1c5]/25 to-[#38bdf8]/20 text-[#4fd1c5] border border-[#4fd1c5]/35 hover:from-[#4fd1c5]/35"
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? t('btn.copied') : t('btn.copy')}
          </button>
        </div>
      </div>
    </div>
  );
};
