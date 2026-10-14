// Clipboard API requires HTTPS; the fallback also supports the platform's HTTP deployment.
export async function copyText(value) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(String(value));
      return true;
    }
  } catch { /* Try the browser's legacy copy action below. */ }
  const field = document.createElement('textarea');
  field.value = String(value);
  field.style.cssText = 'position:fixed;left:-9999px;top:0';
  const previous = document.activeElement;
  document.body.appendChild(field);
  try { field.select(); return document.execCommand('copy'); }
  catch { return false; }
  finally { field.remove(); previous?.focus?.({ preventScroll: true }); }
}
