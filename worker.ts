export interface Env {
  ASSETS: Fetcher;
  BACKEND_URL?: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // 1. Worker API routes: do not intercept API requests with SPA fallback
    if (url.pathname.startsWith('/api/')) {
      if (env.BACKEND_URL) {
        const backendBase = env.BACKEND_URL.replace(/\/+$/, '');
        const targetUrl = new URL(url.pathname + url.search, backendBase);
        const headers = new Headers(request.headers);
        headers.set('Host', new URL(backendBase).host);

        return fetch(new Request(targetUrl.toString(), {
          method: request.method,
          headers: headers,
          body: request.body,
          redirect: 'follow',
        }));
      }

      // If no backend proxy is configured, return JSON 404 rather than serving HTML
      return new Response(
        JSON.stringify({
          error: 'Not Found',
          detail: `API endpoint '${url.pathname}' was not intercepted by SPA. Configure BACKEND_URL in Worker environment if proxying to an external backend.`,
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // 2. Fetch static assets from the compiled build output directory
    let response = await env.ASSETS.fetch(request);

    // 3. SPA Fallback: for navigation GET requests that do not match a static file, serve index.html
    if (response.status === 404 && request.method === 'GET') {
      const acceptHeader = request.headers.get('Accept') || '';
      // Only fallback to index.html for page navigation or requests expecting HTML/plain requests
      if (!url.pathname.includes('.') || acceptHeader.includes('text/html')) {
        const indexRequest = new Request(new URL('/index.html', request.url), request);
        response = await env.ASSETS.fetch(indexRequest);
      }
    }

    return response;
  },
};
