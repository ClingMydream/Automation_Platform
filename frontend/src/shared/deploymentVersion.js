// Used by both the lightweight login entry and the authenticated workspace.
export async function reloadWhenDeploymentChanges(onAvailable) {
  try {
    const current = document.querySelector('script[type="module"][src]')?.getAttribute('src') || '';
    const response = await fetch(`/?version_check=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) return;
    const html = await response.text();
    const next = html.match(/<script[^>]+type=["']module["'][^>]+src=["']([^"']+)["']/)?.[1] || '';
    if (next && current && next !== current) onAvailable(true);
  } catch { /* A failed version check must not interrupt the user's work. */ }
}
