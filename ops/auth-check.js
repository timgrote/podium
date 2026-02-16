// Auth guard — include in <head> of every protected ops page.
// Calls GET /api/auth/me; redirects to login if unauthenticated.
// Stores the current user in window.__user for page scripts to use.
(async function () {
    try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) throw new Error('Not authenticated');
        window.__user = await res.json();
    } catch {
        window.location.href = '/ops/login.html';
    }
})();
