'use client';

import { createClient, Session } from '@supabase/supabase-js';
import { FormEvent, ReactNode, useEffect, useState } from 'react';
import { configureAuth } from '@/lib/auth-session';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
const required = process.env.NEXT_PUBLIC_AUTH_REQUIRED === 'true' || !!url;
const client = url && publishableKey ? createClient(url, publishableKey, {
  auth: { persistSession: false, autoRefreshToken: true, detectSessionInUrl: false },
}) : null;

export function AuthGate({ children }: { children: (account: string) => ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(!!client);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    if (!client) return;
    const auth = client.auth;
    let previousAccount: string | undefined;
    const { data } = auth.onAuthStateChange((_event, current) => {
      if (previousAccount !== current?.user.id) {
        configureAuth(current ? async () => (await auth.getSession()).data.session?.access_token || null : null);
        previousAccount = current?.user.id;
      }
      setSession(current); setLoading(false);
    });
    return () => { data.subscription.unsubscribe(); configureAuth(null); };
  }, []);

  if (!required) return <>{children('local')}</>;
  if (!client) return <main className="p-12"><h1>Sign-in setup is incomplete</h1><p>The site administrator must configure authentication before documents can be opened.</p></main>;
  if (loading) return <p role="status" className="p-12">Checking your session…</p>;
  if (session) return <>
    <div className="fixed right-4 top-4 z-[90] bg-[#151515] text-white p-3 text-xs flex gap-4 items-center">
      <span>{session.user.email}</span>
      <button onClick={() => { configureAuth(null); setSession(null); void client.auth.signOut(); }}>Sign out</button>
    </div>
    {children(session.user.id)}
  </>;

  async function submit(event: FormEvent, signup = false) {
    event.preventDefault();
    if (!client || busy) return;
    setBusy(true); setNotice('');
    try {
      const result = signup ? await client.auth.signUp({ email, password }) : await client.auth.signInWithPassword({ email, password });
      if (result.error) setNotice(signup ? 'Account creation could not complete. Check the details and try again.' : 'Sign-in failed. Check your email and password.');
      else if (signup && !result.data.session) setNotice('Check your email to confirm your account, then sign in here.');
      setPassword('');
    } catch { setNotice('Authentication is temporarily unavailable. Please retry.'); }
    finally { setBusy(false); }
  }
  return <main className="min-h-screen bg-[#f4f1ea] text-[#151515] grid place-items-center p-6">
    <form onSubmit={submit} className="w-full max-w-md border border-black/15 bg-white/70 rounded-2xl p-8 space-y-5 shadow-lg">
      <p className="text-xs uppercase tracking-widest text-[#151515]/60 font-mono font-semibold">ContractIQ</p>
      <h1 className="text-3xl font-bold tracking-tight">Your Contracts, Your Workspace</h1>
      <p className="text-sm text-[#151515]/75 leading-relaxed">Sign in to upload and review your documents. Sessions stay in this browser tab.</p>
      <label className="block text-xs font-bold uppercase tracking-wider text-[#151515]">
        Email
        <input
          className="block w-full border border-black/20 bg-white/90 hover:bg-white focus:bg-white focus:border-coral focus:ring-2 focus:ring-coral/20 rounded-xl p-3 mt-1.5 text-sm outline-none transition-all shadow-sm"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
      </label>
      <label className="block text-xs font-bold uppercase tracking-wider text-[#151515]">
        Password
        <input
          className="block w-full border border-black/20 bg-white/90 hover:bg-white focus:bg-white focus:border-coral focus:ring-2 focus:ring-coral/20 rounded-xl p-3 mt-1.5 text-sm outline-none transition-all shadow-sm"
          type="password"
          autoComplete="current-password"
          minLength={8}
          required
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
      </label>
      <button className="studio-btn" disabled={busy} type="submit">{busy ? 'Please wait…' : 'Sign in'}</button>
      <button className="block underline text-sm text-[#151515]/70 hover:text-[#151515] font-medium" disabled={busy || !email || password.length < 8} type="button" onClick={e => void submit(e, true)}>Create an account</button>
      {notice && <p role="alert" className="text-xs p-3 rounded-lg border border-coral/30 bg-coral/10 text-coral">{notice}</p>}
    </form>
  </main>;
}
