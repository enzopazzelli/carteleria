const BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function manejarRespuesta<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    const mensaje =
      cuerpo && typeof cuerpo.detail === "string" ? cuerpo.detail : `Error ${respuesta.status}`;
    throw new ApiError(respuesta.status, mensaje);
  }
  if (respuesta.status === 204) {
    return undefined as T;
  }
  return respuesta.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`);
  return manejarRespuesta<T>(respuesta);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiDelete(path: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  return manejarRespuesta<void>(respuesta);
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, { method: "POST", body: formData });
  return manejarRespuesta<T>(respuesta);
}
