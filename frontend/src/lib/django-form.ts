/** Submit Django forms without replacing the form on validation errors. */
export async function submitDjangoForm(form: HTMLFormElement): Promise<string[]> {
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      credentials: 'same-origin',
      cache: 'no-store',
      redirect: 'manual',
    });

    const location = response.headers.get('location');
    if (response.status >= 300 && response.status < 400 && location) {
      const destination = new URL(location, window.location.href);
      if (destination.origin === window.location.origin) {
        window.location.assign(destination.href);
        return [];
      }
      return ['The sign-in service returned an invalid redirect. Please try again.'];
    }

    if ((response.headers.get('content-type') ?? '').includes('application/json')) {
      const result = await response.json() as { redirect?: string; detail?: string };
      if (result.redirect) {
        window.location.assign(result.redirect);
        return [];
      }
      if (result.detail) return [result.detail];
    }

    if ((response.headers.get('content-type') ?? '').includes('text/html')) {
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      const errors = Array.from(parsed.querySelectorAll('.alert-danger, .alert-error, .invalid-feedback, .errorlist, .text-danger.small'))
        .map((element) => element.textContent?.replace(/\s+/g, ' ').trim() ?? '')
        .filter(Boolean);
      const uniqueErrors = [...new Set(errors)];
      if (uniqueErrors.length) return uniqueErrors;
    }

    return [response.ok ? 'Please review the form and try again.' : `The request failed (${response.status}). Please try again.`];
  } catch {
    return ['The service could not be reached. Your entries are still here; please try again.'];
  }
}
