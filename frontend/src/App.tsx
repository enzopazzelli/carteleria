export default function App() {
  return (
    <div className="min-h-screen bg-paper text-ink p-8">
      <h1 className="text-2xl font-semibold">Cartelería — cotizador</h1>
      <p className="mt-2 text-sm">
        Herramienta interna.{" "}
        <span className="rounded px-2 py-1 bg-cut text-paper">corte</span>{" "}
        <span className="rounded px-2 py-1 bg-bronze text-paper">dinero</span>{" "}
        <span className="rounded px-2 py-1 bg-conflict text-paper">conflicto</span>
      </p>
      <p className="mt-2 font-mono text-sm">123.45 mm · $ 45.678,90</p>
    </div>
  );
}
