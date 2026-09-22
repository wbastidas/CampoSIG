/**
 * La pantalla del importador, renderizada (RF-301, RF-302).
 *
 * Lo que se prueba es lo que distingue esta pantalla de un formulario: que la evidencia de cada
 * candidata esté en el DOM, que una ambigüedad se anuncie sin preseleccionar nada, que publicar
 * esté cerrado mientras falte algo, y que cambiar de clase **no** deje en pantalla los campos de
 * la clase rechazada.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { AssetProposal, Draft, ProposalResponse } from '../../api/modelProfile';
import { ModelProfileScreen } from './ModelProfileScreen';

function pointAsset(overrides: Partial<AssetProposal> = {}): AssetProposal {
  return {
    asset_type_key: 'support_structure',
    geometry: 'point',
    candidates: [
      {
        layer: 'ClasePostes',
        score: 0.95,
        evidence: [
          { signal: 'nombre', detail: 'el nombre de la clase contiene «poste»', weight: 0.5 },
          { signal: 'estructura', detail: '5 de 5 atributos encuentran un campo', weight: 0.3 },
        ],
      },
      { layer: 'ClaseOtra', score: 0.4, evidence: [] },
    ],
    attributes: [
      {
        attribute_key: 'code',
        attribute_type: 'string',
        required: true,
        candidates: [
          {
            field: 'COD_ACT',
            label: 'Código',
            score: 0.9,
            evidence: [],
            domain: null,
            volatile_by_business_unit: false,
            value_map: null,
          },
        ],
        refused: ['OBJECTID: es una columna de control de la geodatabase'],
      },
      {
        attribute_key: 'feeder_code',
        attribute_type: 'string',
        required: false,
        candidates: [
          {
            field: 'ALIM',
            label: 'Alimentador',
            score: 0.8,
            evidence: [],
            domain: 'DomAlim',
            volatile_by_business_unit: true,
            value_map: null,
          },
        ],
        refused: [],
      },
    ],
    related: [],
    participates_in_geometric_network: false,
    ...overrides,
  };
}

function proposalResponse(assets: AssetProposal[], gaps: string[] = []): ProposalResponse {
  return {
    profile_id: 'gye-importado',
    proposal: { profile_id: 'gye-importado', assets, unclaimed_layer_count: 184 },
    gaps,
    layer_names: ['ClasePostes', 'ClaseOtra', 'ClaseRural'],
  };
}

function draft(overrides: Partial<Draft> = {}): Draft {
  return {
    draft_id: 'd1',
    business_unit_code: 'GYE',
    profile_id: 'gye-importado',
    version: 1,
    status: 'draft',
    ready: true,
    problems: [],
    decisions: {
      header: {
        id: 'gye-importado',
        label: null,
        provider: 'arcpy-agent',
        arcgis_version: null,
        spatial_reference: 32717,
        geometric_network: null,
        feature_dataset: null,
      },
      assets: {
        support_structure: {
          layer: 'ClasePostes',
          attributes: { code: 'COD_ACT', feeder_code: 'ALIM' },
          related: [],
          participates_in_geometric_network: false,
        },
      },
    },
    document: { profile: { id: 'gye-importado' } },
    created_by: 'dev:admin',
    updated_by: null,
    published_by: null,
    updated_at: null,
    published_at: null,
    ...overrides,
  };
}

interface Routes {
  proposal: ProposalResponse;
  current?: Draft | null;
  assetProposal?: AssetProposal;
  published?: Draft;
  saved?: Draft;
  onCall?: (url: string, init?: RequestInit) => void;
}

function mockApi(routes: Routes) {
  const ok = (body: unknown) =>
    ({ ok: true, status: 200, json: async () => body }) as unknown as Response;
  const notFound = () =>
    ({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'no hay borrador abierto' }),
    }) as unknown as Response;

  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    routes.onCall?.(url, init);
    if (url.includes('/publish')) return ok(routes.published ?? draft({ status: 'published' }));
    if (url.includes('/drafts/current')) {
      return routes.current ? ok(routes.current) : notFound();
    }
    if (url.includes('/history')) return ok([]);
    if (url.match(/\/proposal\/[^?]+/)) return ok(routes.assetProposal ?? pointAsset());
    if (url.includes('/proposal')) return ok(routes.proposal);
    if (init?.method === 'PUT') return ok(routes.saved ?? draft());
    if (init?.method === 'POST') return ok(routes.current ?? draft());
    return ok({});
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('la propuesta', () => {
  it('muestra la evidencia de cada candidata, no solo una puntuación', async () => {
    // Una puntuación que nadie puede discutir convierte aceptar un binding en pulsar un botón.
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: draft() }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'support_structure' }));
    expect(screen.getByText(/el nombre de la clase contiene «poste»/)).not.toBeNull();
    expect(screen.getByText(/5 de 5 atributos encuentran un campo/)).not.toBeNull();
  });

  it('la confianza se dice en palabras', async () => {
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: draft() }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'support_structure' }));
    expect(screen.getByText('confianza alta')).not.toBeNull();
    expect(screen.queryByText(/0\.95/)).toBeNull();
  });

  it('dice cuántas clases del snapshot no corresponden a nada, porque es lo normal', async () => {
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: draft() }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    expect(await screen.findByText(/184 clases del snapshot/)).not.toBeNull();
  });

  it('un tipo sin ninguna clase parecida lo dice, y no ofrece nada', async () => {
    const orphan = pointAsset({ asset_type_key: 'street_light', candidates: [], attributes: [] });
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([orphan]), current: draft() }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    expect(
      await screen.findByText(/Ninguna clase del snapshot se parece a este tipo de activo/),
    ).not.toBeNull();
  });
});

describe('la ambigüedad', () => {
  it('se anuncia y no se preselecciona ninguna de las dos', async () => {
    const uncertain = pointAsset({
      candidates: [
        { layer: 'ClaseAerea', score: 0.9, evidence: [] },
        { layer: 'ClaseSubterranea', score: 0.87, evidence: [] },
      ],
    });
    vi.stubGlobal(
      'fetch',
      mockApi({
        proposal: proposalResponse([uncertain]),
        current: draft({ decisions: { ...draft().decisions, assets: {} } }),
      }),
    );
    render(<ModelProfileScreen businessUnit="GYE" />);

    expect(await screen.findByText(/puntúan casi igual/)).not.toBeNull();
    expect(screen.getByText('sin clase elegida')).not.toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'support_structure' }));
    // Por el árbol de accesibilidad, no por el atributo: React fija la *propiedad* `checked` en
    // un input controlado, así que comprobar el atributo pasaría con el radio marcado.
    expect(screen.getAllByRole('radio')).toHaveLength(2);
    expect(screen.queryAllByRole('radio', { checked: true })).toHaveLength(0);
  });
});

describe('cambiar de clase', () => {
  it('reevalúa los atributos contra la clase elegida y suelta los de la rechazada', async () => {
    // El defecto: `CODIGO` existe en casi todas las clases, así que el campo elegido para la
    // clase rechazada sobreviviría al cambio y parecería decidido.
    const rescored = pointAsset({
      attributes: [
        {
          attribute_key: 'code',
          attribute_type: 'string',
          required: true,
          candidates: [
            {
              field: 'NUM_POSTE',
              label: 'Número',
              score: 0.85,
              evidence: [],
              domain: null,
              volatile_by_business_unit: false,
              value_map: null,
            },
          ],
          refused: [],
        },
      ],
    });
    vi.stubGlobal(
      'fetch',
      mockApi({
        proposal: proposalResponse([pointAsset()]),
        current: draft(),
        assetProposal: rescored,
      }),
    );
    render(<ModelProfileScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'support_structure' }));
    fireEvent.click(screen.getByRole('radio', { name: /ClaseOtra/ }));

    // Por el valor mostrado del desplegable, que es lo que ve quien revisa.
    await waitFor(() => expect(screen.getByDisplayValue(/Número/)).not.toBeNull());
    // Y la opción de la clase rechazada ya no existe: si sobreviviera, el campo parecería
    // decidido apuntando a una columna de una clase que nadie eligió.
    expect(screen.queryByRole('option', { name: /Código/ })).toBeNull();
  });
});

describe('publicar', () => {
  it('está cerrado mientras el borrador tenga impedimentos, y se dice cuáles', async () => {
    const blocked = draft({
      ready: false,
      problems: ["'support_structure.code' es obligatorio y no está mapeado"],
    });
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: blocked }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    expect(
      await screen.findByText("'support_structure.code' es obligatorio y no está mapeado"),
    ).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Publicar perfil' }).hasAttribute('disabled')).toBe(
      true,
    );
  });

  it('con el borrador completo, publica y lo dice', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi({
        proposal: proposalResponse([pointAsset()]),
        current: draft(),
        published: draft({ status: 'published', version: 2, published_by: 'dev:admin' }),
      }),
    );
    render(<ModelProfileScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Publicar perfil' }));
    expect(await screen.findByText(/Perfil publicado como versión 2/)).not.toBeNull();
  });

  it('una versión publicada ya no se vuelve a publicar', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi({
        proposal: proposalResponse([pointAsset()]),
        current: draft({ status: 'published' }),
      }),
    );
    render(<ModelProfileScreen businessUnit="GYE" />);

    const publish = await screen.findByRole('button', { name: 'Publicar perfil' });
    expect(publish.hasAttribute('disabled')).toBe(true);
  });
});

describe('sin borrador abierto', () => {
  it('se ofrece abrirlo, con los huecos de la propuesta a la vista', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi({
        proposal: proposalResponse([pointAsset()], ['no se encontró clase para street_light']),
        current: null,
      }),
    );
    render(<ModelProfileScreen businessUnit="GYE" />);

    expect(await screen.findByText('no se encontró clase para street_light')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Abrir borrador' }).hasAttribute('disabled')).toBe(
      false,
    );
    expect(screen.queryByRole('button', { name: 'Publicar perfil' })).toBeNull();
  });

  it('el identificador del perfil llega prellenado con el de la unidad', async () => {
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: null }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    expect(await screen.findByDisplayValue('gye-importado')).not.toBeNull();
  });
});

describe('lo que se rechazó y por qué', () => {
  it('un campo que coincidía por nombre y se rechazó aparece con el motivo', async () => {
    // «¿Por qué no aparece este campo?» se pregunta una vez por instalación, y merece
    // respuesta en la pantalla, no en el código.
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: draft() }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'support_structure' }));
    expect(
      screen.getByText(/OBJECTID: es una columna de control de la geodatabase/),
    ).not.toBeNull();
  });

  it('un dominio volátil por unidad se marca como tal (RF-304)', async () => {
    vi.stubGlobal('fetch', mockApi({ proposal: proposalResponse([pointAsset()]), current: draft() }));
    render(<ModelProfileScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'support_structure' }));
    const table = screen.getAllByRole('table')[0] as HTMLElement;
    expect(within(table).getByText(/volátil/)).not.toBeNull();
  });
});

describe('cuando el agente no ha corrido', () => {
  it('se muestra el motivo del servidor y no una pantalla en blanco', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 409,
            statusText: 'Conflict',
            json: async () => ({
              detail: "la unidad 'GYE' no tiene metadatos sincronizados; su agente arcpy todavía no ha corrido",
            }),
          }) as unknown as Response,
      ),
    );
    render(<ModelProfileScreen businessUnit="GYE" />);

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toMatch(/su agente arcpy todavía no ha corrido/);
  });
});
