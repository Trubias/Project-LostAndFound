'use client';

import { useEffect, useState, type ChangeEvent, type FormEvent, type TouchEvent } from 'react';
import { ArrowRight } from 'lucide-react';
import { submitDjangoForm } from '@/lib/django-form';

export type FormField = { name: string; label: string; type: string; required?: boolean; value?: string; placeholder?: string; options?: { value: string | number; label: string }[] };
type Suggestion = { id: number; title: string; description: string; location: string; room: string; category: string; image: string | null; href: string; score: number; photoSimilarity: number; photoMatch: boolean };
type SuggestionsResponse = { results: Suggestion[] };
type PreviewInput = { title: string; description: string; category: string; location: string; building: string; room: string; workstation: string; date: string; image: File | null };

const emptyPreview: PreviewInput = { title: '', description: '', category: '', location: '', building: '', room: '', workstation: '', date: '', image: null };

export function BackendForm({ action, actionLabel, fields, error = false }: { action: string; actionLabel?: string; fields: FormField[]; error?: boolean }) {
  const [csrf, setCsrf] = useState('');
  const [previewInput, setPreviewInput] = useState<PreviewInput>(emptyPreview);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [matching, setMatching] = useState(false);
  const [suggestionError, setSuggestionError] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState(0);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const reportAction = action.replace(/\/$/, '');
  const showMatchPanel = reportAction === '/items/report/found' || reportAction === '/items/report/lost';
  const reportType = reportAction.endsWith('/lost') ? 'LOST' : 'FOUND';
  const errorMessage = reportAction === '/profile'
    ? 'Your profile was not saved. Review the details and make sure the photo is a supported image.'
    : reportAction.startsWith('/claims/item/')
      ? 'Your claim was not submitted. Review the details and try again.'
      : showMatchPanel
        ? 'Your report was not saved. Review the required fields and try again. A match is not required to post.'
        : reportAction.startsWith('/items/') && reportAction.endsWith('/edit')
          ? 'Your report changes were not saved. Review the required fields and try again.'
          : 'We could not save your changes. Review the fields and try again.';
  const readyToMatch = showMatchPanel && Boolean(
    previewInput.title.trim() && previewInput.description.trim() && previewInput.category &&
    previewInput.location && previewInput.date,
  );

  useEffect(() => {
    let cancelled = false;
    fetch('/api/csrf/', { cache: 'no-store' })
      .then((response) => response.ok ? response.json() as Promise<{ csrfToken: string }> : Promise.reject())
      .then(({ csrfToken }) => { if (!cancelled) setCsrf(csrfToken); })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!showMatchPanel || !csrf) return;
    if (!readyToMatch) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      const payload = new FormData();
      payload.set('csrfmiddlewaretoken', csrf);
      payload.set('item_type', reportType);
      for (const key of ['title', 'description', 'category', 'location', 'building', 'room', 'workstation'] as const) payload.set(key, previewInput[key]);
      payload.set('date_occurred', previewInput.date);
      if (previewInput.image) payload.set('image', previewInput.image);
      setMatching(true);
      setSuggestionError(false);
      try {
        const response = await fetch('/api/django/api/match-suggestions/', { method: 'POST', body: payload, cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error('Could not load suggestions');
        const result = await response.json() as SuggestionsResponse;
        setSuggestions(result.results);
        setActiveSuggestion(0);
      } catch {
        if (!controller.signal.aborted) setSuggestionError(true);
      } finally {
        if (!controller.signal.aborted) setMatching(false);
      }
    }, 450);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [csrf, previewInput, readyToMatch, reportType, showMatchPanel]);

  function updatePreview(event: ChangeEvent<HTMLFormElement>) {
    if (!showMatchPanel) return;
    setSuggestions([]);
    setSuggestionError(false);
    setMatching(false);
    const data = new FormData(event.currentTarget);
    const file = data.get('image');
    setPreviewInput({
      title: String(data.get('title') ?? ''),
      description: String(data.get('description') ?? ''),
      category: String(data.get('category') ?? ''),
      location: String(data.get('location') ?? ''),
      building: String(data.get('building') ?? ''),
      room: String(data.get('room') ?? ''),
      workstation: String(data.get('workstation') ?? ''),
      date: String(data.get('date_occurred') ?? ''),
      image: file instanceof File && file.size > 0 ? file : null,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFormErrors(await submitDjangoForm(event.currentTarget));
    setSubmitting(false);
  }

  const renderFields = () => fields.map((field) => <label key={field.name} className="block text-sm font-semibold text-[#405148]">{field.label}{field.required ? <span aria-hidden="true" className="ml-1 text-[#9c695b]">*</span> : null}
    {field.type === 'textarea' ? <textarea required={field.required} name={field.name} defaultValue={field.value} rows={4} className="mt-2 w-full resize-y rounded-xl border border-[#e4eae2] bg-white px-4 py-3 text-sm font-normal outline-none transition placeholder:text-[#a5aea6] focus:border-[#8ba68b] focus:ring-4 focus:ring-[#dce8dc]/60"/> : field.type === 'select' ? <select required={field.required} name={field.name} defaultValue={field.value ?? ''} className="mt-2 w-full rounded-xl border border-[#e4eae2] bg-white px-4 py-3 text-sm font-normal outline-none focus:border-[#8ba68b] focus:ring-4 focus:ring-[#dce8dc]/60"><option value="">{field.placeholder ?? 'Choose an option'}</option>{field.value && !field.options?.some((option) => String(option.value) === field.value) ? <option value={field.value}>{field.value}</option> : null}{field.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select> : <input required={field.required} name={field.name} type={field.type} accept={field.type === 'file' ? 'image/*' : undefined} defaultValue={field.type === 'file' ? undefined : field.value} className="mt-2 w-full rounded-xl border border-[#e4eae2] bg-white px-4 py-3 text-sm font-normal outline-none transition file:mr-3 file:rounded-lg file:border-0 file:bg-[#eff4eb] file:px-3 file:py-2 file:text-xs file:font-semibold file:text-[#52765b] focus:border-[#8ba68b] focus:ring-4 focus:ring-[#dce8dc]/60"/>}
  </label>);

  return <form method="post" encType="multipart/form-data" action={`/api/django${action.endsWith('/') ? action : `${action}/`}`} onSubmit={handleSubmit} onChange={showMatchPanel ? updatePreview : undefined} className={readyToMatch ? 'grid items-start gap-6 xl:grid-cols-[minmax(0,48rem)_310px]' : 'space-y-5'}>
    <input type="hidden" name="csrfmiddlewaretoken" value={csrf}/>
    {error ? <p role="alert" className={`rounded-xl bg-[#f8efea] px-4 py-3 text-sm leading-6 text-[#915b4e] ${showMatchPanel ? 'xl:col-span-full' : ''}`}>{errorMessage}</p> : null}
    {formErrors.length ? <div role="alert" className={`space-y-1 rounded-xl bg-[#f8efea] px-4 py-3 text-sm leading-6 text-[#915b4e] ${showMatchPanel ? 'xl:col-span-full' : ''}`}>{formErrors.map((message, index) => <p key={`${index}-${message}`}>{message}</p>)}</div> : null}
    {showMatchPanel ? <><div className="max-w-3xl space-y-5 rounded-2xl border border-[#e8ece5] bg-white p-6 md:p-8">{renderFields()}<SubmitButton csrf={csrf} label={actionLabel} submitting={submitting}/></div>{readyToMatch ? <MatchPanel suggestions={suggestions} matching={matching} error={suggestionError} reportType={reportType} activeIndex={activeSuggestion} setActiveIndex={setActiveSuggestion} touchStart={touchStart} setTouchStart={setTouchStart}/>: null}</> : <>{renderFields()}<SubmitButton csrf={csrf} label={actionLabel} submitting={submitting}/></>}
  </form>;
}

function SubmitButton({ csrf, label = 'Continue', submitting }: { csrf: string; label?: string; submitting: boolean }) {
  return <button disabled={!csrf || submitting} className="inline-flex items-center rounded-xl bg-[#274c3b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#1e3d2f] disabled:cursor-wait disabled:opacity-100">{submitting ? 'Please wait…' : label} <ArrowRight size={15} className="ml-2"/></button>;
}

function MatchPanel({ suggestions, matching, error, reportType, activeIndex, setActiveIndex, touchStart, setTouchStart }: {
  suggestions: Suggestion[];
  matching: boolean;
  error: boolean;
  reportType: 'LOST' | 'FOUND';
  activeIndex: number;
  setActiveIndex: React.Dispatch<React.SetStateAction<number>>;
  touchStart: number | null;
  setTouchStart: (value: number | null) => void;
}) {
  const comparedType = reportType === 'LOST' ? 'found' : 'lost';
  const current = suggestions[activeIndex];

  function finishSwipe(event: TouchEvent<HTMLDivElement>) {
    if (touchStart === null || suggestions.length < 2) return;
    const distance = event.changedTouches[0].clientX - touchStart;
    if (Math.abs(distance) > 45) {
      setActiveIndex((index) => (index + (distance < 0 ? 1 : suggestions.length - 1)) % suggestions.length);
    }
    setTouchStart(null);
  }

  return <aside aria-live="polite" className="w-full max-w-3xl rounded-2xl border border-[#e3e9df] bg-[#f4f7f1] p-5 xl:sticky xl:top-5 xl:w-[310px]">
    <div><p className="text-sm font-bold text-[#34483a]">Possible matches</p><p className="mt-1 text-[11px] leading-5 text-[#78867c]">Comparing your {reportType.toLowerCase()} report with active {comparedType} reports.</p></div>
    {matching ? <p className="mt-5 flex items-center gap-2 text-xs font-medium text-[#66806b]"><span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-[#709b75]"/>Checking report details...</p> : null}
    {error ? <p role="status" className="mt-5 rounded-xl bg-white p-3 text-xs leading-5 text-[#8a6957]">Matches could not load right now. You can still submit your report.</p> : null}
    {!matching && !error && current ? <div className="mt-5">
      <div className="mb-2 flex items-center justify-between gap-2"><p className="text-[10px] font-semibold uppercase tracking-wide text-[#718078]">Match {activeIndex + 1} of {suggestions.length}</p>{suggestions.length > 1 ? <div className="flex gap-2"><button type="button" onClick={() => setActiveIndex((index) => (index + suggestions.length - 1) % suggestions.length)} className="rounded-lg border border-[#dce5da] bg-white px-2.5 py-1.5 text-[10px] font-semibold text-[#49624f] hover:bg-[#f9fbf8]">Previous</button><button type="button" onClick={() => setActiveIndex((index) => (index + 1) % suggestions.length)} className="rounded-lg border border-[#dce5da] bg-white px-2.5 py-1.5 text-[10px] font-semibold text-[#49624f] hover:bg-[#f9fbf8]">Next</button></div> : null}</div>
      <div onTouchStart={(event) => setTouchStart(event.touches[0].clientX)} onTouchEnd={finishSwipe} className="touch-pan-y">
        <a href={current.href} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-xl border border-[#e0e8dd] bg-white transition hover:border-[#b9cbb8]">
          {current.image ? <img src={current.image} alt={`Photo for ${current.title}`} className="h-36 w-full object-cover"/> : <div className="grid h-24 place-items-center bg-[#edf2e9] text-[11px] text-[#87978a]">No photo provided</div>}
          <div className="p-4"><div className="flex items-start justify-between gap-2"><h3 className="text-sm font-bold leading-5 text-[#34483a]">{current.title}</h3><span className="shrink-0 rounded-full bg-[#edf4e9] px-2 py-1 text-[10px] font-bold text-[#52765b]">{current.photoMatch ? `${current.photoSimilarity}% photo` : `${current.score}% match`}</span></div>
            <p className="mt-2 text-[11px] leading-5 text-[#68766d]">{current.description}</p><p className="mt-3 border-t border-[#edf0eb] pt-3 text-[10px] text-[#5d6a61]">{current.category} · {current.room || current.location}</p>
          </div>
        </a>
      </div>
      {suggestions.length > 1 ? <p className="mt-2 text-center text-[10px] text-[#839087]">Swipe the card or use Previous / Next to review matches.</p> : null}
      {current.photoMatch ? <p className="mt-3 text-[10px] leading-4 text-[#78917a]">Similar photo. Review the description and identifying details before contacting the reporter.</p> : null}
    </div> : null}
    {!matching && !error && !current ? <div className="mt-5 rounded-xl border border-dashed border-[#d7e1d5] bg-white/75 p-4"><p className="text-xs font-semibold text-[#54685a]">No close matches found</p><p className="mt-1 text-[11px] leading-5 text-[#849087]">We compare the title, description, category, location, date, and photo when available.</p></div> : null}
    <p className="mt-4 text-[10px] leading-4 text-[#98a198]">A suggested match is only a clue. Verify the item&apos;s identifying details.</p>
  </aside>;
}
