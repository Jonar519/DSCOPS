# DSCOPS Web (Next.js)

Frontend de DSCOPS hecho con **Next.js (App Router) + TypeScript + Tailwind CSS + Motion**.
Reemplaza al antiguo `playground.html`. Tiene dos páginas:

| Ruta | Qué es |
|---|---|
| `/` | Página de inicio: qué es DSCOPS, el lenguaje, las fases del compilador, las reglas y los destinos. |
| `/playground` | Editor para escribir un `.dscops`, validarlo y compilarlo. |

El frontend **no contiene lógica del compilador**: todo lo calcula la API de Python
(`POST /v1/check`, `POST /v1/compile`, `GET /v1/targets`). Así se respeta la regla de
`AGENTS.md`: las interfaces son delgadas.

## Arrancar en desarrollo

Necesitas Node.js 20 o superior y la API de DSCOPS corriendo.

```bash
# Terminal 1: la API de Python (desde la raíz del repo)
uv run dscops serve            # http://127.0.0.1:8000

# Terminal 2: el frontend
cd web
npm install
npm run dev                    # http://localhost:3000
```

Si la API está en otra URL, copia `.env.example` a `.env.local` y cambia `DSCOPS_API_URL`.

Para producción: `npm run build` y luego `npm start`.

## Cómo se conecta con la API

```text
Navegador ──► Next.js (:3000) ──rewrite──► FastAPI (:8000)
              /api/v1/check                /v1/check
              /docs                        /docs
```

`next.config.ts` reenvía todo lo que empieza por `/api` a FastAPI. El navegador
solo habla con Next.js, así que **no hace falta configurar CORS**.

## Estructura

```text
web/
├── next.config.ts              # rewrites hacia la API
└── src/
    ├── app/                    # rutas (App Router)
    │   ├── layout.tsx          # fuentes y <html>
    │   ├── globals.css         # colores, retícula de fondo, subrayados
    │   ├── page.tsx            # "/"
    │   └── playground/page.tsx # "/playground"
    ├── hooks/
    │   └── useCompiler.ts      # TODO el estado del playground (llamadas a la API)
    ├── lib/
    │   ├── api.ts              # cliente HTTP (fetch)
    │   ├── types.ts            # tipos espejo de schemas.py
    │   ├── highlight.ts        # resaltado de sintaxis (dscops, yaml, hcl)
    │   ├── samples.ts          # ejemplos del playground
    │   └── catalog.ts          # reglas y destinos que se muestran en la web
    └── components/
        ├── ui/                 # piezas reutilizables (Button, Frame, Code, Icons…)
        ├── site/               # Nav y Footer de la página de inicio
        ├── landing/            # secciones de la página de inicio
        └── playground/         # Editor, Findings, Artifacts, Toolbar, Playground
```

Regla de lectura: **los componentes solo pintan; el estado vive en `useCompiler`**.
Si quieres saber qué pasa al pulsar "Compilar", empieza por `hooks/useCompiler.ts`.

## Detalles del playground

- **Validación automática**: 600 ms después de dejar de escribir se llama a `/v1/check`.
  Si llegan respuestas fuera de orden, solo se usa la última (`requestId`).
- **Editor**: un `<textarea>` transparente encima del código coloreado
  (ver comentario en `components/playground/Editor.tsx`). Sin librerías.
- **Hallazgos**: cada uno se puede pulsar para seleccionar el fragmento en el editor.
  Los contadores de arriba filtran por severidad.
- **Atajos**: `Ctrl+Enter` compila, `Ctrl+Shift+Enter` valida.
- **Movimiento reducido**: si el sistema lo pide, la demo de la portada se muestra ya terminada.

## Diseño

Estilo "plano técnico": fondo azul con retícula y marcas de registro en las
esquinas de los paneles (`components/ui/Frame.tsx`). Tipografía IBM Plex Sans y
IBM Plex Mono. Los colores tienen nombres por su función en `globals.css`:

| Token | Uso |
|---|---|
| `ink` | fondo |
| `paper` / `pencil` | texto principal / secundario |
| `amber` | acción principal y advertencias |
| `fail` / `pass` / `sky` | errores / correcto / avisos |
