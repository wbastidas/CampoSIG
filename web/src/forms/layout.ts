/**
 * Laying a composed form out for reading (I5, I6).
 *
 * Driven by `ui:groups`, which is the form's own block structure — safety before execution,
 * evidence before closure, the order a technician works in. The backend's acta does the same walk
 * for paper (`app/reports/acta.py`), and the rule both implement is one sentence: **the layout is
 * the form's, not the renderer's.** A hand-kept list of fields stops mentioning the one a
 * functional administrator adds tomorrow, and the page still looks complete.
 *
 * Kept separate from the component so the part where a field could be dropped or mislabelled is
 * tested without a DOM.
 */

export interface FormFieldLayout {
  key: string;
  label: string;
  required: boolean;
  /** `x-signature`, `x-ai-generated` and friends, for the renderer to decide presentation. */
  annotations: Record<string, unknown>;
}

export interface FormSectionLayout {
  code: string;
  title: string;
  fields: FormFieldLayout[];
}

type Schema = Record<string, unknown>;

function asObject(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/**
 * A string field of an untyped object, or a fallback.
 *
 * Rather than `String(value)`: the same lint rule that caught `[object Object]` on the review
 * screen catches it here, and it is right to — a block title that came back as an object would be
 * printed as a Python-ish repr above a supervisor's data.
 */
function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

/** Every `x-…` key of a field schema, which is where the platform's own semantics live. */
export function annotationsOf(fieldSchema: unknown): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(asObject(fieldSchema)).filter(([key]) => key.startsWith('x-')),
  );
}

/** The label a person should read: the form's own title, never the field key dressed up. */
export function fieldLabel(fieldSchema: unknown, key: string): string {
  const title = asString(asObject(fieldSchema).title);
  return title.trim() ? title : key;
}

/**
 * The form's sections, in the form's order.
 *
 * A group whose fields are all absent from the schema is dropped: it means the block was composed
 * away for this work type, and an empty heading reads like missing data rather than like a block
 * that does not apply.
 */
export function formSections(schema: Schema, uiSchema: Schema): FormSectionLayout[] {
  const properties = asObject(schema.properties);
  const required = new Set(
    Array.isArray(schema.required) ? schema.required.map((key) => String(key)) : [],
  );
  const groups = Array.isArray(uiSchema['ui:groups']) ? uiSchema['ui:groups'] : [];

  const sections: FormSectionLayout[] = [];
  for (const raw of groups) {
    const group = asObject(raw);
    const keys = Array.isArray(group.fields) ? group.fields.map((key) => String(key)) : [];
    const fields = keys
      .filter((key) => key in properties)
      .map((key) => ({
        key,
        label: fieldLabel(properties[key], key),
        required: required.has(key),
        annotations: annotationsOf(properties[key]),
      }));
    if (fields.length === 0) continue;
    sections.push({
      code: asString(group.block),
      title: asString(group.title),
      fields,
    });
  }
  return sections;
}

/**
 * Fields the schema declares and no group claims.
 *
 * Shown by the renderer under a heading of their own rather than dropped. A field that exists, was
 * answered, and appears nowhere is the one way this layout can lose data silently — so it is
 * surfaced as a defect the person can report instead of a blank the person never sees.
 */
export function orphanFields(schema: Schema, uiSchema: Schema): FormFieldLayout[] {
  const properties = asObject(schema.properties);
  const claimed = new Set(formSections(schema, uiSchema).flatMap((s) => s.fields.map((f) => f.key)));
  const required = new Set(
    Array.isArray(schema.required) ? schema.required.map((key) => String(key)) : [],
  );
  return Object.keys(properties)
    .filter((key) => !claimed.has(key))
    .map((key) => ({
      key,
      label: fieldLabel(properties[key], key),
      required: required.has(key),
      annotations: annotationsOf(properties[key]),
    }));
}
