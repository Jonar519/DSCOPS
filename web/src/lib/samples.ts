/** Ejemplos que se pueden cargar en el playground. */

export interface Sample {
  id: string;
  label: string;
  description: string;
  source: string;
}

export const SAMPLES: Sample[] = [
  {
    id: "secure",
    label: "Infraestructura segura",
    description: "Pasa todas las reglas y compila.",
    source: `# Infraestructura segura y compilable
service api {
  image: "python:3.12-slim"
  port: 8000
  replicas: 3
  env: { DB_URL: secret("db_url"), DEBUG: false }
  expose: public
  user: "10001:10001"
  resources: { cpu: "500m", memory: "512Mi" }
}

service worker {
  image: "python:3.12-slim"
  replicas: 2
  env: { DB_URL: secret("db_url") }
  user: "10001:10001"
  resources: { cpu: "250m", memory: "256Mi" }
}

database main {
  engine: postgres
  version: "16"
  size: "20GB"
  expose: private
}

api -> main
worker -> main
`,
  },
  {
    id: "insecure",
    label: "Fallos de seguridad",
    description: "Secretos en texto plano, imagen latest, base de datos pública…",
    source: `# Ejemplo con defectos: observa los hallazgos
service api {
  image: "python:latest"
  port: 22
  replicas: 1
  env: { DB_PASSWORD: "admin123", DEBUG: true }
  expose: public
}

database main {
  engine: postgres
  version: "16"
  expose: public
}

api -> ghost
`,
  },
  {
    id: "syntax",
    label: "Error de sintaxis",
    description: "Falta la llave de cierre.",
    source: `# Falta la llave de cierre del servicio
service api {
  image: "python:3.12-slim"
  port: 8000
`,
  },
  {
    id: "semantic",
    label: "Error semántico",
    description: "Nombre duplicado y enlace a un recurso que no existe.",
    source: `# Nombre duplicado y enlace inexistente
service api {
  image: "python:3.12-slim"
  port: 8000
  user: "10001:10001"
  resources: { cpu: "100m", memory: "128Mi" }
}

database api {
  engine: postgres
  version: "16"
}

api -> missing
`,
  },
];

export const DEFAULT_SAMPLE = SAMPLES[0];
