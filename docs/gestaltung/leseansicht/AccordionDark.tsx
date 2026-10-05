import { useState } from "react";
import { training, Masthead, Tools, ExerciseDetails, PrototypeNote, usePanels } from "./_shared";
import "./accordion.css";
import "./accordion-dark.css";

export function AccordionDark() {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const panels = usePanels();
  return <main className="tv accordion accordion-dark" lang="de"><div className="wrap">
    <Masthead />
    <Tools openReference={panels.openReference} openPreparation={panels.openPreparation} />
    <div className="section-head"><h1>Ablauf</h1><span>12 Teile · Minuten ab Start</span></div>
    <div className="schedule">{training.schedule.map((item, index) => {
      const isOpen = expanded.has(index);
      return <section className={`schedule-item ${item.phase === "Pause" ? "pause" : ""}`} key={item.time}>
        <h2><button type="button" className="schedule-toggle" aria-expanded={isOpen} aria-controls={`accordion-exercise-${index}`} onClick={() => setExpanded(previous => {
          const next = new Set(previous);
          if (next.has(index)) next.delete(index); else next.add(index);
          return next;
        })}>
          <span className="time">{item.time}<small>{item.duration} min</small></span>
          <span><span className="phase">{item.phase}</span><strong>{item.name}</strong></span>
          <span className="mark" aria-hidden="true">{isOpen ? "−" : "+"}</span>
        </button></h2>
        <div id={`accordion-exercise-${index}`} hidden={!isOpen}>
          {isOpen && <ExerciseDetails item={item} openReference={panels.openReference} />}
        </div>
      </section>;
    })}</div>
    <PrototypeNote />
    {panels.panels}
  </div></main>;
}