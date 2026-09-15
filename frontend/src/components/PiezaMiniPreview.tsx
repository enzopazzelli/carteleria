interface PiezaMiniPreviewProps {
  contornoMm: string[][];
  anchoMm: string;
  altoMm: string;
}

const TAMANO_PX = 48;

export default function PiezaMiniPreview({ contornoMm, anchoMm, altoMm }: PiezaMiniPreviewProps) {
  const ancho = Number(anchoMm);
  const alto = Number(altoMm);
  const puntos = contornoMm.map(([x, y]) => `${x},${y}`).join(" ");

  return (
    <svg
      width={TAMANO_PX}
      height={TAMANO_PX}
      viewBox={`0 0 ${ancho || 1} ${alto || 1}`}
      className="border border-line rounded bg-paper"
    >
      <polygon points={puntos} fill="none" stroke="#2E8074" strokeWidth={Math.max(ancho, alto) / 40} />
    </svg>
  );
}
