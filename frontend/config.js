// Backend API Configuration
// Auto-detect environment based on hostname
(function() {
    const hostname = window.location.hostname;

    // Development environment: develop.hed-bot.pages.dev
    const isDev = hostname.startsWith('develop.') ||
                  hostname.includes('localhost') ||
                  hostname.includes('127.0.0.1');

    if (isDev) {
        // Dev backend (direct connection to dev API)
        window.BACKEND_URL = 'https://hedtools.org/hed-bot-dev-api';
        // Turnstile testing key (always passes) - pairs with testing secret key
        window.TURNSTILE_SITE_KEY = '1x00000000000000000000AA';
        console.log('[HED-BOT] Using DEV backend:', window.BACKEND_URL);
    } else {
        // Production backend (direct connection to prod API)
        window.BACKEND_URL = 'https://hedtools.org/hed-bot-api';
        // Production Turnstile site key
        window.TURNSTILE_SITE_KEY = '0x4AAAAAACEkzthaT1R2kLIF';
    }
})();
