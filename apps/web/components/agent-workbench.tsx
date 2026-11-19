"use client";

import { useId, useRef, useState } from "react";

const roles = [
  { name: "Scout", title: "Find the signal.", verb: "Investigate", description: "Start with the purchase identifiers. Find a supported recall and bring its official source into the case.", detail: "Purchase record + official evidence", mark: "search" },
  { name: "Skeptic", title: "Question the match.", verb: "Challenge", description: "Test the candidate against exclusions. A challenge explains why a similar model might not be affected, or which fact is still unknown.", detail: "Candidate + exclusions + missing facts", mark: "challenge" },
  { name: "Builder", title: "Make it actionable.", verb: "Explain", description: "Turn the finding and challenge into a clear case board. Ask for the next missing fact, or explain the next step for local review.", detail: "Finding + challenge = next step", mark: "build" },
] as const;

const sponsorRoles = [
  { tool: "Agent37", use: "runs Scout’s official recall lookup." },
  { tool: "Lyzr", use: "reviews the evidence and tests the proposed match." },
  { tool: "Lyzr", use: "builds the case summary from the finding and challenge." },
] as const;

export function AgentWorkbench() {
  const [selected, setSelected] = useState(0);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const id = useId();
  const role = roles[selected];
  const sponsor = sponsorRoles[selected];
  return (
    <section className="agent-workbench" aria-label="How the agent team works">
      <div className="workbench-top"><span>One case. Three perspectives.</span><span className="preview-label">How it works</span></div>
      <div className="agent-tabs" role="tablist" aria-label="Agent roles">
        <span className="agent-selection-marker" data-testid="agent-selection-marker" aria-hidden="true"
          style={{ transform: `translateX(calc(${selected} * (100% + 5px)))` }} />
        {roles.map((item, index) => <button
          key={item.name} ref={el => { buttons.current[index] = el; }}
          id={`${id}-tab-${index}`} role="tab" aria-selected={selected === index}
          aria-controls={`${id}-panel`} tabIndex={selected === index ? 0 : -1}
          onClick={() => setSelected(index)}
          onKeyDown={event => {
            let next = selected;
            if (event.key === "ArrowRight") next = (selected + 1) % roles.length;
            else if (event.key === "ArrowLeft") next = (selected + roles.length - 1) % roles.length;
            else if (event.key === "Home") next = 0;
            else if (event.key === "End") next = roles.length - 1;
            else return;
            event.preventDefault(); setSelected(next); buttons.current[next]?.focus();
          }}
        ><span className="agent-tab-dot" aria-hidden="true" />{item.name}</button>)}
      </div>
      <div key={role.name} id={`${id}-panel`} role="tabpanel" tabIndex={0} aria-labelledby={`${id}-tab-${selected}`} className="agent-stage">
        <div className="agent-stage-visual" aria-hidden="true">
          <svg className={`agent-glyph ${role.mark}`} viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2">
            {role.mark === "search" ? <><circle cx="28" cy="28" r="17" /><path d="m40 40 15 15M20 28h16M28 20v16" /></> : role.mark === "challenge" ? <><path d="M12 15h40v34H12zM22 26l20 13M42 26 22 39" /><path d="M20 8v7M44 8v7M20 49v7M44 49v7" /></> : <><path d="M15 8h25l9 9v39H15zM40 8v12h9M23 31l6 6 12-13M23 46h18" /></>}
          </svg>
          <span className="stage-verb">{role.verb}</span>
          <span className="stage-index">{String(selected + 1).padStart(2, "0")} / 03</span>
        </div>
        <div className="agent-stage-copy"><h2>{role.title}</h2><p>{role.description}</p></div>
        <div className="workbench-equation"><span className="signal-mark" aria-hidden="true" />{role.detail}</div>
        <p className="workbench-sponsor"><strong>{sponsor.tool}</strong> {sponsor.use}</p>
      </div>
      <div className="workbench-foot">
        <div><strong>BAND</strong> hands off tasks and results between agents.</div>
        <details>
          <summary>Proposed sponsor roles</summary>
          <div><strong>Finch</strong> could deliver a reusable review skill for Skeptic.</div>
          <div><strong>AdaL</strong> could run an independent review and produce the presentation video.</div>
        </details>
      </div>
    </section>
  );
}
