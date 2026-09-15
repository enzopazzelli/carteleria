interface BannerProps {
  variante: "error" | "aviso";
  children: React.ReactNode;
}

export default function Banner({ variante, children }: BannerProps) {
  const color = variante === "error" ? "border-conflict text-conflict" : "border-bronze text-bronze";
  return <div className={`border rounded px-3 py-2 text-sm bg-paper ${color}`}>{children}</div>;
}
