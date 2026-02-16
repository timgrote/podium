// Auth guard — include in <head> of every protected ops page.
// Calls GET /api/auth/me; redirects to login only on 401.
// Stores the current user in window.__user for page scripts to use.
(async function () {
    try {
        const res = await fetch('/api/auth/me');
        if (res.status === 401) {
            window.location.href = '/ops/login.html';
            return;
        }
        if (!res.ok) {
            console.error('Auth check failed with status', res.status);
            return;
        }
        window.__user = await res.json();
    } catch (err) {
        console.error('Auth check network error:', err);
    }
})();
