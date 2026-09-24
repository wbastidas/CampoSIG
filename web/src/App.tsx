/**
 * The application shell: which screen, for which business unit, as which person.
 *
 * Deliberately a plain tab switch and not a router. There are four screens, each one a
 * self-contained tool, and no deep-linking requirement that a router would serve — a
 * dependency bought for a `useState` is a dependency to keep patched forever. When work-order
 * permalinks arrive, that is the moment for a router.
 *
 * The business unit is chosen here, once, from what the token says the person may act in. A
 * screen never guesses it: passing it explicitly is what keeps ADR-009 visible in the types.
 */

import { lazy, Suspense, useState } from 'react';

import { useSession } from './auth/SessionProvider';
import { defaultBusinessUnit } from './config';
import { AiDashboardScreen } from './features/ai-dashboard/AiDashboardScreen';
import { ApgScreen } from './features/apg/ApgScreen';
import { AuditScreen } from './features/audit/AuditScreen';
import { CatalogsScreen } from './features/catalogs/CatalogsScreen';
import { DispatchBoard } from './features/dispatch/DispatchBoard';
import { FormCatalogueScreen } from './features/form-catalogue/FormCatalogueScreen';
import { IntegrationsScreen } from './features/integrations/IntegrationsScreen';
import { MaintenanceScreen } from './features/maintenance/MaintenanceScreen';
import { ModelProfileScreen } from './features/model-profile/ModelProfileScreen';
import { OperationsBoard } from './features/operations/OperationsBoard';
import { PlansScreen } from './features/plans/PlansScreen';
import { PolicyScreen } from './features/policy/PolicyScreen';
import { ProposalsScreen } from './features/proposals/ProposalsScreen';
import { RegulatoryScreen } from './features/regulatory/RegulatoryScreen';
import { ReviewScreen } from './features/review/ReviewScreen';
import { ZonesScreen } from './features/zones/ZonesScreen';

/**
 * The map is loaded on demand, and only this screen is.
 *
 * MapLibre is roughly a megabyte, and it is the only screen that needs it. A supervisor who
 * spends the day in the review queue was downloading the whole map engine to never open it —
 * over the connection a business-unit office actually has.
 */
const PlannerMap = lazy(async () => ({
  default: (await import('./features/planning/PlannerMap')).PlannerMap,
}));

type Screen =
  | 'planificacion'
  | 'despliegue'
  | 'revision'
  | 'operacion'
  | 'alumbrado'
  | 'mantenimiento'
  | 'preventivo'
  | 'propuestas'
  | 'ia'
  | 'integraciones'
  | 'bitacora'
  | 'zonas'
  | 'politica'
  | 'normativa'
  | 'formularios'
  | 'catalogos'
  | 'perfil';

const SCREENS: { key: Screen; label: string; roles: string[] }[] = [
  { key: 'planificacion', label: 'Planificación', roles: ['planificador', 'supervisor'] },
  { key: 'despliegue', label: 'Despliegue', roles: ['planificador', 'supervisor'] },
  { key: 'revision', label: 'Revisión', roles: ['supervisor', 'inspector'] },
  // El tablero operativo es de quien reparte y de quien responde por el SLA (RF-130).
  { key: 'operacion', label: 'Operación', roles: ['supervisor', 'planificador'] },
  // El área de APG responde por el plazo de reposición ante el regulador (RF-131).
  { key: 'alumbrado', label: 'Alumbrado', roles: ['supervisor', 'planificador'] },
  // El área de mantenimiento planifica con los hallazgos de las inspecciones (RF-133).
  { key: 'mantenimiento', label: 'Mantenimiento', roles: ['supervisor', 'planificador'] },
  // El plan preventivo lo escribe quien planifica; el supervisor mira, porque es quien responde
  // por qué se mandó una cuadrilla a ese poste (RF-012).
  { key: 'preventivo', label: 'Plan preventivo', roles: ['planificador', 'admin_funcional'] },
  // La bandeja de propuestas es del supervisor, que es quien decide, y del planificador porque
  // alimenta su tablero. Levantar propuestas no es decidir y no se hace desde aquí (RF-013).
  { key: 'propuestas', label: 'OT propuestas', roles: ['supervisor', 'planificador'] },
  // RF-134 nombra los dos roles: el analista ML porque es su trabajo, y el supervisor porque es
  // quien decide con esos números. El servidor exige lo mismo.
  { key: 'ia', label: 'Tablero de IA', roles: ['analista_ml', 'supervisor'] },
  { key: 'integraciones', label: 'Integraciones', roles: ['admin_ti', 'admin_funcional'] },
  // Las zonas deciden qué cuadrilla cubre qué calle, así que moverlas es administración
  // funcional. El planificador entra a mirar: el servidor le niega la escritura igual (RF-152).
  { key: 'zonas', label: 'Zonas', roles: ['admin_funcional', 'planificador'] },
  // La política de captura la fija el área y la obedece el teléfono. El supervisor entra a
  // mirar, porque es quien pregunta por qué una cuadrilla hizo lo que hizo (RF-151).
  { key: 'politica', label: 'Política de captura', roles: ['admin_funcional', 'supervisor'] },
  // Los límites regulatorios son nacionales, no de una unidad. Quien los carga afirma haber
  // leído el texto oficial, y el auditor necesita ver quién lo afirmó (RF-150, ADR-007).
  { key: 'normativa', label: 'Parámetros regulatorios', roles: ['admin_funcional', 'auditor'] },
  // Publicar un formulario congela su forma, y desde ahí cada OT conserva la suya. Es un acto
  // de administración; el supervisor mira, porque es quien pregunta con qué versión se llenó
  // una OT que le llegó rara (RF-032).
  { key: 'formularios', label: 'Formularios', roles: ['admin_funcional', 'admin_ti', 'supervisor'] },
  // Un catálogo vacío es un selector sin valores, y el técnico acaba escribiendo en
  // observaciones. El supervisor mira porque es quien ve el resultado (RF-034).
  { key: 'catalogos', label: 'Catálogos', roles: ['admin_funcional', 'admin_ti', 'supervisor'] },
  // La bitácora es del auditor, y de TI para poder responder durante un incidente. No del
  // supervisor: un registro de auditoría no es un informe de gestión (RF-161).
  { key: 'bitacora', label: 'Bitácora', roles: ['auditor', 'admin_ti'] },
  // El perfil decide en qué clase aterrizan los datos de campo: administración funcional o
  // de TI, y nadie más. El servidor lo exige igual (RF-002).
  { key: 'perfil', label: 'Modelo de datos', roles: ['admin_ti', 'admin_funcional'] },
];

