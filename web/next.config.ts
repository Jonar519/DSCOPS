import type { NextConfig } from "next";

/**
 * El frontend no habla directamente con FastAPI desde el navegador.
 * Next.js reenvía (rewrite) las rutas de abajo a la API de Python, así:
 *   - no hace falta configurar CORS en FastAPI;
 *   - el navegador solo conoce una URL (la de Next.js).
 *
 * Cambia la URL de la API con la variable de entorno DSCOPS_API_URL.
 */
const API_URL = process.env.DSCOPS_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // /api/v1/check  ->  http://127.0.0.1:8000/v1/check
      { source: "/api/:path*", destination: `${API_URL}/:path*` },
      // Swagger UI de FastAPI y el esquema que carga.
      { source: "/docs", destination: `${API_URL}/docs` },
      { source: "/openapi.json", destination: `${API_URL}/openapi.json` },
    ];
  },
};

export default nextConfig;
