/**
 * The profile importer screen (`/admin/model-profile`, RF-301, RF-302).
 *
 * The acceptance criterion of I2, as a screen: a functional administrator starts from the
 * metadata another business unit's agent exported, and produces a working profile without
 * writing code. Until now the only way in was writing a YAML file by hand, guessing which of
 * two hundred feature classes the canonical `support_structure` means.
 *
 * What the design turns on: **a proposal is shown with its reasons, never as a verdict.** Each
 * candidate carries the evidence that scored it — the term that matched the class name, how many
 * canonical attributes found a column, whether the geometry is the one the type asks for — and
 * the confidence is a word, not a percentage, because a "0.62" invites somebody to treat a guess
 * as a measurement. An ambiguous pair is marked and left undecided: pre-selecting a coin flip
 * and calling it a default is how a wrong binding gets accepted by somebody clicking through.
 *
 * Every judgement lives in `decisions.ts` and is tested there. This file renders and calls.
 */

import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '../../api/planning';
import {
  type AssetProposal,
  createDraft,
  type Draft,
  fetchAssetProposal,
  fetchCurrentDraft,
  fetchHistory,
  fetchProposal,
  type HistoryEntry,
  type ProfileDecisions,
  type ProfileProposal,
  publishDraft,
  saveDecisions,
  yamlUrl,
} from '../../api/modelProfile';
import {
  ambiguous,
  candidatesFor,
  chooseField,
  chooseLayer,
  chosenField,
  chosenLayer,
  clearAsset,
  confidence,
  progressOf,
  rankedEvidence,
  refusals,
  statusOf,
  valueMapGaps,
} from './decisions';

export interface ModelProfileScreenProps {
  /** Required: a profile belongs to one business unit's geodatabase (ADR-009). */
  businessUnit: string;
  /** Prefilled profile id for a new draft. The unit's own id by default. */
  suggestedProfileId?: string;
}

