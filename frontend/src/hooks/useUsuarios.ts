import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarUsuario,
  crearUsuario,
  darDeAlta,
  darDeBaja,
  listarUsuarios,
  restablecerContrasena,
  type CambiosDeUsuario,
  type UsuarioNuevo,
} from "../api/usuarios";

const CLAVE = ["usuarios"];

export function useUsuarios() {
  return useQuery({ queryKey: CLAVE, queryFn: listarUsuarios });
}

/** Cada cambio vuelve a pedir la lista: lo que muestra es lo que quedó en el servidor. */
function useCambiaLaLista<A, R>(accion: (argumento: A) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: accion,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLAVE }),
  });
}

export function useCrearUsuario() {
  return useCambiaLaLista((datos: UsuarioNuevo) => crearUsuario(datos));
}

export function useActualizarUsuario() {
  return useCambiaLaLista(({ id, cambios }: { id: number; cambios: CambiosDeUsuario }) =>
    actualizarUsuario(id, cambios),
  );
}

export function useRestablecerContrasena() {
  return useCambiaLaLista((id: number) => restablecerContrasena(id));
}

export function useDarDeBaja() {
  return useCambiaLaLista((id: number) => darDeBaja(id));
}

export function useDarDeAlta() {
  return useCambiaLaLista((id: number) => darDeAlta(id));
}
