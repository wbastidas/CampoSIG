/**
 * The capture, laid out as the form the technician filled (I5, I6 «vista de formulario»).
 *
 * The review screen showed everything *about* a capture — the AI audit, the compliance findings,
 * the photographs — and never the capture itself. A supervisor could approve a work order without
 * once seeing the answers as the crew entered them, which is the one view the decision is actually
 * about.
 *
 * Read-only, deliberately. A supervisor corrects a capture by returning it with an observation on
 * the exact field (RF-112), not by editing what somebody else recorded: an approval is worth
 * something because it says a person checked what the crew wrote, and an edited answer nobody can
 * attribute is worth nothing. The editing renderer belongs to the office capture flow, and it will
 * reuse the layout and the rules below.
 *
 * Three things are marked on the field, because each is something a supervisor must not have to
 * infer: a value a model proposed, a required field left empty, and a field a conditional rule
 * demands given the other answers — that last one from `rules.ts`, the same evaluator the phone
 * and the server run against a shared corpus.
 */

import { Fragment } from 'react';

import { formSections, orphanFields, type FormFieldLayout } from './layout';
import { type FieldOrigin, originNote } from './origin';
import { missingRequirements } from './rules';
import { displayValue } from './values';

export interface FormViewProps {
  schema: Record<string, unknown>;
  uiSchema: Record<string, unknown>;
  answers: Record<string, unknown>;
  /** Conditional rules, so the view marks what the answers still owe. */
  rules?: unknown;
  provenance?: FieldOrigin[];
  /** Warnings the composer raised. A form assembled from an incomplete catalogue says so. */
  warnings?: string[];
}

export function FormView({
  schema,
  uiSchema,
  answers,
  rules,
  provenance = [],
  warnings = [],
}: FormViewProps) {
  const sections = formSections(schema, uiSchema);
  const orphans = orphanFields(schema, uiSchema);
  const owed = new Map(
    missingRequirements(rules, answers).map((missing) => [missing.field, missing.message]),
  );
  const origins = new Map(provenance.filter((entry) => entry.is_ai).map((e) => [e.field_key, e]));

  const renderField = (field: FormFieldLayout) => {
    const value = answers[field.key];
    const empty = displayValue(value) === '—';
    const demanded = owed.has(field.key);
    const origin = origins.get(field.key);
    return (
      <Fragment key={field.key}>
        <dt className={demanded ? 'form-view__owed' : undefined}>
          {field.label}
          {field.required && <abbr title="obligatorio"> *</abbr>}
        </dt>
        <dd>
          <span className={empty ? 'form-view__empty' : undefined}>{displayValue(value)}</span>
          {origin && <div className="form-view__origin">{originNote(origin)}</div>}
          {demanded && (
            <div role="status" className="form-view__owed-reason">
              {owed.get(field.key) ?? 'Este campo es obligatorio en este caso'}
            </div>
          )}
        </dd>
      </Fragment>
    );
  };

  return (
    <section className="form-view" aria-label="Formulario capturado">
      <h3>Formulario capturado</h3>

      {warnings.length > 0 && (
        <div role="status" className="form-view__warnings">
          <p>Avisos al armar este formulario:</p>
          <ul>
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {sections.length === 0 && <p>Este formulario no declara bloques que mostrar.</p>}

      {sections.map((section) => (
        <section key={`${section.code}-${section.title}`} aria-label={section.title}>
          <h4>
            {section.title} <span className="form-view__block">{section.code}</span>
          </h4>
          <dl className="form-view__fields">{section.fields.map(renderField)}</dl>
        </section>
      ))}

      {orphans.length > 0 && (
        <section aria-label="Campos sin bloque">
          {/* Un campo que existe, se respondió y no aparece en ningún bloque es la única forma en
              que esta vista puede perder datos en silencio. Se muestra como lo que es: algo que
              alguien debe reportar, no un hueco que nadie ve. */}
          <h4>Campos que el formulario no agrupa en ningún bloque</h4>
          <dl className="form-view__fields">{orphans.map(renderField)}</dl>
        </section>
      )}
    </section>
  );
}
