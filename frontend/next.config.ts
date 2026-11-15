import type { NextConfig } from "next";

/*
 * Cabeceras de seguridad en todas las respuestas. La política de contenido no
 * limita los scripts (Next inserta algunos en línea); solo impide que la página
 * se incruste en otra, que se cambie su dirección base, los complementos y que
 * un formulario envíe datos a otro sitio.
 */
const SECURITY_HEADERS = [
  {
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'",
  },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  cacheComponents: true,
  // Sin la cabecera X-Powered-By: no anuncia con qué está hecho el sitio.
  poweredByHeader: false,
  async headers() {
    return [{ source: "/(.*)", headers: SECURITY_HEADERS }];
  },
  images: {
    // Fotos de perfil de las cuentas de Google.
    remotePatterns: [{ protocol: "https", hostname: "**.googleusercontent.com" }],
  },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