export function ModelProfileScreen({
  businessUnit,
  suggestedProfileId,
}: ModelProfileScreenProps) {
  const [proposal, setProposal] = useState<ProfileProposal | null>(null);
  const [layerNames, setLayerNames] = useState<string[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [decisions, setDecisions] = useState<ProfileDecisions | null>(null);
  const [profileId, setProfileId] = useState(suggestedProfileId ?? '');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const answer = await fetchProposal(businessUnit, signal);
        setProposal(answer.proposal);
        setLayerNames(answer.layer_names);
        setGaps(answer.gaps);
        if (!suggestedProfileId) setProfileId((current) => current || answer.profile_id);
        setError(null);
        try {
          const open = await fetchCurrentDraft(businessUnit, answer.profile_id, signal);
          setDraft(open);
          setDecisions(open.decisions);
        } catch (cause) {
          // 404 is the ordinary case: no draft open yet. Anything else is worth saying.
          if (!(cause instanceof ApiError) || cause.status !== 404) throw cause;
          setDraft(null);
          setDecisions(null);
        }
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    },
    [businessUnit, suggestedProfileId],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto. La
    // regla no lo ve a través de la indirección, igual que en la pantalla de integraciones.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    if (!draft) return;
    const controller = new AbortController();
    fetchHistory(businessUnit, draft.profile_id, controller.signal)
      .then(setHistory)
      .catch(() => {
        // The history is context, not the task. Losing it must not take the screen with it.
      });
    return () => controller.abort();
  }, [businessUnit, draft]);

  const onStart = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await createDraft(businessUnit, { profile_id: profileId });
      setDraft(created);
      setDecisions(created.decisions);
      setNotice(`Borrador abierto: versión ${created.version}.`);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit, profileId]);

  const onSave = useCallback(async () => {
    if (!draft || !decisions) return;
    setBusy(true);
    setError(null);
    try {
      const saved = await saveDecisions(businessUnit, draft.draft_id, decisions);
      setDraft(saved);
      setDecisions(saved.decisions);
      setNotice(
        saved.ready
          ? 'Guardado. El perfil está completo y se puede publicar.'
          : `Guardado. Faltan ${saved.problems.length} cosas por resolver.`,
      );
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit, decisions, draft]);

  const onPublish = useCallback(async () => {
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      const published = await publishDraft(businessUnit, draft.draft_id);
      setDraft(published);
      setDecisions(published.decisions);
      setNotice(
        `Perfil publicado como versión ${published.version}. La unidad lo adopta desde ahora.`,
      );
    } catch (cause) {
      // The server re-validates on publish, so its refusal is the authoritative list of what
      // is missing — shown as it came, not summarised into "no se pudo publicar".
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit, draft]);

  /** Accept a class for an asset type, re-scoring its attributes against that class. */
  const onChooseLayer = useCallback(
    async (assetTypeKey: string, layer: string) => {
      if (!decisions) return;
      setBusy(true);
      try {
        const rescored = await fetchAssetProposal(businessUnit, assetTypeKey, layer);
        setProposal((current) =>
          current
            ? {
                ...current,
                assets: current.assets.map((asset) =>
                  asset.asset_type_key === assetTypeKey
                    ? { ...rescored, candidates: asset.candidates }
                    : asset,
                ),
              }
            : current,
        );
        setDecisions(chooseLayer(decisions, assetTypeKey, rescored, layer));
        setError(null);
      } catch (cause) {
        setError((cause as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [businessUnit, decisions],
  );

  if (error && !proposal) {
    return (
      <section className="importer">
        <h2>Perfil de modelo de datos</h2>
        <p role="alert">{error}</p>
      </section>
    );
  }

  if (!proposal) return <p>Analizando los metadatos sincronizados…</p>;

  const progress = decisions ? progressOf(proposal.assets, decisions) : null;

  return (
    <section className="importer">
      <header className="importer__header">
        <h2>Perfil de modelo de datos</h2>
        <p className="importer__hint">
          La propuesta sale de los metadatos que el agente exportó de esta unidad. Cada
          candidata trae la evidencia que la puntuó; nada se aplica hasta que usted lo acepta y
          publica.
        </p>

        {proposal.unclaimed_layer_count > 0 && (
          <p role="status">
            {proposal.unclaimed_layer_count} clases del snapshot no corresponden a ningún tipo
            canónico. Es lo normal: la geodatabase tiene cientos y el vocabulario cubre{' '}
            {proposal.assets.length}.
          </p>
        )}

        {!draft && (
          <div className="importer__start">
            <label htmlFor="profile-id">Identificador del perfil</label>
            <input
              id="profile-id"
              value={profileId}
              onChange={(event) => setProfileId(event.target.value)}
            />
            <button type="button" onClick={() => void onStart()} disabled={busy || !profileId}>
              Abrir borrador
            </button>
          </div>
        )}

        {draft && progress && (
          <dl className="importer__progress">
            <dt>Versión</dt>
            <dd>
              {draft.version} · {draft.status}
            </dd>
            <dt>Tipos resueltos</dt>
            <dd>
              {progress.decided} de {progress.total}
            </dd>
            <dt>A medio mapear</dt>
            <dd>{progress.blocked}</dd>
          </dl>
        )}

        {notice && (
          <p role="status" className="importer__notice">
            {notice}
          </p>
        )}
        {error && <p role="alert">{error}</p>}
      </header>

      {gaps.length > 0 && !draft && (
        <section aria-label="Huecos de la propuesta">
          <h3>Lo que la propuesta no resuelve sola</h3>
          <ul>
            {gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </section>
      )}

      {draft && draft.problems.length > 0 && (
        <section aria-label="Impedimentos para publicar">
          <h3>Falta esto para poder publicar</h3>
          <ul>
            {draft.problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </section>
      )}

      <ul className="importer__assets">
        {proposal.assets.map((asset) => (
          <AssetCard
            key={asset.asset_type_key}
            asset={asset}
            decisions={decisions}
            layerNames={layerNames}
            expanded={expanded === asset.asset_type_key}
            busy={busy}
            onToggle={() =>
              setExpanded((current) =>
                current === asset.asset_type_key ? null : asset.asset_type_key,
              )
            }
            onChooseLayer={(layer) => void onChooseLayer(asset.asset_type_key, layer)}
            onChooseField={(attributeKey, field) =>
              decisions &&
              setDecisions(chooseField(decisions, asset.asset_type_key, attributeKey, field))
            }
            onForget={() => decisions && setDecisions(clearAsset(decisions, asset.asset_type_key))}
          />
        ))}
      </ul>

      {draft && (
        <footer className="importer__actions">
          <button type="button" onClick={() => void onSave()} disabled={busy}>
            Guardar decisiones
          </button>
          <button
            type="button"
            onClick={() => void onPublish()}
            disabled={busy || !draft.ready || draft.status !== 'draft'}
          >
            Publicar perfil
          </button>
          {draft.document && (
            <a href={yamlUrl(businessUnit, draft.draft_id)} download>
              Descargar el YAML para versionar
            </a>
          )}
        </footer>
      )}

      {history.length > 0 && (
        <section aria-label="Versiones del perfil">
          <h3>Versiones</h3>
          <table>
            <thead>
              <tr>
                <th scope="col">Versión</th>
                <th scope="col">Estado</th>
                <th scope="col">Publicó</th>
                <th scope="col">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.draft_id}>
                  <td>{entry.version}</td>
                  <td>{entry.status}</td>
                  <td>{entry.published_by ?? '—'}</td>
                  <td>{entry.published_at ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </section>
  );
}

interface AssetCardProps {
  asset: AssetProposal;
  decisions: ProfileDecisions | null;
  layerNames: string[];
  expanded: boolean;
  busy: boolean;
  onToggle: () => void;
  onChooseLayer: (layer: string) => void;
  onChooseField: (attributeKey: string, field: string | null) => void;
  onForget: () => void;
}

function AssetCard({
  asset,
  decisions,
  layerNames,
  expanded,
  busy,
  onToggle,
  onChooseLayer,
  onChooseField,
  onForget,
}: AssetCardProps) {
  const chosen = decisions ? chosenLayer(decisions, asset.asset_type_key) : null;
  const status = statusOf(asset, decisions?.assets[asset.asset_type_key]);
  const uncertain = ambiguous(asset.candidates);
  const gaps = decisions ? valueMapGaps(asset, decisions.assets[asset.asset_type_key]) : [];

  return (
    <li className="importer__asset">
      <header>
        <button type="button" aria-expanded={expanded} onClick={onToggle}>
          {asset.asset_type_key}
        </button>
        <span className="importer__geometry">{asset.geometry}</span>
        {chosen ? (
          <strong>{chosen}</strong>
        ) : (
          <em>sin clase elegida</em>
        )}
        {status.missingRequired.length > 0 && (
          <span role="status">
            falta lo obligatorio: {status.missingRequired.join(', ')}
          </span>
        )}
      </header>

      {uncertain && (
        <p role="status">
          Dos clases puntúan casi igual ({asset.candidates.slice(0, 2).map((c) => c.layer).join(' y ')}).
          Elija una: no se preselecciona ninguna.
        </p>
      )}

      {asset.candidates.length === 0 && (
        <p role="status">
          Ninguna clase del snapshot se parece a este tipo de activo. Si la instalación sí lo
          registra, elíjala a mano; si no, déjelo sin mapear.
        </p>
      )}

      {expanded && (
        <div className="importer__detail">
          <h4>Clases candidatas</h4>
          <ul>
            {asset.candidates.map((candidate) => (
              <li key={candidate.layer}>
                <label>
                  <input
                    type="radio"
                    name={`layer-${asset.asset_type_key}`}
                    checked={chosen === candidate.layer}
                    disabled={busy || !decisions}
                    onChange={() => onChooseLayer(candidate.layer)}
                  />
                  {candidate.layer}
                </label>
                <span className={`importer__confidence importer__confidence--${confidence(candidate.score)}`}>
                  confianza {confidence(candidate.score)}
                </span>
                <ul className="importer__evidence">
                  {rankedEvidence(candidate.evidence).map((item) => (
                    <li key={`${item.signal}-${item.detail}`}>
                      <b>{item.signal}:</b> {item.detail}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>

          <label htmlFor={`manual-${asset.asset_type_key}`}>
            …o elegir otra clase del snapshot
          </label>
          <select
            id={`manual-${asset.asset_type_key}`}
            value={chosen ?? ''}
            disabled={busy || !decisions}
            onChange={(event) => event.target.value && onChooseLayer(event.target.value)}
          >
            <option value="">—</option>
            {layerNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>

          <h4>Atributos canónicos</h4>
          <table>
            <thead>
              <tr>
                <th scope="col">Atributo</th>
                <th scope="col">Campo</th>
                <th scope="col">Dominio</th>
              </tr>
            </thead>
            <tbody>
              {asset.attributes.map((attribute) => {
                const field = decisions
                  ? chosenField(decisions, asset.asset_type_key, attribute.attribute_key)
                  : null;
                const options = candidatesFor(asset, attribute.attribute_key);
                const current = options.find((option) => option.field === field);
                return (
                  <tr key={attribute.attribute_key}>
                    <th scope="row">
                      {attribute.attribute_key}
                      {attribute.required && <abbr title="obligatorio"> *</abbr>}
                    </th>
                    <td>
                      <select
                        aria-label={`Campo para ${attribute.attribute_key}`}
                        value={field ?? ''}
                        disabled={busy || !decisions || !chosen}
                        onChange={(event) =>
                          onChooseField(attribute.attribute_key, event.target.value || null)
                        }
                      >
                        <option value="">sin mapear</option>
                        {options.map((option) => (
                          <option key={option.field} value={option.field}>
                            {option.label} — confianza {confidence(option.score)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      {current?.domain ?? '—'}
                      {current?.volatile_by_business_unit && (
                        <span title="Cambia por unidad de negocio; se refresca en cada sincronización (RF-304)">
                          {' '}
                          · volátil
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {gaps.length > 0 && (
            <>
              <h4>Valores canónicos sin código en el dominio</h4>
              <ul>
                {gaps.map((gap) => (
                  <li key={gap.attributeKey}>
                    {gap.attributeKey} · {gap.domain}: {gap.unmapped.join(', ')}
                  </li>
                ))}
              </ul>
            </>
          )}

          {refusals(asset).length > 0 && (
            <>
              <h4>Campos que coincidían y se rechazaron</h4>
              <ul>
                {refusals(asset).map((refusal) => (
                  <li key={refusal.attributeKey}>
                    {refusal.attributeKey}: {refusal.reasons.join('; ')}
                  </li>
                ))}
              </ul>
            </>
          )}

          {asset.related.length > 0 && (
            <>
              <h4>Tablas repetibles propuestas</h4>
              <ul>
                {asset.related.map((related) => (
                  <li key={related.relationship}>
                    {related.as} ← {related.target_layer} ({related.relationship})
                  </li>
                ))}
              </ul>
            </>
          )}

          {chosen && (
            <button type="button" onClick={onForget} disabled={busy}>
              Esta instalación no registra este tipo de activo
            </button>
          )}
        </div>
      )}
    </li>
  );
}
