'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { BenefitsResult, Message, StoredDocument } from '@/lib/contracts';
import { loadHistory, saveHistory } from '@/lib/history';
import { Audit, IndiaContext } from '@/lib/audit-contracts';

export function useContract(account = 'local') {
  const readHistory = useCallback(() => loadHistory(localStorage, Date.now(), account), [account]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [document, setDocument] = useState<StoredDocument | null>(null);
  const [history, setHistory] = useState<StoredDocument[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [benefits, setBenefits] = useState<BenefitsResult | null>(null);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [draft, setDraft] = useState('');
  const streamController = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState<'upload' | 'chat' | 'benefits' | 'audit' | 'history' | null>(null);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const pending = useRef(false);

  const remember = useCallback((docs: StoredDocument[]) => {
    saveHistory(docs, localStorage, Date.now(), account);
    setHistory(docs);
  }, [account]);

  useEffect(() => {
    let active = true;
    const localDocs = readHistory();
    setHistory(localDocs);
    if (localDocs.length > 0) {
      setDocument(current => current ?? localDocs[0]);
    }

    api.documents().then(serverDocs => {
      if (!active) return;
      if (serverDocs && serverDocs.length > 0) {
        const merged = [
          ...serverDocs,
          ...localDocs.filter(l => !serverDocs.some(s => s.doc_id === l.doc_id)),
        ].slice(0, 20);
        saveHistory(merged, localStorage, Date.now(), account);
        setHistory(merged);
        setDocument(current => {
          if (current && merged.some(d => d.doc_id === current.doc_id)) {
            return current;
          }
          return serverDocs[0];
        });
      }
    }).catch(() => {
      // Offline fallback: keep localDocs
    });

    return () => {
      active = false;
    };
  }, [readHistory, account]);

  const reset = useCallback(() => {
    generation.current += 1;
    pending.current = false;
    streamController.current?.abort();
    setAudit(null); setDraft('');
    setDocument(null); setMessages([]); setBenefits(null); setBusy(null); setError('');
  }, []);

  useEffect(() => () => { generation.current += 1; streamController.current?.abort(); }, []);

  useEffect(() => {
    if (!document) return;
    const timer = setTimeout(() => {
      reset();
      remember(readHistory());
      setError('This document has expired. Please upload it again.');
    }, Math.max(0, document.expires_at * 1000 - Date.now()));
    return () => clearTimeout(timer);
  }, [document, remember, reset, readHistory]);

  async function run(kind: NonNullable<typeof busy>, operation: (version: number) => Promise<void>, relatedDocId?: string): Promise<boolean> {
    if (pending.current) return false;
    pending.current = true;
    const version = generation.current;
    setBusy(kind); setError('');
    try {
      await operation(version);
      return generation.current === version;
    } catch (failure) {
      if (generation.current === version) {
        if (failure instanceof ApiError && failure.status === 404 && document && document.doc_id === relatedDocId) {
          remember(readHistory().filter(item => item.doc_id !== document.doc_id));
          setDocument(null); setMessages([]); setBenefits(null);
          setAudit(null); setDraft('');
        }
        setError(failure instanceof Error ? failure.message : 'The request failed.');
      }
      return false;
    } finally {
      if (generation.current === version) { pending.current = false; setBusy(null); }
    }
  }

  async function upload(fileOrFiles: File | File[]) {
    const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
    if (files.length === 0) return false;
    return run('upload', async version => {
      let currentHistory = readHistory();
      let lastUploaded: StoredDocument | null = null;
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const prefix = files.length > 1 ? `[${i + 1}/${files.length}] ` : '';
        setUploadStatus(`${prefix}Uploading ${file.name}…`);
        const result = await api.upload(file, status => {
          if (generation.current === version) setUploadStatus(`${prefix}${status}`);
        });
        if (generation.current !== version) return;
        currentHistory = [result, ...currentHistory.filter(item => item.doc_id !== result.doc_id)].slice(0, 20);
        remember(currentHistory);
        lastUploaded = result;
      }
      setUploadStatus('');
      if (lastUploaded) {
        setDocument(lastUploaded);
        setMessages([]);
        setBenefits(null);
        setAudit(null);
      }
    });
  }

  async function restore(item: StoredDocument) {
    await run('history', async version => {
      try {
        const result = await api.document(item.doc_id);
        const saved = await api.savedAudit(item.doc_id).catch(failure => {
          if (failure instanceof ApiError && (failure.status === 409 || failure.status === 404)) return null;
          throw failure;
        });
        if (generation.current !== version) return;
        setDocument(result); setMessages([]); setBenefits(null);
        setAudit(saved?.audit ?? null);
        remember([result, ...readHistory().filter(doc => doc.doc_id !== result.doc_id)].slice(0, 10));
      } catch (failure) {
        if (generation.current === version && failure instanceof ApiError && failure.status === 404) {
          remember(readHistory().filter(doc => doc.doc_id !== item.doc_id));
          setDocument(current => (current?.doc_id === item.doc_id ? null : current));
        }
        throw failure;
      }
    }, item.doc_id);
  }

  async function remove(id: string) {
    await run('history', async version => {
      await api.remove(id);
      if (generation.current !== version) return;
      remember(readHistory().filter(item => item.doc_id !== id));
      if (document?.doc_id === id && generation.current === version) reset();
    });
  }

  async function clearHistory() {
    await run('history', async version => {
      // Forget only after server deletion succeeds, preserving a retry handle on failure.
      for (const item of readHistory()) {
        await api.remove(item.doc_id);
        if (generation.current !== version) return;
        remember(readHistory().filter(doc => doc.doc_id !== item.doc_id));
        if (document?.doc_id === item.doc_id && generation.current === version) {
          setDocument(null); setMessages([]); setBenefits(null);
          setAudit(null);
        }
      }
    });
  }

  async function analyze() {
    let target = document;
    if (!target && history.length > 0) {
      target = history[0];
      setDocument(target);
    }
    if (!target) {
      setError('Upload a document to begin analysis.');
      return;
    }
    await run('benefits', async version => {
      const result = await api.benefits(target.doc_id);
      if (generation.current === version) setBenefits(result);
    }, target.doc_id);
  }

  async function chat(question: string) {
    if (!question.trim()) return false;
    let target = document;
    if (!target && history.length > 0) {
      target = history[0];
      setDocument(target);
    }
    if (!target) {
      setError('Upload a contract to start chatting.');
      return false;
    }
    return run('chat', async version => {
      const controller = new AbortController();
      streamController.current = controller;
      const result = await api.chat(target.doc_id, question.trim(), messages, {
        signal: controller.signal,
        onDraft: text => { if (generation.current === version) setDraft(text); },
      });
      if (generation.current === version) setMessages(previous => [
        ...previous, { role: 'user', content: question.trim() },
        { role: 'assistant', content: result.answer, sources: result.sources },
      ]);
    }, target.doc_id);
  }

  async function runAudit(india: IndiaContext) {
    let target = document;
    if (!target && history.length > 0) {
      target = history[0];
      setDocument(target);
    }
    if (!target) {
      setError('Upload a document to run a clause audit.');
      return;
    }
    await run('audit', async version => {
      const result = await api.audit(target.doc_id, india);
      if (generation.current === version) setAudit(result);
    }, target.doc_id);
  }

  return { document, history, messages, benefits, audit, draft, busy, error, uploadStatus, upload, restore, remove, clearHistory, analyze, chat, runAudit, reset };
}
