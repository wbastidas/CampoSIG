/**
 * The importer screen's decision logic, as pure functions (RF-301).
 *
 * Separated from the component for the usual reason: the part where a mistake binds a canonical
 * attribute to the wrong real field is tested without a browser. Two of the functions below
 * exist entirely because of a way this goes wrong on screen.
 */

import type {
  AssetDecision,
  AssetProposal,
  AttributeProposal,
  FieldCandidate,
  LayerCandidate,
  ProfileDecisions,
} from '../../api/modelProfile';

/** The server's margin, mirrored so the screen marks the same pairs the server does. */
export const AMBIGUITY_MARGIN = 0.1;

export type Confidence = 'alta' | 'media' | 'baja';

/**
 * How much the evidence is worth, in words.
 *
 * Words rather than a percentage: a "0.62" invites an administrator to treat a guess as a
 * measurement. The bands are coarse on purpose.
 */
export function confidence(score: number): Confidence {
  if (score >= 0.75) return 'alta';
  if (score >= 0.5) return 'media';
  return 'baja';
}

/** Whether the two best candidates are too close to call. */
export function ambiguous(candidates: { score: number }[]): boolean {
  if (candidates.length < 2) return false;
  const [first, second] = candidates;
  if (!first || !second) return false;
  return first.score - second.score < AMBIGUITY_MARGIN;
}

/** Evidence with the heaviest signal first, so the reason that decided it reads first. */
export function rankedEvidence<T extends { weight: number }>(evidence: T[]): T[] {
  return [...evidence].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight));
}

/** The class chosen for an asset type, or null while nobody has chosen. */
export function chosenLayer(decisions: ProfileDecisions, assetTypeKey: string): string | null {
  return decisions.assets[assetTypeKey]?.layer ?? null;
}

/** The field chosen for a canonical attribute, or null when deliberately unmapped. */
export function chosenField(
  decisions: ProfileDecisions,
  assetTypeKey: string,
  attributeKey: string,
): string | null {
  return decisions.assets[assetTypeKey]?.attributes[attributeKey] ?? null;
}

/** The candidates the proposal offers for one attribute, best first. */
export function candidatesFor(
  asset: AssetProposal,
  attributeKey: string,
): FieldCandidate[] {
  return asset.attributes.find((a) => a.attribute_key === attributeKey)?.candidates ?? [];
}

/**
 * Accept a class for an asset type, and **drop every field chosen for the previous one.**
 *
 * The defect this prevents: the fields on screen belonged to the class that was just rejected.
 * A field name that happens to exist in both classes — `CODIGO` exists in most of them — would
 * survive the change and look decided, pointing at a column of a class nobody picked. So the
 * change is a reset, seeded with what the new proposal settles on its own.
 */
export function chooseLayer(
  decisions: ProfileDecisions,
  assetTypeKey: string,
  asset: AssetProposal,
  layer: string,
): ProfileDecisions {
  const attributes: Record<string, string> = {};
  for (const attribute of asset.attributes) {
    const best = attribute.candidates[0];
    if (best && !ambiguous(attribute.candidates)) attributes[attribute.attribute_key] = best.field;
  }
  return {
    ...decisions,
    assets: {
      ...decisions.assets,
      [assetTypeKey]: {
        layer,
        attributes,
        related: asset.related,
        participates_in_geometric_network:
          decisions.assets[assetTypeKey]?.participates_in_geometric_network ?? false,
      },
    },
  };
}

/** Bind a canonical attribute to a field, or to nothing when `field` is null. */
export function chooseField(
  decisions: ProfileDecisions,
  assetTypeKey: string,
  attributeKey: string,
  field: string | null,
): ProfileDecisions {
  const asset = decisions.assets[assetTypeKey];
  if (!asset) return decisions;
  const attributes = { ...asset.attributes };
  if (field === null) delete attributes[attributeKey];
  else attributes[attributeKey] = field;
  return {
    ...decisions,
    assets: { ...decisions.assets, [assetTypeKey]: { ...asset, attributes } },
  };
}

/** Forget an asset type entirely: this installation does not record it. */
export function clearAsset(
  decisions: ProfileDecisions,
  assetTypeKey: string,
): ProfileDecisions {
  const assets = { ...decisions.assets };
  delete assets[assetTypeKey];
  return { ...decisions, assets };
}

export interface AssetStatus {
  assetTypeKey: string;
  layer: string | null;
  /** Required canonical attributes with nothing bound. These block publication. */
  missingRequired: string[];
  /** Optional ones with nothing bound. Legitimate, and worth seeing. */
  unmapped: string[];
  ambiguous: string[];
  ready: boolean;
}

export function statusOf(asset: AssetProposal, decision: AssetDecision | undefined): AssetStatus {
  const bound = decision?.attributes ?? {};
  const missingRequired: string[] = [];
  const unmapped: string[] = [];
  const uncertain: string[] = [];

  for (const attribute of asset.attributes) {
    if (!bound[attribute.attribute_key]) {
      (attribute.required ? missingRequired : unmapped).push(attribute.attribute_key);
    }
    if (ambiguous(attribute.candidates) && !bound[attribute.attribute_key]) {
      uncertain.push(attribute.attribute_key);
    }
  }

  return {
    assetTypeKey: asset.asset_type_key,
    layer: decision?.layer ?? null,
    missingRequired,
    unmapped,
    ambiguous: uncertain,
    ready: Boolean(decision?.layer) && missingRequired.length === 0,
  };
}

export interface Progress {
  total: number;
  decided: number;
  blocked: number;
}

/** What the header shows: how far along this is, and whether anything blocks publishing. */
export function progressOf(
  assets: AssetProposal[],
  decisions: ProfileDecisions,
): Progress {
  const statuses = assets.map((asset) => statusOf(asset, decisions.assets[asset.asset_type_key]));
  return {
    total: statuses.length,
    decided: statuses.filter((s) => s.ready).length,
    // An asset type nobody mapped at all is not a blocker: an installation without street
    // lights is a real installation. What blocks is a class chosen with a required attribute
    // left dangling, which is the half-finished state.
    blocked: statuses.filter((s) => s.layer !== null && s.missingRequired.length > 0).length,
  };
}

/** The best candidate's class name, for the "accept the proposal" button's label. */
export function leadingLayer(candidates: LayerCandidate[]): string | null {
  return candidates[0]?.layer ?? null;
}

/** Canonical enum values the chosen domain offers no code for, across one asset type. */
export function valueMapGaps(
  asset: AssetProposal,
  decision: AssetDecision | undefined,
): { attributeKey: string; domain: string; unmapped: string[] }[] {
  const gaps: { attributeKey: string; domain: string; unmapped: string[] }[] = [];
  for (const attribute of asset.attributes) {
    const field = decision?.attributes[attribute.attribute_key];
    if (!field) continue;
    const candidate = attribute.candidates.find((c) => c.field === field);
    const map = candidate?.value_map;
    if (map && map.unmapped.length > 0) {
      gaps.push({ attributeKey: attribute.attribute_key, domain: map.domain, unmapped: map.unmapped });
    }
  }
  return gaps;
}

/** Whether an attribute was refused a field it matched by name, and why. */
export function refusals(asset: AssetProposal): { attributeKey: string; reasons: string[] }[] {
  return asset.attributes
    .filter((attribute: AttributeProposal) => attribute.refused.length > 0)
    .map((attribute) => ({
      attributeKey: attribute.attribute_key,
      reasons: attribute.refused,
    }));
}
