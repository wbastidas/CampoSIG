# 02 · Catálogo de Relaciones

[⬅ Volver al índice](00_Indice_y_Conceptos.md) · [Dominios](01_Dominios.md) · [Clases: Redes y Soporte](03_Clases_Redes_y_Soporte.md) · [Clases: Protección y Potencia](04_Clases_Proteccion_y_Potencia.md) · [Clases: Generación/Subestaciones](05_Clases_Generacion_Subestaciones_Fuentes.md) · [Clases: Consumidores/Alumbrado](06_Clases_Consumidores_y_Alumbrado.md)

Este archivo cataloga las **79 relaciones** (relationship classes) formales de la geodatabase — es decir, vínculos declarados a nivel de esquema con clave origen/destino, cardinalidad y reglas. **No incluye** la conectividad de la red geométrica (trazado eléctrico aguas arriba/abajo), que se resuelve por topología espacial y por los campos `CIRCUITSOURCEGUID` / `PARENTCIRCUITSOURCEGUID` — ver [00_Indice_y_Conceptos.md → Conectividad eléctrica](00_Indice_y_Conceptos.md#conectividad-eléctrica-y-trazado-source--sink)

## Cómo leer cada relación

- **Cardinalidad** `One To One` / `One To Many`: cuántos registros del destino puede tener cada registro del origen.
- **Clave**: el campo que une ambas tablas — casi siempre `GLOBALID` en el origen (*Origin Primary Key*) contra un campo `...GLOBALID` en el destino (*Origin Foreign Key*). En ArcGIS esto se resuelve automáticamente al editar en el software, pero **para SQL/consultas directas hay que hacer el join manualmente** con estos campos.
- **Compuesta (Composite)**: si es `Yes`, al borrar el origen se borran en cascada los destinos relacionados (relación de composición fuerte); si es `No`, son independientes.
- **Reglas (Rules)**: si es `Yes`, la relación tiene reglas de subtipo configuradas en el esquema (qué subtipo de origen puede vincularse a qué subtipo de destino).

---

## Índice completo

| # | Relación | Origen | Destino | Cardinalidad | Compuesta | Reglas |
|---|---|---|---|---|---|---|
| 1 | [AtribConsumidor_ConexConsumidor](#atribconsumidorconexconsumidor) | [`ATRIBUTOSCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#atributosconsumidor) | [`CONEXIONCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#conexionconsumidor) | One To One | No | No |
| 2 | [CatEstruc_EstrucNivel](#catestrucestrucnivel) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many | No | No |
| 3 | [CatEstruc_EstrucPoste](#catestrucestrucposte) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`ESTRUCTURAENPOSTE`](03_Clases_Redes_y_Soporte.md#estructuraenposte) | One To Many | No | No |
| 4 | [CatEstruc_Luminaria](#catestrucluminaria) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | One To Many | No | No |
| 5 | [CatEstruc_Pararrayos](#catestrucpararrayos) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Pararrayos`](04_Clases_Proteccion_y_Potencia.md#pararrayos) | One To Many | No | No |
| 6 | [CatEstruc_PuestoProtBT](#catestrucpuestoprotbt) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many | No | No |
| 7 | [CatEstruc_PuestoSecc](#catestrucpuestosecc) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) | One To Many | No | No |
| 8 | [CatEstruc_PuestoSeccFus](#catestrucpuestoseccfus) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many | No | No |
| 9 | [CatEstruc_PuntoApertura](#catestrucpuntoapertura) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuntoApertura`](03_Clases_Redes_y_Soporte.md#puntoapertura) | One To Many | No | No |
| 10 | [CatEstruc_PuntoMiscelaneo](#catestrucpuntomiscelaneo) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuntoMiscelaneo`](03_Clases_Redes_y_Soporte.md#puntomiscelaneo) | One To Many | No | No |
| 11 | [CatEstruc_Semaforo](#catestrucsemaforo) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many | No | No |
| 12 | [CatEstruc_Tensor](#catestructensor) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Tensor`](03_Clases_Redes_y_Soporte.md#tensor) | One To Many | No | No |
| 13 | [CatEstruc_TramoBTAFase](#catestructramobtafase) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) | One To Many | No | No |
| 14 | [CatEstruc_TramoBTANeutro](#catestructramobtaneutro) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) | One To Many | No | No |
| 15 | [CatEstruc_TramoBTSFase](#catestructramobtsfase) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) | One To Many | No | No |
| 16 | [CatEstruc_TramoBTSNeutro](#catestructramobtsneutro) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) | One To Many | No | No |
| 17 | [CatEstruc_TramoDistAereoFase](#catestructramodistaereofase) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionAereo`](03_Clases_Redes_y_Soporte.md#tramodistribucionaereo) | One To Many | No | No |
| 18 | [CatEstruc_TramoDistAereoNeutro](#catestructramodistaereoneutro) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionAereo`](03_Clases_Redes_y_Soporte.md#tramodistribucionaereo) | One To Many | No | No |
| 19 | [CatEstruc_TramoDistSubterrFase](#catestructramodistsubterrfase) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramodistribucionsubterraneo) | One To Many | No | No |
| 20 | [CatEstruc_TramoDistSubterrNeutro](#catestructramodistsubterrneutro) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramodistribucionsubterraneo) | One To Many | No | No |
| 21 | [CatEstruc_TramoSubtAereoFase](#catestructramosubtaereofase) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) | One To Many | No | No |
| 22 | [CatEstruc_TramoSubtAereoNeutro](#catestructramosubtaereoneutro) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) | One To Many | No | No |
| 23 | [CatEstruc_TramoSubtSubterraneoFase](#catestructramosubtsubterraneofase) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) | One To Many | No | No |
| 24 | [CatEstruc_TramoSubtSubterraneoNeutro](#catestructramosubtsubterraneoneutro) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) | One To Many | No | No |
| 25 | [CatEstruc_UnidadCapacitor](#catestrucunidadcapacitor) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor) | One To Many | No | No |
| 26 | [CatEstruc_UnidadProtecDinamico](#catestrucunidadprotecdinamico) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico) | One To Many | No | No |
| 27 | [CatEstruc_UnidadReguladorTension](#catestrucunidadreguladortension) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension) | One To Many | No | No |
| 28 | [CatEstruc_UnidadTransDistribucion](#catestrucunidadtransdistribucion) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion) | One To Many | No | No |
| 29 | [CatEstruc_UnidadTransPotencia](#catestrucunidadtranspotencia) | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia) | One To Many | No | No |
| 30 | [DATOSOPERADOR_OPERADORA](#datosoperadoroperadora) | [`DATOSOPERADORA`](05_Clases_Generacion_Subestaciones_Fuentes.md#datosoperadora) | [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte) | One To Many | No | No |
| 31 | [EstrucNivel_PuestoCorrFacPot](#estrucnivelpuestocorrfacpot) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) | One To Many | No | No |
| 32 | [EstrucNivel_PuestoProtBT](#estrucnivelpuestoprotbt) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many | No | No |
| 33 | [EstrucNivel_PuestoProtDin](#estrucnivelpuestoprotdin) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | One To Many | No | No |
| 34 | [EstrucNivel_PuestoRegTens](#estrucnivelpuestoregtens) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) | One To Many | No | No |
| 35 | [EstrucNivel_PuestoSecc](#estrucnivelpuestosecc) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) | One To Many | No | No |
| 36 | [EstrucNivel_PuestoSeccFus](#estrucnivelpuestoseccfus) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many | No | No |
| 37 | [EstrucNivel_PuestoTransDist](#estrucnivelpuestotransdist) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many | No | No |
| 38 | [EstrucNivel_PuestoTransPot](#estrucnivelpuestotranspot) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | One To Many | No | No |
| 39 | [EstrucNivel_PuntoAper](#estrucnivelpuntoaper) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuntoApertura`](03_Clases_Redes_y_Soporte.md#puntoapertura) | One To Many | No | No |
| 40 | [EstrucNivel_PuntoCarga](#estrucnivelpuntocarga) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many | No | No |
| 41 | [EstrucSop_EstrucEnPoste](#estrucsopestrucenposte) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`ESTRUCTURAENPOSTE`](03_Clases_Redes_y_Soporte.md#estructuraenposte) | One To Many | No | No |
| 42 | [EstrucSop_InstEnPoste](#estrucsopinstenposte) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`INSTITUCIONENPOSTE`](03_Clases_Redes_y_Soporte.md#institucionenposte) | One To Many | No | No |
| 43 | [EstrucSop_Luminaria](#estrucsopluminaria) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | One To Many | No | No |
| 44 | [EstrucSop_PuestoCorrFacPot](#estrucsoppuestocorrfacpot) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) | One To Many | No | No |
| 45 | [EstrucSop_PuestoProtBT](#estrucsoppuestoprotbt) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many | No | No |
| 46 | [EstrucSop_PuestoProtDinam](#estrucsoppuestoprotdinam) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | One To Many | No | No |
| 47 | [EstrucSop_PuestoRegTens](#estrucsoppuestoregtens) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) | One To Many | No | No |
| 48 | [EstrucSop_PuestoSecc](#estrucsoppuestosecc) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) | One To Many | No | No |
| 49 | [EstrucSop_PuestoSeccFus](#estrucsoppuestoseccfus) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many | No | No |
| 50 | [EstrucSop_PuestoTransDist](#estrucsoppuestotransdist) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many | No | No |
| 51 | [EstrucSop_PuntoCarga](#estrucsoppuntocarga) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many | No | No |
| 52 | [EstrucSop_Semaforo](#estrucsopsemaforo) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many | No | No |
| 53 | [EstrucSop_Tensor](#estrucsoptensor) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`Tensor`](03_Clases_Redes_y_Soporte.md#tensor) | One To Many | No | No |
| 54 | [Luminaria_UnidadLuminaria](#luminariaunidadluminaria) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | [`UNIDADLUMINARIA`](06_Clases_Consumidores_y_Alumbrado.md#unidadluminaria) | One To One | No | No |
| 55 | [POSTE_OPERADORAPOSTE](#posteoperadoraposte) | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte) | One To Many | No | No |
| 56 | [PuestoCorrFacPot_UnidadCapacitor](#puestocorrfacpotunidadcapacitor) | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) | [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor) | One To Many | Yes | No |
| 57 | [PuestoProtBT_UnidadProtBT](#puestoprotbtunidadprotbt) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | [`UNIDADPROTECCIONBAJATENSION`](04_Clases_Proteccion_y_Potencia.md#unidadproteccionbajatension) | One To Many | Yes | No |
| 58 | [PuestoProtDinam_CircuitoFuente](#puestoprotdinamcircuitofuente) | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | [`CIRCUITOFUENTE`](05_Clases_Generacion_Subestaciones_Fuentes.md#circuitofuente) | One To One | No | No |
| 59 | [PuestoProtDinam_UnidadProtDinam](#puestoprotdinamunidadprotdinam) | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico) | One To Many | Yes | No |
| 60 | [PuestoRegTens_UnidadRegTens](#puestoregtensunidadregtens) | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) | [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension) | One To Many | Yes | No |
| 61 | [PuestoSeccFusible_UnidadFusible](#puestoseccfusibleunidadfusible) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | [`UNIDADFUSIBLE`](04_Clases_Proteccion_y_Potencia.md#unidadfusible) | One To Many | Yes | No |
| 62 | [PuestoTransDist_Luminaria](#puestotransdistluminaria) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | One To Many | No | No |
| 63 | [PuestoTransDist_PuestoProtBT](#puestotransdistpuestoprotbt) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many | No | No |
| 64 | [PuestoTransDist_PuestoSeccFus](#puestotransdistpuestoseccfus) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many | No | No |
| 65 | [PuestoTransDist_PuntoCarga](#puestotransdistpuntocarga) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many | No | No |
| 66 | [PuestoTransDist_Semaforo](#puestotransdistsemaforo) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many | No | No |
| 67 | [PuestoTransDist_TramoBTA](#puestotransdisttramobta) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) | One To Many | No | No |
| 68 | [PuestoTransDist_TramoBTS](#puestotransdisttramobts) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) | One To Many | No | No |
| 69 | [PuestoTransDist_UnidadTransDist](#puestotransdistunidadtransdist) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion) | One To Many | Yes | No |
| 70 | [PuestoTransPot_TramoSTA](#puestotranspottramosta) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) | One To Many | No | No |
| 71 | [PuestoTransPot_TramoSTS](#puestotranspottramosts) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) | One To Many | No | No |
| 72 | [PuestoTransPot_UnidadTransPot](#puestotranspotunidadtranspot) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia) | One To Many | Yes | No |
| 73 | [PuntoCarga_ConexConsumidor](#puntocargaconexconsumidor) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`CONEXIONCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#conexionconsumidor) | One To Many | Yes | No |
| 74 | [PuntoCarga_Generador](#puntocargagenerador) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`Generador`](05_Clases_Generacion_Subestaciones_Fuentes.md#generador) | One To One | No | No |
| 75 | [PuntoCarga_GeneradorDist](#puntocargageneradordist) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`GeneradorDistribuido`](05_Clases_Generacion_Subestaciones_Fuentes.md#generadordistribuido) | One To One | No | No |
| 76 | [PuntoCarga_MotorInduccion](#puntocargamotorinduccion) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`MOTORINDUCCION`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorinduccion) | One To Many | Yes | No |
| 77 | [PuntoCarga_MotorSincrono](#puntocargamotorsincrono) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`MOTORSINCRONO`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorsincrono) | One To Many | Yes | No |
| 78 | [Semaforo_ServicioCAlles](#semaforoserviciocalles) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | [`SERVICIOCALLES`](03_Clases_Redes_y_Soporte.md#serviciocalles) | One To Many | Yes | No |
| 79 | [Subestacion_PuestoTransfPot](#subestacionpuestotransfpot) | [`Subestacion`](05_Clases_Generacion_Subestaciones_Fuentes.md#subestacion) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | One To Many | No | No |

---

## Detalle por relación

### AtribConsumidor_ConexConsumidor
<a id="atribconsumidorconexconsumidor"></a>

**[`ATRIBUTOSCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#atributosconsumidor) → [`CONEXIONCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#conexionconsumidor)** &nbsp;·&nbsp; Cardinalidad: **One To One** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`ATRIBUTOSCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#atributosconsumidor) | [`CONEXIONCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#conexionconsumidor) |
| Clave (join) | `CodigoUnico ( Origin Primary Key )` | `CodigoUnico ( Origin Foreign Key )` |
| Etiqueta | Atributos de Consumidor | Conexion de Consumidor |

### CatEstruc_EstrucNivel
<a id="catestrucestrucnivel"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Estructura Nivel |

### CatEstruc_EstrucPoste
<a id="catestrucestrucposte"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`ESTRUCTURAENPOSTE`](03_Clases_Redes_y_Soporte.md#estructuraenposte)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`ESTRUCTURAENPOSTE`](03_Clases_Redes_y_Soporte.md#estructuraenposte) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Estructura en Poste |

### CatEstruc_Luminaria
<a id="catestrucluminaria"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Luminaria |

### CatEstruc_Pararrayos
<a id="catestrucpararrayos"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`Pararrayos`](04_Clases_Proteccion_y_Potencia.md#pararrayos)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Pararrayos`](04_Clases_Proteccion_y_Potencia.md#pararrayos) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Pararrayos |

### CatEstruc_PuestoProtBT
<a id="catestrucpuestoprotbt"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) |
| Clave (join) | `CodigoEstructura ( Origin Primary Key )` | `CodigoEstructura ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Puesto Proteccion Baja Tension |

### CatEstruc_PuestoSecc
<a id="catestrucpuestosecc"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) |
| Clave (join) | `CodigoEstructura ( Origin Primary Key )` | `CodigoEstructura ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Puesto Seccionador |

### CatEstruc_PuestoSeccFus
<a id="catestrucpuestoseccfus"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) |
| Clave (join) | `CodigoEstructura ( Origin Primary Key )` | `CodigoEstructura ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Puesto Seccionador Fusible |

### CatEstruc_PuntoApertura
<a id="catestrucpuntoapertura"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`PuntoApertura`](03_Clases_Redes_y_Soporte.md#puntoapertura)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuntoApertura`](03_Clases_Redes_y_Soporte.md#puntoapertura) |
| Clave (join) | `CodigoEstructura ( Origin Primary Key )` | `CodigoEstructura ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Punto Apertura |

### CatEstruc_PuntoMiscelaneo
<a id="catestrucpuntomiscelaneo"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`PuntoMiscelaneo`](03_Clases_Redes_y_Soporte.md#puntomiscelaneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`PuntoMiscelaneo`](03_Clases_Redes_y_Soporte.md#puntomiscelaneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Punto Miscelaneo |

### CatEstruc_Semaforo
<a id="catestrucsemaforo"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | CATALOGO ESTRUCTURA | Semaforo |

### CatEstruc_Tensor
<a id="catestructensor"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`Tensor`](03_Clases_Redes_y_Soporte.md#tensor)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`Tensor`](03_Clases_Redes_y_Soporte.md#tensor) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Tensor |

### CatEstruc_TramoBTAFase
<a id="catestructramobtafase"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORFASE ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura - Fase | Tramo BTA - Fase |

### CatEstruc_TramoBTANeutro
<a id="catestructramobtaneutro"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORNEUTRO ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Neutro | Tramo BTA-Neutro |

### CatEstruc_TramoBTSFase
<a id="catestructramobtsfase"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORFASE ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Fase | TramoBTS-Fase |

### CatEstruc_TramoBTSNeutro
<a id="catestructramobtsneutro"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORNEUTRO ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Neutro | Tramo BTS-Neutro |

### CatEstruc_TramoDistAereoFase
<a id="catestructramodistaereofase"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoDistribucionAereo`](03_Clases_Redes_y_Soporte.md#tramodistribucionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionAereo`](03_Clases_Redes_y_Soporte.md#tramodistribucionaereo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORFASE ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Fase | Tramo DistAereo-Fase |

### CatEstruc_TramoDistAereoNeutro
<a id="catestructramodistaereoneutro"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoDistribucionAereo`](03_Clases_Redes_y_Soporte.md#tramodistribucionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionAereo`](03_Clases_Redes_y_Soporte.md#tramodistribucionaereo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORNEUTRO ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Neutro | Tramo DistAereo-Neutro |

### CatEstruc_TramoDistSubterrFase
<a id="catestructramodistsubterrfase"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoDistribucionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramodistribucionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramodistribucionsubterraneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORFASE ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Fase | Tramo DistSub-Fase |

### CatEstruc_TramoDistSubterrNeutro
<a id="catestructramodistsubterrneutro"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoDistribucionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramodistribucionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoDistribucionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramodistribucionsubterraneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORNEUTRO ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura-Neutro | Tramo DistSub-Neutro |

### CatEstruc_TramoSubtAereoFase
<a id="catestructramosubtaereofase"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORFASE ( Origin Foreign Key )` |
| Etiqueta | CATALOGOESTRUCTURA | TramoSubtransmisionAereo |

### CatEstruc_TramoSubtAereoNeutro
<a id="catestructramosubtaereoneutro"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORNEUTRO ( Origin Foreign Key )` |
| Etiqueta | CATALOGOESTRUCTURA | TramoSubtransmisionAereo |

### CatEstruc_TramoSubtSubterraneoFase
<a id="catestructramosubtsubterraneofase"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORFASE ( Origin Foreign Key )` |
| Etiqueta | CATALOGOESTRUCTURA | TramoSubtransmisionSubterraneo |

### CatEstruc_TramoSubtSubterraneoNeutro
<a id="catestructramosubtsubterraneoneutro"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOCONDUCTORNEUTRO ( Origin Foreign Key )` |
| Etiqueta | CATALOGOESTRUCTURA | TramoSubtransmisionSubterraneo |

### CatEstruc_UnidadCapacitor
<a id="catestrucunidadcapacitor"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Unidad Capacitor |

### CatEstruc_UnidadProtecDinamico
<a id="catestrucunidadprotecdinamico"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Unidad Proteccion Dinamico |

### CatEstruc_UnidadReguladorTension
<a id="catestrucunidadreguladortension"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Unidad Regulador Tension |

### CatEstruc_UnidadTransDistribucion
<a id="catestrucunidadtransdistribucion"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Unidad Trans Distribucion |

### CatEstruc_UnidadTransPotencia
<a id="catestrucunidadtranspotencia"></a>

**[`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) → [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia) |
| Clave (join) | `CODIGOESTRUCTURA ( Origin Primary Key )` | `CODIGOESTRUCTURA ( Origin Foreign Key )` |
| Etiqueta | Catalogo Estructura | Unidad Trans Potencia |

### DATOSOPERADOR_OPERADORA
<a id="datosoperadoroperadora"></a>

**[`DATOSOPERADORA`](05_Clases_Generacion_Subestaciones_Fuentes.md#datosoperadora) → [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`DATOSOPERADORA`](05_Clases_Generacion_Subestaciones_Fuentes.md#datosoperadora) | [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte) |
| Clave (join) | `CODIGOOPERADORA ( Origin Primary Key )` | `OPERADORA ( Origin Foreign Key )` |
| Etiqueta | SIGELEC.DATOSOPERADORA | SIGELEC.OPERADORAENPOSTE |

### EstrucNivel_PuestoCorrFacPot
<a id="estrucnivelpuestocorrfacpot"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura A Nivel | Puesto Corrector Factor Potencia |

### EstrucNivel_PuestoProtBT
<a id="estrucnivelpuestoprotbt"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Puesto Proteccion BT |

### EstrucNivel_PuestoProtDin
<a id="estrucnivelpuestoprotdin"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Puesto Proteccion Dinamico |

### EstrucNivel_PuestoRegTens
<a id="estrucnivelpuestoregtens"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Regulador Tension |

### EstrucNivel_PuestoSecc
<a id="estrucnivelpuestosecc"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Puesto Seccionador |

### EstrucNivel_PuestoSeccFus
<a id="estrucnivelpuestoseccfus"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Puesto Seccionador Fusible |

### EstrucNivel_PuestoTransDist
<a id="estrucnivelpuestotransdist"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Puesto Transformador Dist |

### EstrucNivel_PuestoTransPot
<a id="estrucnivelpuestotranspot"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura A Nivel | Puesto Transf Potencia |

### EstrucNivel_PuntoAper
<a id="estrucnivelpuntoaper"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuntoApertura`](03_Clases_Redes_y_Soporte.md#puntoapertura)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuntoApertura`](03_Clases_Redes_y_Soporte.md#puntoapertura) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Punto Apertura |

### EstrucNivel_PuntoCarga
<a id="estrucnivelpuntocarga"></a>

**[`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) → [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURANIVELGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura a Nivel | Punto Carga |

### EstrucSop_EstrucEnPoste
<a id="estrucsopestrucenposte"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`ESTRUCTURAENPOSTE`](03_Clases_Redes_y_Soporte.md#estructuraenposte)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`ESTRUCTURAENPOSTE`](03_Clases_Redes_y_Soporte.md#estructuraenposte) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | ESTRUCTURA EN POSTE |

### EstrucSop_InstEnPoste
<a id="estrucsopinstenposte"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`INSTITUCIONENPOSTE`](03_Clases_Redes_y_Soporte.md#institucionenposte)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`INSTITUCIONENPOSTE`](03_Clases_Redes_y_Soporte.md#institucionenposte) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | INSTITUCION EN POSTE |

### EstrucSop_Luminaria
<a id="estrucsopluminaria"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Luminaria |

### EstrucSop_PuestoCorrFacPot
<a id="estrucsoppuestocorrfacpot"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Corrector Factor Pot |

### EstrucSop_PuestoProtBT
<a id="estrucsoppuestoprotbt"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Proteccion BT |

### EstrucSop_PuestoProtDinam
<a id="estrucsoppuestoprotdinam"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Proteccion Dinamico |

### EstrucSop_PuestoRegTens
<a id="estrucsoppuestoregtens"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Regulador Tension |

### EstrucSop_PuestoSecc
<a id="estrucsoppuestosecc"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Seccionador |

### EstrucSop_PuestoSeccFus
<a id="estrucsoppuestoseccfus"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Seccionador Fusible |

### EstrucSop_PuestoTransDist
<a id="estrucsoppuestotransdist"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Puesto Transf Distribucion |

### EstrucSop_PuntoCarga
<a id="estrucsoppuntocarga"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Punto Carga |

### EstrucSop_Semaforo
<a id="estrucsopsemaforo"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | EstructuraSoporte | Semaforo |

### EstrucSop_Tensor
<a id="estrucsoptensor"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`Tensor`](03_Clases_Redes_y_Soporte.md#tensor)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`Tensor`](03_Clases_Redes_y_Soporte.md#tensor) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `ESTRUCTURASOPORTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Estructura Soporte | Tensor |

### Luminaria_UnidadLuminaria
<a id="luminariaunidadluminaria"></a>

**[`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) → [`UNIDADLUMINARIA`](06_Clases_Consumidores_y_Alumbrado.md#unidadluminaria)** &nbsp;·&nbsp; Cardinalidad: **One To One** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | [`UNIDADLUMINARIA`](06_Clases_Consumidores_y_Alumbrado.md#unidadluminaria) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `LUMINARIAGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Luminaria | Unidad Luminaria |

### POSTE_OPERADORAPOSTE
<a id="posteoperadoraposte"></a>

**[`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) → [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `POSTEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | SIGELEC.EstructuraSoporte | SIGELEC.OPERADORAENPOSTE |

### PuestoCorrFacPot_UnidadCapacitor
<a id="puestocorrfacpotunidadcapacitor"></a>

**[`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) → [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) | [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOCORRFACPOTGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Corrector Factor Potencia | Unidad Capacitor |

### PuestoProtBT_UnidadProtBT
<a id="puestoprotbtunidadprotbt"></a>

**[`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) → [`UNIDADPROTECCIONBAJATENSION`](04_Clases_Proteccion_y_Potencia.md#unidadproteccionbajatension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | [`UNIDADPROTECCIONBAJATENSION`](04_Clases_Proteccion_y_Potencia.md#unidadproteccionbajatension) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOPROTECCIONBTGLOBALID ( Origin Foreign Key )` |
| Etiqueta | PuestoProteccionBajaTension | UNIDADPROTECCIONBAJATENSION |

### PuestoProtDinam_CircuitoFuente
<a id="puestoprotdinamcircuitofuente"></a>

**[`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) → [`CIRCUITOFUENTE`](05_Clases_Generacion_Subestaciones_Fuentes.md#circuitofuente)** &nbsp;·&nbsp; Cardinalidad: **One To One** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | [`CIRCUITOFUENTE`](05_Clases_Generacion_Subestaciones_Fuentes.md#circuitofuente) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOPROTDINAMGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Proteccion Dinamico | Circuito Fuente |

### PuestoProtDinam_UnidadProtDinam
<a id="puestoprotdinamunidadprotdinam"></a>

**[`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) → [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOPROTDINAMGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Proteccion Dinamico | Unidad Proteccion Dinamico |

### PuestoRegTens_UnidadRegTens
<a id="puestoregtensunidadregtens"></a>

**[`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) → [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) | [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOREGTENSGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Regulador Tension | Unidad Regulador Tension |

### PuestoSeccFusible_UnidadFusible
<a id="puestoseccfusibleunidadfusible"></a>

**[`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) → [`UNIDADFUSIBLE`](04_Clases_Proteccion_y_Potencia.md#unidadfusible)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | [`UNIDADFUSIBLE`](04_Clases_Proteccion_y_Potencia.md#unidadfusible) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOSECFUSIBLEGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Seccionador Fusible | Unidad Fusible |

### PuestoTransDist_Luminaria
<a id="puestotransdistluminaria"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | PuestoTransfDistribucion | Luminaria |

### PuestoTransDist_PuestoProtBT
<a id="puestotransdistpuestoprotbt"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transformador Dist | Puesto Proteccion Baja Tension |

### PuestoTransDist_PuestoSeccFus
<a id="puestotransdistpuestoseccfus"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transformador Dist. | Puesto Seccionador Fusible |

### PuestoTransDist_PuntoCarga
<a id="puestotransdistpuntocarga"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transformador Distribucio | Punto Carga |

### PuestoTransDist_Semaforo
<a id="puestotransdistsemaforo"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transf Distribucion | Semaforo |

### PuestoTransDist_TramoBTA
<a id="puestotransdisttramobta"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | PuestoTransDist | TramoBTA |

### PuestoTransDist_TramoBTS
<a id="puestotransdisttramobts"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | PuestoTransDist | TramoBTS |

### PuestoTransDist_UnidadTransDist
<a id="puestotransdistunidadtransdist"></a>

**[`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) → [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOTRANSFDISTGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transformador Distribucion | Unidad Transformador Distribucion |

### PuestoTransPot_TramoSTA
<a id="puestotranspottramosta"></a>

**[`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) → [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transf Potencia | Tramo Subtransmision Aereo |

### PuestoTransPot_TramoSTS
<a id="puestotranspottramosts"></a>

**[`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) → [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) |
| Clave (join) | `CIRCUITSOURCEGUID ( Origin Primary Key )` | `PARENTCIRCUITSOURCEGUID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transf Potencia | Tramo Subtransmision Subterraneo |

### PuestoTransPot_UnidadTransPot
<a id="puestotranspotunidadtranspot"></a>

**[`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) → [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Forward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUESTOTRANSFPOTGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Puesto Transf Potencia | Unidad Transformador Potencia |

### PuntoCarga_ConexConsumidor
<a id="puntocargaconexconsumidor"></a>

**[`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) → [`CONEXIONCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#conexionconsumidor)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`CONEXIONCONSUMIDOR`](06_Clases_Consumidores_y_Alumbrado.md#conexionconsumidor) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUNTOCARGAGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Punto Carga | Conexion Consumidor |

### PuntoCarga_Generador
<a id="puntocargagenerador"></a>

**[`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) → [`Generador`](05_Clases_Generacion_Subestaciones_Fuentes.md#generador)** &nbsp;·&nbsp; Cardinalidad: **One To One** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`Generador`](05_Clases_Generacion_Subestaciones_Fuentes.md#generador) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUNTOCARGAGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Punto Carga | Generador |

### PuntoCarga_GeneradorDist
<a id="puntocargageneradordist"></a>

**[`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) → [`GeneradorDistribuido`](05_Clases_Generacion_Subestaciones_Fuentes.md#generadordistribuido)** &nbsp;·&nbsp; Cardinalidad: **One To One** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`GeneradorDistribuido`](05_Clases_Generacion_Subestaciones_Fuentes.md#generadordistribuido) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUNTOCARGAGLOBALID ( Origin Foreign Key )` |
| Etiqueta | PuntoCarga | Generador Distribuido |

### PuntoCarga_MotorInduccion
<a id="puntocargamotorinduccion"></a>

**[`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) → [`MOTORINDUCCION`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorinduccion)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`MOTORINDUCCION`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorinduccion) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUNTOCARGAGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Punto Carga | Motor Induccion |

### PuntoCarga_MotorSincrono
<a id="puntocargamotorsincrono"></a>

**[`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) → [`MOTORSINCRONO`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorsincrono)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | [`MOTORSINCRONO`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorsincrono) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `PUNTOCARGAGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Punto Carga | Motor Síncrono |

### Semaforo_ServicioCAlles
<a id="semaforoserviciocalles"></a>

**[`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) → [`SERVICIOCALLES`](03_Clases_Redes_y_Soporte.md#serviciocalles)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: Yes &nbsp;·&nbsp; Notificación: Backward &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | [`SERVICIOCALLES`](03_Clases_Redes_y_Soporte.md#serviciocalles) |
| Clave (join) | `GlobalID ( Origin Primary Key )` | `PUNTOSEMAFORIZACIONGUID ( Origin Foreign Key )` |
| Etiqueta | Semaforo | SERVICIO CALLES |

### Subestacion_PuestoTransfPot
<a id="subestacionpuestotransfpot"></a>

**[`Subestacion`](05_Clases_Generacion_Subestaciones_Fuentes.md#subestacion) → [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia)** &nbsp;·&nbsp; Cardinalidad: **One To Many** &nbsp;·&nbsp; Compuesta: No &nbsp;·&nbsp; Notificación: None &nbsp;·&nbsp; Atribuida: No &nbsp;·&nbsp; Reglas de subtipo: No

| | Origen | Destino |
|---|---|---|
| Clase | [`Subestacion`](05_Clases_Generacion_Subestaciones_Fuentes.md#subestacion) | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) |
| Clave (join) | `GLOBALID ( Origin Primary Key )` | `SUBESTACIONGLOBALID ( Origin Foreign Key )` |
| Etiqueta | Subestacion | Puesto Transf Potencia |
