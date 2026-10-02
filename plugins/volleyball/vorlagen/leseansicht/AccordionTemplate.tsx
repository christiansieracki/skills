import { useEffect, useId, useState } from "react";
import { training, Masthead, Tools, ExerciseDetails, PrototypeNote, usePanels } from "./_shared";
import "./accordion.css";
import "./accordion-dark.css";
import "./accordion-template.css";

type ThemePreference = "light" | "dark" | "system";
const storageKey = "volleyball-reading-theme";
const choices: { value: ThemePreference; label: string }[] = [
  { value: "light", label: "Hell" },
  { value: "dark", label: "Dunkel" },
  { value: "system", label: "System" },
];

function readPreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(storageKey);
    if (value === "light" || value === "dark" || value === "system") return value;
  } catch { /* Storage may be unavailable in private or local-file browsing. */ }
  return "system";
}

// Shared light/dark design template. System is the default; no network required
// for theme detection. The sandbox's content/image dependencies are not an
// independently exportable offline HTML document.
export function AccordionTemplate() {
  const [preference, setPreference] = useState<ThemePreference>(readPreference);
  const [systemDark, setSystemDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const panels = usePanels();
  const id = useId();
  const dark = preference === "dark" || (preference === "system" && systemDark);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setSystemDark(media.matches);
    media.addEventListener("change", update);
    const sync = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) setPreference(readPreference());
    };
    window.addEventListener("storage", sync);
    return () => {
      media.removeEventListener("change", update);
      window.removeEventListener("storage", sync);
    };
  }, []);

  function choose(value: ThemePreference) {
    setPreference(value);
    try { window.localStorage.setItem(storageKey, value); }
    catch { /* The selection still works for this visit without storage. */ }
  }

  return <main className={`tv accordion accordion-template${dark ? " accordion-dark" : ""}`} lang="de">
    <div className="wrap">
      <Masthead />
      <fieldset className="theme-control" aria-describedby={`${id}-hint`}>
        <legend>Darstellung</legend>
        <div className="theme-options">
          {choices.map(choice => <label className="theme-option" key={choice.value}>
            <input type="radio" name={`${id}-theme`} value={choice.value} checked={preference === choice.value}
              onChange={() => choose(choice.value)} />
            <span>{choice.label}</span>
          </label>)}
        </div>
        <p className="theme-hint" id={`${id}-hint`}>
          {preference === "system" ? `Folgt deiner Geräteeinstellung · ${dark ? "dunkel" : "hell"}` : "Manuell gewählt · „System“ folgt deinem Gerät"}
        </p>
      </fieldset>
      <Tools openReference={panels.openReference} openPreparation={panels.openPreparation} />
      <div className="section-head"><h1>Ablauf</h1><span>12 Teile · Minuten ab Start</span></div>
      <div className="schedule">{training.schedule.map((item, index) => {
        const isOpen = expanded.has(index);
        return <section className={`schedule-item ${item.phase === "Pause" ? "pause" : ""}`} key={item.time}>
          <h2><button type="button" className="schedule-toggle" aria-expanded={isOpen}
            aria-controls={`${id}-exercise-${index}`} onClick={() => setExpanded(previous => {
              const next = new Set(previous);
              if (next.has(index)) next.delete(index); else next.add(index);
              return next;
            })}>
            <span className="time">{item.time}<small>{item.duration} min</small></span>
            <span><span className="phase">{item.phase}</span><strong>{item.name}</strong></span>
            <span className="mark" aria-hidden="true">{isOpen ? "−" : "+"}</span>
          </button></h2>
          <div id={`${id}-exercise-${index}`} hidden={!isOpen}>
            {isOpen && <ExerciseDetails item={item} openReference={panels.openReference} />}
          </div>
        </section>;
      })}</div>
      <PrototypeNote />
      {panels.panels}
    </div>
  </main>;
}