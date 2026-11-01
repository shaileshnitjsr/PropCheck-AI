'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  History,
  Home,
  Layers,
  MessageSquare,
  Scale,
  Shield,
  Upload,
} from 'lucide-react';
import { BenefitsPanel } from '@/components/benefits-panel';
import { ChatPanel } from '@/components/chat-panel';
import { HistoryPanel } from '@/components/history-panel';
import { LegalNotice } from '@/components/legal-notice';
import { UploadPanel } from '@/components/upload-panel';
import { useContract } from '@/hooks/use-contract';
import { AuditPanel } from '@/components/audit-panel';
import { SourceViewer } from '@/components/source-viewer';
import { SourceSelection } from '@/lib/audit-contracts';
import { AuthGate } from '@/components/auth-gate';
import { DocumentWorkspace } from '@/components/document-workspace';
import { ReportActions } from '@/components/report-actions';
import { PropCheckDashboard } from '@/components/propcheck-dashboard';

const NAV_ITEMS = [
  { id: 'intro', label: 'Intro', icon: Home },
  { id: 'upload', label: 'Upload', icon: Upload },
  { id: 'propcheck', label: 'PropCheck', icon: Shield },
  { id: 'workspace', label: 'Workspace', icon: Layers },
  { id: 'benefits', label: 'Benefits', icon: Scale },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'audit', label: 'Audit', icon: AlertTriangle },
] as const;

export default function HomePage() {
  return <AuthGate>{account => <Workspace key={account} account={account} />}</AuthGate>;
}

function Workspace({ account }: { account: string }) {
  const contract = useContract(account);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [source, setSource] = useState<SourceSelection | null>(null);
  const [activeSection, setActiveSection] = useState('intro');
  const closeSource = useCallback(() => setSource(null), []);
  const busy = contract.busy !== null;

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 200;
      for (let i = NAV_ITEMS.length - 1; i >= 0; i--) {
        const el = document.getElementById(NAV_ITEMS[i].id);
        if (el && el.offsetTop <= scrollPosition) {
          setActiveSection(NAV_ITEMS[i].id);
          break;
        }
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return <div className="studio-container relative">
    <aside className="studio-sidebar">
      <a
        href="#intro"
        className="studio-logo"
        onClick={() => { contract.reset(); setSource(null); }}
        aria-label="PropCheck AI home"
        title="PropCheck AI Home"
      >
        <span className="font-black text-lg tracking-widest text-[#ff4e3a] leading-none">PROP</span>
        <span className="text-[9px] font-bold tracking-widest text-gray-400 uppercase mt-1 leading-none">CHECK</span>
      </a>
      <nav className="studio-nav-links" aria-label="Main navigation">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <a
            key={id}
            href={`#${id}`}
            className={`studio-nav-item ${activeSection === id ? 'active' : ''}`}
            aria-label={label}
            title={label}
          >
            <Icon className="w-4 h-4 mb-0.5 transition-transform group-hover:scale-110" />
            <span className="studio-nav-label">{label}</span>
          </a>
        ))}
      </nav>
      <button
        aria-label="Open history"
        onClick={() => setHistoryOpen(true)}
        className="p-2 rounded-lg text-gray-400 hover:text-coral hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
        title="Document History"
      >
        <History className="w-5 h-5 text-coral" />
      </button>
    </aside>
    <HistoryPanel open={historyOpen} documents={contract.history} busy={busy} onClose={() => setHistoryOpen(false)}
      onRestore={contract.restore} onRemove={contract.remove} onClear={contract.clearHistory} />
    <main className="studio-main">
      <section id="intro" className="studio-section dark-theme justify-between">
        <div className="bg-text-grid"><div>INDIAN REAL ESTATE</div><div>PROPERTY DUE DILIGENCE</div><div>RERA & TITLE CLARITY</div></div>
        <div className="z-10 mt-12">
          {['PROPCHECK AI', 'PROPERTY DUE DILIGENCE', 'FOR INDIAN BUYERS', 'DOCUMENT CLARITY'].map((line, index) => <div key={line} className="mask-container block">
            <h1 className="kinetic-header mask-text" style={{ animationDelay: `${index * 0.2}s` }}>{line}</h1>
          </div>)}
          <p className="max-w-md text-sm leading-relaxed text-studio-gray mt-6">AI-powered property due-diligence platform for Indian homebuyers. Cross-verify sale deeds, allotment letters, carpet area, consideration amounts, and official RERA records.</p>
          <LegalNotice />
        </div>
        <div className="z-10 mt-8"><a href="#upload" className="studio-btn">Get started <ArrowRight className="w-4 h-4" /></a></div>
        <div className="marquee-container w-full mt-12"><div className="marquee-content">PROPCHECK AI · RERA VERIFICATION · CARPET AREA AUDIT · CROSS-DOCUMENT CONSISTENCY · INDIAN REAL ESTATE CLARITY ·</div></div>
      </section>
      <UploadPanel document={contract.document} documents={contract.history} busy={busy} onUpload={contract.upload} status={contract.uploadStatus} />
      <PropCheckDashboard
        documents={contract.history}
        busy={busy}
        onSource={setSource}
        onOpenDoc={contract.restore}
        onRemoveDoc={contract.remove}
        onUpload={contract.upload}
      />
      <DocumentWorkspace revision={contract.history.map(doc => doc.doc_id).join(',')} onOpen={contract.restore} onRemove={contract.remove} onSource={setSource} />
      <BenefitsPanel
        result={contract.benefits}
        available={Boolean(contract.document || contract.history.length > 0)}
        busy={busy}
        analyzing={contract.busy === 'benefits'}
        onAnalyze={contract.analyze}
        document={contract.document}
        documents={contract.history}
        onSelectDocument={contract.restore}
        error={contract.busy === 'benefits' ? contract.error : undefined}
      />
      <ChatPanel
        messages={contract.messages}
        available={Boolean(contract.document || contract.history.length > 0)}
        busy={busy}
        sending={contract.busy === 'chat'}
        onSend={contract.chat}
        draft={contract.draft}
        docId={contract.document?.doc_id || contract.history[0]?.doc_id}
        onSource={setSource}
        document={contract.document}
        documents={contract.history}
        onSelectDocument={contract.restore}
        error={contract.busy === 'chat' ? contract.error : undefined}
      />
      <AuditPanel
        result={contract.audit}
        available={Boolean(contract.document || contract.history.length > 0)}
        busy={busy}
        analyzing={contract.busy === 'audit'}
        onAnalyze={contract.runAudit}
        onSource={setSource}
        document={contract.document}
        documents={contract.history}
        onSelectDocument={contract.restore}
        error={contract.busy === 'audit' ? contract.error : undefined}
      />
      {contract.audit && <div className="bg-[#151515] text-white p-6 md:px-16"><ReportActions key={contract.audit.doc_id} docId={contract.audit.doc_id} sharing={account !== 'local'} /></div>}
    </main>
    {source && <SourceViewer selection={source} onClose={closeSource} />}
    {contract.error && <div role="alert" className="fixed bottom-4 left-24 right-4 z-[80] border border-coral bg-[#151515] text-white p-4 text-sm flex gap-3 shadow-xl">
      <AlertCircle className="w-5 h-5 text-coral shrink-0" /><span>{contract.error}</span>
    </div>}
  </div>;
}
