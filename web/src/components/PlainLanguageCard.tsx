import { ReactNode } from "react";

interface PlainLanguageCardProps {
  title: string;
  summary: string;
  children?: ReactNode;
}

export function PlainLanguageCard({ title, summary, children }: PlainLanguageCardProps) {
  return (
    <article className="panel-card plain-card">
      <h3>{title}</h3>
      <p className="plain-summary">{summary}</p>
      {children}
    </article>
  );
}
