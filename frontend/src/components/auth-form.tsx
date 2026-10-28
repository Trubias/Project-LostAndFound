'use client';

import { useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowRight, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { submitDjangoForm } from '@/lib/django-form';

type AuthMode = 'login' | 'register';

export function AuthForm({ mode, error = false }: { mode: AuthMode; error?: boolean }) {
  const [csrf, setCsrf] = useState('');
  const [csrfError, setCsrfError] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/csrf/', { cache: 'no-store' })
      .then((response) => response.ok ? response.json() as Promise<{ csrfToken: string }> : Promise.reject())
      .then(({ csrfToken }) => { if (!cancelled) setCsrf(csrfToken); })
      .catch(() => { if (!cancelled) setCsrfError(true); });
    return () => { cancelled = true; };
  }, []);

  const isRegister = mode === 'register';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setSubmitting(true);
    const errors = await submitDjangoForm(form);
    setFormErrors(errors);
    if (errors.length) form.querySelectorAll<HTMLInputElement>('input[type="password"]').forEach((input) => { input.value = ''; });
    setSubmitting(false);
  }

  return (
    <form method="post" action={`/api/django/${mode}/`} onSubmit={handleSubmit} className="mt-7 space-y-4">
      <input type="hidden" name="csrfmiddlewaretoken" value={csrf}/>
      {isRegister ? <>
        <Field label="First name" name="first_name" placeholder="Your first name" icon={<UserRound size={16}/>} autoComplete="given-name"/>
        <Field label="Last name" name="last_name" placeholder="Your last name" icon={<UserRound size={16}/>} autoComplete="family-name"/>
        <Field label="Email" name="email" type="email" placeholder="you@example.com" icon={<Mail size={16}/>} autoComplete="email"/>
      </> : null}
      <Field label="Username" name="username" placeholder="Enter your username" icon={<UserRound size={16}/>} autoComplete="username"/>
      <Field label="Password" name="password" type="password" placeholder={isRegister ? 'At least 8 characters' : 'Enter your password'} icon={<LockKeyhole size={16}/>} autoComplete={isRegister ? 'new-password' : 'current-password'}/>
      {!isRegister ? <p className="-mt-2 text-right text-sm"><Link className="font-semibold text-[#55705d] hover:underline" href="/password-reset/">Forgot your password?</Link></p> : null}
      {isRegister ? <Field label="Confirm password" name="confirm_password" type="password" placeholder="Enter your password again" icon={<LockKeyhole size={16}/>} autoComplete="new-password"/> : null}
      {error ? <p role="alert" className="rounded-xl bg-[#f8efea] px-4 py-3 text-sm text-[#915b4e]">{isRegister ? 'We couldn’t create your account with those details. Check the fields and try again.' : 'That username and password didn’t match. Please try again.'}</p> : null}
      {formErrors.length ? <div role="alert" className="space-y-1 rounded-xl bg-[#f8efea] px-4 py-3 text-sm text-[#915b4e]">{formErrors.map((message, index) => <p key={`${index}-${message}`}>{message}</p>)}</div> : null}
      {csrfError ? <p role="alert" className="text-sm text-[#9a5546]">We couldn’t connect to the sign-in service. Please refresh and try again.</p> : null}
      <button disabled={!csrf || submitting} className="mt-2 flex w-full items-center justify-center rounded-xl bg-[#274c3b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#1e3d2f] disabled:cursor-wait disabled:opacity-100">{submitting ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'} <ArrowRight size={15} className="ml-2"/></button>
      <p className="pt-2 text-center text-sm text-[#5d6a61]">{isRegister ? 'Already part of Findly?' : 'New to Findly?'}{' '}
        <Link className="font-semibold text-[#55705d]" href={isRegister ? '/login' : '/register'}>{isRegister ? 'Log in' : 'Create an account'}</Link>
      </p>
    </form>
  );
}

function Field({ label, name, type = 'text', placeholder, icon, autoComplete }: { label: string; name: string; type?: string; placeholder: string; icon: React.ReactNode; autoComplete: string }) {
  return <label className="block text-sm font-semibold text-[#405148]">{label}<span className="relative mt-2 block"><span className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-[#5f6c63]">{icon}</span><input required name={name} type={type} placeholder={placeholder} autoComplete={autoComplete} className="w-full rounded-xl border border-[#e4eae2] bg-white py-3 pl-10 pr-3.5 text-sm font-normal text-[#293b30] outline-none transition placeholder:text-[#a5aea6] focus:border-[#8ba68b] focus:ring-4 focus:ring-[#dce8dc]/60"/></span></label>;
}
