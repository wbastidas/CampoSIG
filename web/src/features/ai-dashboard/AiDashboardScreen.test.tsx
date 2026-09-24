/**
 * El tablero de IA, renderizado (RF-134, RF-111a).
 *
 * Lo que se comprueba es que la pantalla no convierta una ausencia en un dato: una tasa suprimida
 * no puede aparecer como «0 %», un panel vacío tiene que decir que no había nada que medir —y no
 * dejar creer que no hay nada que arreglar—, y la advertencia de qué mide el error de palabras
 * tiene que estar a la vista, porque quien lea el número lo va a citar.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { AiDashboard } from '../../api/analytics';
import { AiDashboardScreen } from './AiDashboardScreen';

const EMPTY_AGREEMENT = {
  both_clear: 0,
  both_flagged: 0,
  supervisor_only: 0,
  agent_only: 0,
  pending: 0,
  unpaired: 0,
  paired: 0,
  observed_agreement: null,
  kappa: null,
  kappa_floor: 0.6,
  meets_floor: null,
  min_sample: 10,
};

function board(overrides: Partial<AiDashboard> = {}): AiDashboard {
  return {
    since: null,
    until: null,
    min_for_a_rate: 5,
    fields: [],
    visual_classes: [],
    word_errors: null,
    voice_adoption: [],
    fleet: [],
    agreement: EMPTY_AGREEMENT,
    ...overrides,
  };
}

function mockApi(body: AiDashboard) {
  return vi.fn(async () => ({ ok: true, status: 200, json: async () => body }) as unknown as Response);
}

afterEach(() => vi.unstubAllGlobals());

describe('la aceptación por campo', () => {
  it('muestra la tasa con su denominador y el consejo', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        board({
          fields: [
            {
              field_key: 'material',
              proposals: 40,
              accepted: 24,
              corrected: 16,
              acceptance: 0.6,
              mean_confidence: 0.95,
            },
          ],
        }),
      ),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    expect(await screen.findByText(/60,0 % \(24 de 40\)/)).toBeTruthy();
    // Equivocado y seguro: el consejo es revisar el umbral, no el modelo.
    expect(screen.getByText(/revisar el umbral/)).toBeTruthy();
  });

  it('una tasa suprimida no se pinta como cero por ciento', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        board({
          fields: [
            {
              field_key: 'material',
              proposals: 2,
              accepted: 2,
              corrected: 0,
              acceptance: null,
              mean_confidence: 0.9,
            },
          ],
        }),
      ),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    expect(await screen.findByText(/sin muestra suficiente: 2 de 5/)).toBeTruthy();
    expect(screen.queryByText(/100,0 %/)).toBeNull();
    expect(screen.queryByText(/0,0 %/)).toBeNull();
  });

  it('sin propuestas dice que ningún modelo propuso, no que todo esté bien', async () => {
    vi.stubGlobal('fetch', mockApi(board()));
    render(<AiDashboardScreen businessUnit="GYE" />);
    expect(await screen.findByText(/Ningún modelo propuso valores/)).toBeTruthy();
  });
});

describe('el error de palabras', () => {
  it('muestra la advertencia de qué mide, tal como la manda el servidor', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        board({
          word_errors: {
            reference_words: 120,
            errors: 12,
            measured_fields: 20,
            unmeasurable_fields: 380,
            error_rate: 0.1,
            measures: 'No es un WER contra una transcripción de referencia.',
          },
        }),
      ),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    expect(await screen.findByText(/10,0 % de palabras con error/)).toBeTruthy();
    expect(screen.getByText(/No es un WER contra una transcripción de referencia/)).toBeTruthy();
    // Y cuánto quedó fuera: una tasa sobre veinte campos de cuatrocientos no es la tasa de nada.
    expect(screen.getByText(/380 de 400 campos dictados no son texto/)).toBeTruthy();
  });
});

describe('las versiones en la flota', () => {
  it('avisa cuando una versión nueva acepta peor que la anterior', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        board({
          fleet: [
            {
              model_name: 'mobilenetv3-pole',
              model_version: '2026.08',
              origin: 'vision',
              proposals: 40,
              accepted: 36,
              acceptance: 0.9,
              first_seen: '2026-08-01T00:00:00Z',
              last_seen: '2026-08-30T00:00:00Z',
            },
            {
              model_name: 'mobilenetv3-pole',
              model_version: '2026.09',
              origin: 'vision',
              proposals: 40,
              accepted: 24,
              acceptance: 0.6,
              first_seen: '2026-09-01T00:00:00Z',
              last_seen: '2026-09-20T00:00:00Z',
            },
          ],
        }),
      ),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('2026.09');
    expect(alert.textContent).toContain('candidata a reversión');
  });
});

describe('la adopción de la voz', () => {
  it('dice para qué es el panel, porque un número por persona se lee como calificación', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        board({
          voice_adoption: [
            {
              user: 'escribe.todo',
              responses: 12,
              responses_with_voice: 0,
              voice_fields: 0,
              adoption: 0,
            },
          ],
        }),
      ),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    expect(await screen.findByText(/no para calificar a nadie/)).toBeTruthy();
    expect(screen.getByText(/escribe.todo/)).toBeTruthy();
    // Un cero real sí se muestra como cero: es el dato que importa.
    expect(screen.getByText(/0,0 % \(0 de 12\)/)).toBeTruthy();
  });
});

describe('la concordancia (RF-111a)', () => {
  it('aparece en el tablero, que es lo que pide el criterio de aceptación', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        board({
          agreement: {
            ...EMPTY_AGREEMENT,
            both_clear: 30,
            both_flagged: 20,
            supervisor_only: 2,
            agent_only: 3,
            paired: 55,
            observed_agreement: 0.909,
            kappa: 0.81,
            meets_floor: true,
          },
        }),
      ),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    expect(await screen.findByText(/Kappa 0,81/)).toBeTruthy();
    expect(screen.getByText(/solo sobre la muestra ciega/)).toBeTruthy();
  });
});

describe('cuando el servidor falla', () => {
  it('lo dice en vez de mostrar un tablero vacío', async () => {
    // Un tablero en blanco se lee como «no hay nada que arreglar», que es la lectura contraria.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'la consulta falló' }),
      }) as unknown as Response),
    );
    render(<AiDashboardScreen businessUnit="GYE" />);

    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('la consulta falló'));
    expect(screen.queryByText(/Ningún modelo propuso/)).toBeNull();
    // Y tampoco se queda diciendo «cargando»: ya no está cargando, falló.
    expect(screen.queryByText(/Cargando el tablero/)).toBeNull();
  });
});
