import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import data from "./training-data.json";
import "./training.css";

export const training = {
  ...data,
  schedule: data.schedule.map(item => ({
    ...item,
    image: item.image ? new URL("./training-2026-10-01-dankeball.png", import.meta.url).href : "",
  })),
};
export type ScheduleItem = (typeof data.schedule)[number];
export type ReferenceKey = keyof typeof data.references;
const labels: Record<ReferenceKey, string> = {
  teams: "Die drei Sechser",
  rotations: "5-1 · alle sechs Läufer",
  rules: "Kommunikationsregeln",
};

export function Rich({ html }: { html: string }) {
  // Only trusted, locally extracted training-source markup; no user input.
  return <div className="rich" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function Masthead() {
  return <header className="mast">
    <div><p className="date">Do, 01.10.2026</p><p className="meta">Herren 1 + 2 · 18 Teilnehmer</p></div>
    <p className="duration">120 min<small>geplant · 1 Hallenteil</small></p>
  </header>;
}

export function Modal({ open, onClose, title, children, className = "", closeLabel = "Zurück" }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; className?: string; closeLabel?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const headingId = useId();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) {
      node.showModal();
      node.scrollTop = 0;
    } else if (!open && node.open) {
      node.close();
    }
    return () => { if (node.open) node.close(); };
  }, [open]);
  return <dialog ref={dialog} className={className} aria-labelledby={headingId}
    onCancel={(event) => { event.preventDefault(); onCloseRef.current(); }}
    onClick={(event) => {
      if (event.target !== event.currentTarget) return;
      const bounds = event.currentTarget.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onCloseRef.current();
    }}>
    <div className="dialog-head"><h2 id={headingId}>{title}</h2><button type="button" onClick={onClose}>{closeLabel}</button></div>
    <div className="dialog-content">{open ? children : null}</div>
  </dialog>;
}

export function usePanels() {
  const [reference, setReference] = useState<ReferenceKey | null>(null);
  const [preparation, setPreparation] = useState(false);
  const panels = <>
    <Modal open={reference !== null} onClose={() => setReference(null)} title="Nachschlagen" closeLabel="Zurück zur Übung">
      <nav className="reference-tabs" aria-label="Gemeinsame Referenzen">
        {(Object.keys(labels) as ReferenceKey[]).map(key => <button key={key} type="button" aria-pressed={reference === key} onClick={() => setReference(key)}>
          {key === "teams" ? "Sechser" : key === "rotations" ? "Rotationen" : "Regeln"}
        </button>)}
      </nav>
      {reference && <><h2>{labels[reference]}</h2><Rich html={data.references[reference]} /></>}
    </Modal>
    <Modal open={preparation} onClose={() => setPreparation(false)} title="Vorbereitung & Hintergrund" closeLabel="Zurück zum Ablauf">
      <div className="preparation">{data.preparation.map(section => <details key={section.title}>
        <summary>{section.title}</summary><Rich html={section.html} />
      </details>)}</div>
    </Modal>
  </>;
  return { openReference: (key: ReferenceKey) => setReference(key), openPreparation: () => setPreparation(true), panels };
}

export function Tools({ openReference, openPreparation }: { openReference: (key: ReferenceKey) => void; openPreparation: () => void }) {
  return <nav className="tools" aria-label="Trainingsunterlagen">
    <button type="button" onClick={() => openReference("teams")}>Sechser & Regeln</button>
    <button type="button" onClick={openPreparation}>Vorbereitung</button>
  </nav>;
}

export function ExerciseDetails({ item, openReference }: { item: ScheduleItem; openReference: (key: ReferenceKey) => void }) {
  const [zoom, setZoom] = useState<"image" | "sketch" | null>(null);
  const [enlarged, setEnlarged] = useState(false);
  const today = item.today.replace(/\.? Ablauf siehe unten\.?/, "").replace(/Ablauf siehe unten/, "").replace(/, siehe unten/, "").replace(/wie immer, siehe Tabelle unten/, "wie immer");
  return <div className="details-body">
    {today && <div className="today"><b>Heute</b><Rich html={today} /></div>}
    {item.practical && <><h3>Aufbau & Ablauf</h3><Rich html={item.practical} /></>}
    {item.athletics.length > 0 && <section aria-label="Athletikübungen">
      <h3>DVV Plan 1 · Ausführung</h3>
      {item.athleticNote && <div className="rich"><p>{item.athleticNote}</p></div>}
      {item.athletics.map(exercise => <details key={exercise.number} className="exercise">
        <summary><span><span>{exercise.number}. {exercise.name}</span><small>{exercise.dose}</small></span></summary>
        <p>{exercise.description}</p>
      </details>)}
      <p className="meta" style={{ marginTop: 12 }}>Vorbereitender Athletikplan DVV, Plan 1. Kurzbeschreibungen aus dem Trainingsplan.</p>
    </section>}
    {item.sketch && <section><h3>Hallenskizze · heute</h3>
      <div className="rich"><pre>{item.sketch}</pre></div>
      <button type="button" onClick={() => { setEnlarged(false); setZoom("sketch"); }}>Skizze vergrößern</button>
    </section>}
    {item.image && <section><h3>Schaubild · Grundform</h3>
      <button type="button" className="diagram" onClick={() => { setEnlarged(false); setZoom("image"); }} aria-label="Schaubild der Dankeballannahme vergrößern">
        <img src={item.image} alt="Schaubild: Dankeballannahme im oberen Zuspiel" loading="lazy" />
        <span>Schaubild vergrößern ↗</span>
      </button>
      <p className="meta">PlayDrill · ue-0015. Grundform ohne Angriff; die Aufteilung von heute steht in der Hallenskizze.</p>
    </section>}
    {item.references.length > 0 && <nav className="reference-links" aria-label="Für diese Übung nachschlagen">
      {item.references.map(key => <button type="button" key={key} onClick={() => openReference(key as ReferenceKey)}>
        {key === "teams" ? "Sechser ↗" : key === "rotations" ? "5-1 / Läufer ↗" : "Kommunikationsregeln ↗"}
      </button>)}
    </nav>}
    {item.why && <details className="why"><summary>Warum hier?</summary><Rich html={item.why} /></details>}
    <Modal open={zoom !== null} onClose={() => setZoom(null)} title={zoom === "image" ? "Dankeballannahme · Grundform" : "Hallenskizze · heute"} closeLabel="Zurück" className="zoom">
      {zoom === "image" ? <>
        <p className="zoom-help">Originaldiagramm · Grundform ohne Angriff</p>
        <button type="button" aria-pressed={enlarged} onClick={() => setEnlarged(value => !value)}>{enlarged ? "Gesamtansicht" : "2× vergrößern"}</button>
        <div style={{ overflow: "auto", marginTop: 16 }}><img src={item.image} alt="Schaubild: Dankeballannahme im oberen Zuspiel" style={{ width: enlarged ? "200%" : "100%" }} /></div>
      </> : <pre>{item.sketch}</pre>}
    </Modal>
  </div>;
}

export function PrototypeNote() {
  return <p className="note">Layout-Prototyp · Trainingsplan 01.10.2026. Keine laufende Zeitmessung.</p>;
}