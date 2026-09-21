const COLOR: Record<string, string> = {
  encolada: "bg-line text-ink",
  corriendo: "bg-bronze text-paper",
  lista: "bg-cut text-paper",
  cancelada: "bg-line text-ink",
  error: "bg-conflict text-paper",
};

export default function EstadoBadge({ estado }: { estado: string }) {
  return <span className={`rounded px-2 py-0.5 text-xs font-mono ${COLOR[estado] ?? ""}`}>{estado}</span>;
}
