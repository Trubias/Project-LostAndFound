'use client';

import { useEffect, useState } from 'react';
import { Check, ChevronDown, Clock3, FlaskConical, Play, RefreshCw, X } from 'lucide-react';

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';
type ProbeResult = {
  endpoint_id: string;
  endpoint: string;
  method: Method;
  request: { path: string; path_parameters: string[]; query_parameters: Record<string, string>; payload: Record<string, unknown> | null };
  response: { status: number | null; headers: Record<string, string>; body: string };
  duration_ms: number;
  database_changed: boolean;
  status_result: 'passed' | 'failed';
  error: string;
};
type TestRun = {
  id: number;
  status: 'running' | 'passed' | 'failed';
  requested_by: string;
  endpoint_id: string;
  http_method: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number;
  passed_count: number;
  failed_count: number;
  results?: ProbeResult[];
  output?: string;
};
type Endpoint = {
  id: string;
  name: string;
  pattern: string;
  sample_path: string;
  path_parameters: string[];
  query_parameters: string[];
  body_parameters: string[];
  methods: Method[];
  last_results: Partial<Record<Method, ProbeResult>>;
};
type ConsoleResponse = { endpoints: Endpoint[]; history: TestRun[] };

const methods: Method[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'];

async function readError(response: Response) {
  const data = await response.json().catch(() => ({})) as { detail?: string };
  return data.detail ?? `Request failed (${response.status}).`;
}

function methodStyle(result?: ProbeResult) {
  if (!result) return 'border-[#e4eae2] bg-white text-[#77847b] hover:border-[#9db39e]';
  if (result.status_result === 'failed') return 'border-[#efd3cd] bg-[#fbf1ef] text-[#a14f41]';
  if (result.response.status === 405) return 'border-[#e4eae2] bg-[#f5f6f3] text-[#87938a]';
  return 'border-[#cfe0d0] bg-[#eff5ee] text-[#52765b]';
}

export function ApiTestDashboard() {
  const [data, setData] = useState<ConsoleResponse | null>(null);
  const [selectedRun, setSelectedRun] = useState<TestRun | null>(null);
  const [csrfToken, setCsrfToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  async function loadConsole() {
    const response = await fetch('/api/django/api/test-console/', { cache: 'no-store' });
    if (!response.ok) throw new Error(await readError(response));
    setData(await response.json() as ConsoleResponse);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [csrfResponse, consoleResponse] = await Promise.all([
          fetch('/api/csrf/', { cache: 'no-store' }),
          fetch('/api/django/api/test-console/', { cache: 'no-store' }),
        ]);
        if (!csrfResponse.ok) throw new Error(await readError(csrfResponse));
        if (!consoleResponse.ok) throw new Error(await readError(consoleResponse));
        const csrf = await csrfResponse.json() as { csrfToken: string };
        const consoleData = await consoleResponse.json() as ConsoleResponse;
        if (!cancelled) {
          setCsrfToken(csrf.csrfToken);
          setData(consoleData);
          setLoading(false);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : 'Could not load the API test console.');
          setLoading(false);
        }
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  async function startRun(selection: { all?: boolean; endpoint_id?: string; method?: Method }) {
    if (running) return;
    setRunning(true);
    setError('');
    setSelectedRun(null);
    try {
      const response = await fetch('/api/django/api/test-console/run/', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(selection),
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(await readError(response));
      const result = await response.json() as { run: TestRun };
      setSelectedRun(result.run);
      await loadConsole();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The API test run could not be completed.');
    } finally {
      setRunning(false);
    }
  }

  async function showRun(run: TestRun) {
    setError('');
    try {
      const response = await fetch(`/api/django/api/test-console/runs/${run.id}/`, { cache: 'no-store' });
      if (!response.ok) throw new Error(await readError(response));
      const result = await response.json() as { run: TestRun };
      setSelectedRun(result.run);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load this test run.');
    }
  }

  if (loading) return <div className="mt-8 rounded-2xl border border-[#e8ece5] bg-white p-6 text-sm text-[#718078]">Loading discovered API endpoints…</div>;

  return <div className="mt-8 space-y-7">
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[#e8ece5] bg-white p-5">
      <div><h2 className="font-semibold">Isolated API test console</h2><p className="mt-1 text-xs leading-5 text-[#718078]">Requests run against Django’s disposable SQLite test database. Outbound network access is blocked; production databases are not supported.</p></div>
      <button type="button" disabled={running || !csrfToken} onClick={() => void startRun({ all: true })} className="inline-flex items-center gap-2 rounded-xl bg-[#274c3b] px-4 py-3 text-sm font-semibold text-white disabled:cursor-wait disabled:opacity-60"><Play size={15}/>{running ? 'Running tests…' : 'Run full API suite'}</button>
    </div>

    {error ? <div role="alert" className="rounded-xl border border-[#efd3cd] bg-[#fbf1ef] px-4 py-3 text-sm text-[#a14f41]">{error}</div> : null}

    {data ? <section className="overflow-hidden rounded-2xl border border-[#e8ece5] bg-white">
      <div className="flex items-center justify-between border-b border-[#edf0eb] px-5 py-4"><div><h2 className="font-semibold">Discovered endpoints</h2><p className="mt-1 text-xs text-[#87938a]">{data.endpoints.length} URL patterns · seven HTTP methods probed per endpoint</p></div><button type="button" aria-label="Refresh endpoint list" onClick={() => void loadConsole().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Refresh failed.'))} className="rounded-lg p-2 text-[#718078] hover:bg-[#f4f6f2]"><RefreshCw size={16}/></button></div>
      <div className="divide-y divide-[#edf0eb]">
        {data.endpoints.map((endpoint) => <details key={endpoint.id} className="group px-5 py-4">
          <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
            <span className="min-w-0"><span className="block break-all text-sm font-semibold text-[#34453b]">{endpoint.pattern}</span><span className="mt-1 block text-xs text-[#87938a]">{endpoint.name} · sample {endpoint.sample_path}</span></span>
            <span className="flex items-center gap-2 text-[#718078]"><span className="hidden text-xs sm:inline">Test endpoint</span><ChevronDown size={16} className="transition group-open:rotate-180"/></span>
          </summary>
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap gap-2">
              {methods.map((method) => {
                const result = endpoint.last_results[method];
                return <button key={method} type="button" disabled={running || !csrfToken} onClick={() => void startRun({ endpoint_id: endpoint.id, method })} title={result ? `Last response: ${result.response.status ?? 'error'} (${result.duration_ms} ms)` : `Run ${method} test`} className={`rounded-lg border px-3 py-2 text-xs font-bold disabled:cursor-wait disabled:opacity-50 ${methodStyle(result)}`}>{method}{result ? ` · ${result.response.status ?? 'ERR'}` : ''}</button>;
              })}
            </div>
            <p className="text-xs text-[#87938a]">Path parameters: {endpoint.path_parameters.length ? endpoint.path_parameters.join(', ') : 'none'} · Query parameters: {endpoint.query_parameters.length ? endpoint.query_parameters.join(', ') : 'none declared'} · Body parameters: {endpoint.body_parameters.length ? endpoint.body_parameters.join(', ') : 'none'}.</p>
          </div>
        </details>)}
        {!data.endpoints.length ? <p className="p-5 text-sm text-[#718078]">No API URL patterns were discovered.</p> : null}
      </div>
    </section> : null}

    <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(300px,.7fr)]">
      <div className="rounded-2xl border border-[#e8ece5] bg-white">
        <div className="border-b border-[#edf0eb] px-5 py-4"><h2 className="font-semibold">Test result</h2></div>
        {selectedRun ? <div className="space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-3"><span className={`rounded-full px-3 py-1 text-xs font-bold ${selectedRun.status === 'passed' ? 'bg-[#eff5ee] text-[#52765b]' : 'bg-[#fbf1ef] text-[#a14f41]'}`}>{selectedRun.status.toUpperCase()}</span><span className="text-xs text-[#718078]">{selectedRun.passed_count} passed · {selectedRun.failed_count} failed · {selectedRun.duration_ms} ms</span></div>
          {selectedRun.results?.map((result, index) => <details key={`${result.endpoint_id}-${result.method}-${index}`} className="rounded-xl border border-[#edf0eb] p-4">
            <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 text-xs"><span className="font-bold">{result.method} {result.endpoint}</span><span className={`inline-flex items-center gap-1 ${result.status_result === 'passed' ? 'text-[#52765b]' : 'text-[#a14f41]'}`}>{result.status_result === 'passed' ? <Check size={14}/> : <X size={14}/>}HTTP {result.response.status ?? 'ERROR'} · {result.duration_ms} ms</span></summary>
            <div className="mt-3 space-y-2 text-xs">
              <p><strong>Request:</strong> {result.request.path} {result.request.payload ? JSON.stringify(result.request.payload) : ''}</p>
              <p><strong>Headers:</strong> {JSON.stringify(result.response.headers)}</p>
              {result.database_changed ? <p className="text-[#9b7042]">Database changes detected and rolled back in the test database.</p> : null}
              {result.error ? <pre className="overflow-auto rounded-lg bg-[#fbf1ef] p-3 whitespace-pre-wrap text-[#a14f41]">{result.error}</pre> : null}
              <pre className="max-h-64 overflow-auto rounded-lg bg-[#f5f7f3] p-3 whitespace-pre-wrap break-words text-[#536158]">{result.response.body || '(empty response body)'}</pre>
            </div>
          </details>)}
          {selectedRun.output ? <details className="rounded-xl border border-[#edf0eb] p-4"><summary className="cursor-pointer text-xs font-semibold">Suite output</summary><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-[#536158]">{selectedRun.output}</pre></details> : null}
        </div> : <div className="p-5 text-sm text-[#87938a]"><FlaskConical size={18} className="mb-2"/>Run a method or the full suite to see real HTTP responses and execution details here.</div>}
      </div>

      <div className="rounded-2xl border border-[#e8ece5] bg-white">
        <div className="flex items-center justify-between border-b border-[#edf0eb] px-5 py-4"><h2 className="font-semibold">Run history</h2><span className="text-xs text-[#87938a]">{data?.history.length ?? 0} recent</span></div>
        <div className="divide-y divide-[#edf0eb]">
          {data?.history.map((run) => <button key={run.id} type="button" onClick={() => void showRun(run)} className="block w-full px-5 py-4 text-left hover:bg-[#fafbf9]"><span className="flex items-center justify-between gap-2"><span className={`text-xs font-bold ${run.status === 'passed' ? 'text-[#52765b]' : run.status === 'failed' ? 'text-[#a14f41]' : 'text-[#9b7042]'}`}>{run.status.toUpperCase()}</span><span className="inline-flex items-center gap-1 text-xs text-[#87938a]"><Clock3 size={13}/>{run.duration_ms} ms</span></span><span className="mt-1 block truncate text-xs text-[#536158]">{run.endpoint_id ? `${run.http_method || 'ALL'} ${run.endpoint_id}` : 'Full API suite'}</span><span className="mt-1 block text-[11px] text-[#98a39b]">{new Date(run.started_at).toLocaleString()} · {run.passed_count} passed / {run.failed_count} failed</span></button>)}
          {!data?.history.length ? <p className="p-5 text-sm text-[#87938a]">No test runs yet.</p> : null}
        </div>
      </div>
    </section>
  </div>;
}