/** Roles that see everything, mirroring `Principal.is_corporate` on the server. */
const CORPORATE_ROLES = ['admin_ti', 'admin_funcional', 'auditor'];

export function App() {
  const session = useSession();
  const roles = session.user?.roles ?? [];
  const corporate = roles.some((role) => CORPORATE_ROLES.includes(role));

  // Hiding a tab is a convenience, not a control: the server refuses the call regardless
  // (ADR-013). Showing a supervisor a tab they cannot use would just waste their time.
  const available = SCREENS.filter(
    (screen) => corporate || screen.roles.some((role) => roles.includes(role)),
  );

  const units = session.user?.businessUnits ?? [];
  const [unit, setUnit] = useState(units[0] ?? defaultBusinessUnit);
  const [screen, setScreen] = useState<Screen>(available[0]?.key ?? 'revision');

  const operator = session.user?.username ?? session.user?.subject ?? 'desconocido';

  return (
    <div className="app">
      <header className="app-bar">
        <strong>SIGEC-Campo</strong>
        <nav aria-label="Pantallas">
          {available.map((entry) => (
            <button
              key={entry.key}
              type="button"
              aria-current={screen === entry.key}
              onClick={() => setScreen(entry.key)}
            >
              {entry.label}
            </button>
          ))}
        </nav>
        {units.length > 1 && (
          <label>
            Unidad de negocio
            <select value={unit} onChange={(event) => setUnit(event.target.value)}>
              {units.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
        )}
        <span className="app-user">{operator}</span>
        <button type="button" onClick={session.signOut}>
          Salir
        </button>
      </header>

      <main>
        {available.length === 0 && (
          <p role="alert">
            Su cuenta no tiene ningún rol que habilite una pantalla de esta plataforma. Solicite el
            rol correspondiente a la administración funcional.
          </p>
        )}
        {screen === 'planificacion' && (
          <Suspense fallback={<p>Cargando el mapa…</p>}>
            <PlannerMap businessUnit={unit} />
          </Suspense>
        )}
        {screen === 'despliegue' && <DispatchBoard businessUnit={unit} />}
        {screen === 'revision' && <ReviewScreen businessUnit={unit} reviewer={operator} />}
        {screen === 'operacion' && <OperationsBoard businessUnit={unit} />}
        {screen === 'alumbrado' && <ApgScreen businessUnit={unit} />}
        {screen === 'mantenimiento' && <MaintenanceScreen businessUnit={unit} />}
        {screen === 'preventivo' && (
          <PlansScreen
            businessUnit={unit}
            mayEdit={roles.includes('planificador') || roles.includes('admin_funcional')}
          />
        )}
        {screen === 'propuestas' && (
          <ProposalsScreen
            businessUnit={unit}
            mayDecide={roles.includes('supervisor') || roles.includes('planificador')}
          />
        )}
        {screen === 'ia' && <AiDashboardScreen businessUnit={unit} />}
        {screen === 'integraciones' && (
          <IntegrationsScreen businessUnit={unit} operator={operator} />
        )}
        {screen === 'bitacora' && <AuditScreen businessUnit={unit} />}
        {screen === 'zonas' && (
          <ZonesScreen businessUnit={unit} mayEdit={roles.includes('admin_funcional')} />
        )}
        {screen === 'politica' && (
          <PolicyScreen businessUnit={unit} mayEdit={roles.includes('admin_funcional')} />
        )}
        {screen === 'normativa' && (
          <RegulatoryScreen mayEdit={roles.includes('admin_funcional')} />
        )}
        {screen === 'catalogos' && (
          <CatalogsScreen
            businessUnit={unit}
            mayEdit={roles.includes('admin_funcional') || roles.includes('admin_ti')}
          />
        )}
        {screen === 'formularios' && (
          <FormCatalogueScreen
            mayPublish={roles.includes('admin_funcional') || roles.includes('admin_ti')}
          />
        )}
        {screen === 'perfil' && <ModelProfileScreen businessUnit={unit} />}
      </main>
    </div>
  );
}
