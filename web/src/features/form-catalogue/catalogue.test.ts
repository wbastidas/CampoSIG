/**
 * Las decisiones del catálogo de formularios (RF-032).
 *
 * Lo que se prueba es la frase que esta pantalla existe para poder decir: «este formulario cambió y
 * nadie lo publicó». Y que «nunca publicado» y «publicado pero editado después» no se mezclen: no
 * son lo mismo y no se arreglan igual.
 */

import { describe, expect, it } from 'vitest';

import type { CatalogueRow, FormVersion } from '../../api/forms';
import {
  blocksLine,
  canObsolete,
  canPublish,
  catalogueHeadline,
  catalogueRows,
  ecuadorDate,
  SITUATION_ADVICE,
  SITUATION_LABEL,
  situationOf,
  versionLine,
} from './catalogue';

function row(overrides: Partial<CatalogueRow> = {}): CatalogueRow {
  return {
    code: 'F-MT-01',
    title: 'Inspección preventiva',
    area: 'mantenimiento',
    file_version: '1.0.0',
    published_version: '1.0.0',
    has_unpublished_draft: false,
    never_published: false,
    ...overrides,
  };
}

function version(overrides: Partial<FormVersion> = {}): FormVersion {
  return {
    code: 'F-MT-01',
    version: '1.0.0',
    state: 'publicado',
    content_hash: 'a'.repeat(64),
    published_by: 'admin.funcional',
    published_at: '2026-09-20T10:00:00+00:00',
    obsoleted_at: null,
    obsoleted_by: null,
    note: null,
    blocks: ['B01', 'B02'],
    ...overrides,
  };
}

describe('situationOf', () => {
  it('nunca publicado', () => {
    expect(situationOf(row({ never_published: true, published_version: null }))).toBe('nunca');
  });

  it('publicado pero editado después', () => {
    expect(situationOf(row({ has_unpublished_draft: true, file_version: '2.0.0' }))).toBe(
      'borrador',
    );
  });

  it('al día', () => {
    expect(situationOf(row())).toBe('al-dia');
  });

  it('cada situación dice qué implica, no solo cómo se llama', () => {
    expect(SITUATION_ADVICE.nunca).toContain('puede cambiar bajo una OT ya asignada');
    expect(SITUATION_ADVICE.borrador).toContain('Nadie en campo ha visto este cambio');
    expect(Object.keys(SITUATION_LABEL).sort()).toEqual(['al-dia', 'borrador', 'nunca']);
  });
});

describe('catalogueRows', () => {
  it('lo peor primero: nunca publicado, luego borradores, luego el resto', () => {
    const ordered = catalogueRows([
      row({ code: 'C' }),
      row({ code: 'B', has_unpublished_draft: true }),
      row({ code: 'A', never_published: true, published_version: null }),
    ]);
    expect(ordered.map((item) => item.code)).toEqual(['A', 'B', 'C']);
  });

  it('dentro de la misma situación ordena por código', () => {
    const ordered = catalogueRows([row({ code: 'F-Z' }), row({ code: 'F-A' })]);
    expect(ordered.map((item) => item.code)).toEqual(['F-A', 'F-Z']);
  });
});

describe('catalogueHeadline', () => {
  it('solo dice «al día» cuando lo están todos', () => {
    expect(catalogueHeadline([row(), row({ code: 'F-AP-01' })])).toContain('todos publicados');
  });

  it('cuenta aparte lo nunca publicado y los borradores', () => {
    const line = catalogueHeadline([
      row({ never_published: true, published_version: null }),
      row({ code: 'B', has_unpublished_draft: true }),
    ]);
    expect(line).toContain('1 nunca publicado(s)');
    expect(line).toContain('1 con borrador sin publicar');
  });

  it('un catálogo vacío lo dice en vez de sonar a éxito', () => {
    expect(catalogueHeadline([])).toContain('No hay formularios');
  });
});

describe('canPublish', () => {
  it('publicar sirve cuando nunca se publicó o cuando hay un borrador', () => {
    expect(canPublish(row({ never_published: true }))).toBe(true);
    expect(canPublish(row({ has_unpublished_draft: true }))).toBe(true);
  });

  it('no sirve cuando ya está al día, y el botón no se ofrece', () => {
    expect(canPublish(row())).toBe(false);
  });
});

describe('las versiones', () => {
  it('una versión se lee con su estado, su autor y su fecha', () => {
    expect(versionLine(version())).toBe(
      'v1.0.0 · Publicada · publicada por admin.funcional el 20/09/2026',
    );
  });

  it('una obsoleta se dice obsoleta', () => {
    expect(versionLine(version({ state: 'obsoleto' }))).toContain('Obsoleta');
  });

  it('un estado que el servidor añada después se muestra tal cual', () => {
    expect(versionLine(version({ state: 'algo_nuevo' }))).toContain('algo_nuevo');
  });

  it('no se inventa un autor cuando no hay', () => {
    expect(versionLine(version({ published_by: null }))).toContain('sin registrar');
  });

  it('los bloques congelados se muestran, que es de qué está hecha la forma', () => {
    expect(blocksLine(version())).toBe('Bloques: B01, B02.');
  });

  it('una versión sin bloques lo dice en vez de quedar en blanco', () => {
    expect(blocksLine(version({ blocks: [] }))).toContain('Sin bloques');
  });

  it('solo una publicada se puede retirar', () => {
    expect(canObsolete(version())).toBe(true);
    expect(canObsolete(version({ state: 'obsoleto' }))).toBe(false);
  });
});

describe('ecuadorDate', () => {
  it('escribe la fecha como en Ecuador', () => {
    expect(ecuadorDate('2026-09-20T10:00:00+00:00')).toBe('20/09/2026');
  });

  it('una fecha ausente no se inventa', () => {
    expect(ecuadorDate(null)).toBe('—');
  });
});
