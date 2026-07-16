from __future__ import annotations

import json
from typing import Any


def build_cockpit_bootstrap(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": payload.get("meta", {}).get("project", "ralphiia-quoteops"),
        "runtime_label": payload.get("runtime_label", "Codex-built / MCP runtime"),
        "integration_traces": payload.get("integration_traces", []),
    }


def render_cockpit_page(payload: dict[str, Any]) -> str:
    bootstrap = build_cockpit_bootstrap(payload)
    bootstrap_json = json.dumps(bootstrap, ensure_ascii=False).replace("</", "<\\/")
    template = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <title>QuoteOps · Proyectos y cotizaciones</title>
  <style>
    :root {
      --ink: #172320;
      --muted: #64716c;
      --paper: #f5f1e7;
      --paper-deep: #e8e1d2;
      --card: rgba(255, 253, 247, .92);
      --line: rgba(23, 35, 32, .14);
      --orange: #ed6a3a;
      --orange-deep: #b63f20;
      --teal: #157267;
      --teal-soft: #d8ece7;
      --gold: #f2c14e;
      --danger: #a73f34;
      --shadow: 0 22px 55px rgba(56, 48, 34, .12);
      --radius: 22px;
    }
    * { box-sizing: border-box; }
    html { background: var(--paper); }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Trebuchet MS", "Gill Sans", sans-serif;
      background:
        linear-gradient(90deg, rgba(23,35,32,.028) 1px, transparent 1px) 0 0 / 34px 34px,
        linear-gradient(rgba(23,35,32,.028) 1px, transparent 1px) 0 0 / 34px 34px,
        radial-gradient(circle at 12% 6%, rgba(242,193,78,.28), transparent 30%),
        radial-gradient(circle at 94% 12%, rgba(21,114,103,.18), transparent 34%),
        var(--paper);
    }
    button, input, textarea { font: inherit; }
    button { cursor: pointer; }
    .app { max-width: 1540px; margin: 0 auto; padding: 20px; }
    .topbar {
      display: flex; align-items: center; justify-content: space-between; gap: 18px;
      min-height: 70px; padding: 12px 18px; margin-bottom: 16px;
      border: 1px solid var(--line); border-radius: 20px; background: rgba(255,253,247,.78);
      backdrop-filter: blur(14px); box-shadow: 0 8px 30px rgba(56,48,34,.08);
    }
    .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .mark { width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; color: white; font-weight: 900; background: linear-gradient(145deg, var(--orange), var(--orange-deep)); box-shadow: 0 9px 24px rgba(182,63,32,.24); }
    .brand h1 { margin: 0; font: 700 23px/1 "Palatino Linotype", Georgia, serif; letter-spacing: -.02em; }
    .brand p { margin: 4px 0 0; color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .top-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; }
    .runtime { max-width: 240px; padding: 8px 11px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); background: white; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .lang { display: inline-flex; padding: 4px; border: 1px solid var(--line); border-radius: 999px; background: white; }
    .lang button { border: 0; background: transparent; color: var(--muted); padding: 7px 10px; border-radius: 999px; font-weight: 800; font-size: 12px; }
    .lang button.active { background: var(--ink); color: white; }
    .workspace { display: grid; grid-template-columns: minmax(0, 1.75fr) minmax(360px, .92fr); gap: 16px; height: calc(100vh - 126px); min-height: 680px; }
    .chat-shell, .side-shell { border: 1px solid var(--line); border-radius: var(--radius); background: var(--card); box-shadow: var(--shadow); overflow: hidden; }
    .chat-shell { display: grid; grid-template-rows: auto 1fr auto; min-width: 0; }
    .chat-head { padding: 21px 24px 17px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }
    .chat-head h2 { margin: 0; font: 700 clamp(25px,3vw,38px)/1.04 "Palatino Linotype", Georgia, serif; letter-spacing: -.035em; }
    .chat-head p { margin: 8px 0 0; max-width: 680px; color: var(--muted); line-height: 1.45; font-size: 14px; }
    .phase { flex: none; display: grid; gap: 5px; justify-items: end; }
    .phase span { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .12em; }
    .phase strong { font-size: 13px; color: var(--teal); }
    .messages { overflow-y: auto; padding: 22px 24px; display: flex; flex-direction: column; gap: 15px; scroll-behavior: smooth; }
    .message { max-width: min(82%, 760px); padding: 14px 16px; border-radius: 19px; line-height: 1.5; font-size: 14px; white-space: pre-wrap; animation: rise .24s ease both; }
    .message.assistant { align-self: flex-start; background: white; border: 1px solid var(--line); border-bottom-left-radius: 6px; }
    .message.user { align-self: flex-end; color: white; background: linear-gradient(140deg, var(--teal), #0d5149); border-bottom-right-radius: 6px; }
    .message small { display: block; opacity: .67; margin-bottom: 5px; font-size: 10px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; }
    .starter { align-self: flex-start; max-width: 700px; padding: 16px; border: 1px dashed rgba(237,106,58,.5); border-radius: 18px; background: rgba(237,106,58,.055); }
    .starter strong { display: block; margin-bottom: 7px; font-family: "Palatino Linotype", Georgia, serif; font-size: 18px; }
    .starter p { margin: 0 0 12px; color: var(--muted); font-size: 13px; line-height: 1.5; }
    .composer { padding: 14px 18px 18px; border-top: 1px solid var(--line); background: rgba(255,253,247,.96); }
    .selected-files { display: flex; gap: 7px; flex-wrap: wrap; min-height: 0; margin-bottom: 8px; }
    .file-chip { padding: 6px 9px; border-radius: 999px; background: var(--teal-soft); color: #0d5149; font-size: 11px; }
    .compose-row { display: grid; grid-template-columns: auto 1fr auto; align-items: end; gap: 10px; }
    textarea { width: 100%; min-height: 54px; max-height: 190px; resize: vertical; padding: 15px 16px; border: 1px solid var(--line); border-radius: 17px; background: white; color: var(--ink); outline: 0; line-height: 1.45; }
    textarea:focus, input:focus { border-color: rgba(21,114,103,.62); box-shadow: 0 0 0 3px rgba(21,114,103,.1); }
    .icon-btn, .send, .action { border: 0; border-radius: 15px; font-weight: 900; }
    .icon-btn { width: 52px; height: 52px; color: var(--teal); background: var(--teal-soft); font-size: 20px; }
    .send { min-width: 92px; height: 52px; padding: 0 18px; color: white; background: var(--orange); box-shadow: 0 8px 20px rgba(237,106,58,.25); }
    .send:disabled, .action:disabled { cursor: not-allowed; opacity: .45; }
    .compose-note { margin: 8px 4px 0; color: var(--muted); font-size: 10px; display: flex; justify-content: space-between; gap: 12px; }
    .side-shell { display: grid; grid-template-rows: auto 1fr; min-width: 0; }
    .tabs { display: grid; grid-template-columns: 1fr 1fr; padding: 7px; border-bottom: 1px solid var(--line); background: var(--paper-deep); }
    .tabs button { border: 0; border-radius: 13px; padding: 11px; color: var(--muted); background: transparent; font-weight: 900; }
    .tabs button.active { color: var(--ink); background: white; box-shadow: 0 4px 15px rgba(56,48,34,.09); }
    .side-content { overflow-y: auto; padding: 17px; }
    .tab-panel[hidden] { display: none; }
    .progress-block { margin-bottom: 14px; padding: 16px; color: white; border-radius: 18px; background: linear-gradient(145deg, var(--ink), #30443e); }
    .progress-row { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
    .progress-row strong { font: 700 20px/1 "Palatino Linotype", Georgia, serif; }
    .progress-row span { font-size: 12px; }
    .bar { height: 7px; margin-top: 12px; overflow: hidden; border-radius: 99px; background: rgba(255,255,255,.16); }
    .bar i { display: block; height: 100%; width: 10%; border-radius: inherit; background: linear-gradient(90deg, var(--gold), var(--orange)); transition: width .35s ease; }
    .identity { margin-bottom: 13px; padding: 15px; border: 1px solid rgba(21,114,103,.24); border-radius: 18px; background: rgba(216,236,231,.42); }
    .identity h3, .section h3 { margin: 0 0 8px; font: 700 17px/1.2 "Palatino Linotype", Georgia, serif; }
    .identity p { margin: 0 0 10px; color: var(--muted); font-size: 12px; line-height: 1.4; }
    .identity-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
    input { width: 100%; border: 1px solid var(--line); border-radius: 12px; padding: 11px 12px; background: white; color: var(--ink); outline: 0; }
    .action { padding: 11px 13px; color: white; background: var(--teal); }
    .status-text { min-height: 16px; margin-top: 8px; font-size: 11px; color: var(--muted); }
    .section { margin-bottom: 12px; padding: 14px; border: 1px solid var(--line); border-radius: 17px; background: white; }
    .section ul { margin: 0; padding-left: 18px; color: var(--muted); font-size: 12px; line-height: 1.55; }
    .empty { color: var(--muted); font-size: 12px; font-style: italic; }
    .option { padding: 10px; border-radius: 12px; background: var(--paper); margin-top: 7px; }
    .option strong { display: block; font-size: 12px; }
    .option span { color: var(--muted); font-size: 11px; line-height: 1.35; }
    .option-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 8px; }
    .option-meta button { border: 1px solid var(--line); border-radius: 999px; background: var(--ink); color: white; padding: 6px 9px; cursor: pointer; font: inherit; font-size: 10px; }
    .decision-intro { padding: 13px; border-radius: 16px; background: linear-gradient(135deg, var(--teal-soft), #fff8e8); border: 1px solid var(--line); color: var(--muted); font-size: 11px; line-height: 1.5; }
    .decision-card { margin-top: 12px; padding: 13px; border: 1px solid var(--line); border-radius: 17px; background: white; }
    .decision-card h3 { margin: 0 0 9px; font-size: 13px; }
    .decision-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
    .decision-field { display: grid; gap: 4px; margin-top: 7px; color: var(--muted); font-size: 10px; font-weight: 800; }
    .decision-field.full { grid-column: 1 / -1; }
    .decision-field input, .decision-field select, .decision-field textarea { width: 100%; padding: 8px; border: 1px solid var(--line); border-radius: 10px; background: var(--paper); color: var(--ink); font: inherit; font-size: 11px; resize: vertical; }
    .requirement-row, .alternative-line { display: grid; gap: 6px; padding: 9px; margin-top: 7px; border-radius: 12px; background: var(--paper); }
    .requirement-row { grid-template-columns: 92px 78px 85px 1fr auto; }
    .alternative-line { grid-template-columns: minmax(150px, 1fr) 58px 100px 110px; }
    .requirement-row input, .requirement-row select, .alternative-line input, .alternative-line select { width: 100%; min-width: 0; padding: 7px; border: 1px solid var(--line); border-radius: 9px; background: white; color: var(--ink); font: inherit; font-size: 10px; }
    .alternative-line .wide { grid-column: span 2; }
    .row-remove { width: 30px; border: 0; border-radius: 9px; background: #ffe9e5; color: var(--danger); cursor: pointer; font-weight: 900; }
    .decision-actions { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 10px; }
    .decision-actions button { font-size: 10px; }
    .decision-note { margin-top: 7px; color: var(--muted); font-size: 10px; line-height: 1.4; }
    .cost-proof { display: flex; justify-content: space-between; gap: 8px; padding-top: 9px; margin-top: 9px; border-top: 1px solid var(--line); font-size: 11px; font-weight: 900; }
    .quote-line { display: grid; grid-template-columns: 1fr 66px 100px; gap: 6px; margin: 7px 0; }
    .quote-line input { padding: 8px; font-size: 11px; }
    .quote-source { grid-column: 1 / -1; color: var(--muted); font-size: 10px; }
    .quote-totals { display: flex; justify-content: space-between; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); font-weight: 900; }
    .quote-actions { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 10px; }
    .quote-actions .action { font-size: 11px; }
    .quote-actions .secondary { color: var(--teal); background: var(--teal-soft); }
    .pdf-link { color: var(--orange-deep); font-size: 12px; font-weight: 900; }
    .trace-card { position: relative; padding: 14px 14px 14px 17px; margin-bottom: 10px; border: 1px solid var(--line); border-radius: 16px; background: white; }
    .trace-card::before { content: ""; position: absolute; left: 0; top: 12px; bottom: 12px; width: 4px; border-radius: 0 5px 5px 0; background: var(--gold); }
    .trace-card.ok::before, .trace-card.ready::before { background: var(--teal); }
    .trace-card.error::before { background: var(--danger); }
    .trace-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .trace-head strong { font-size: 13px; }
    .trace-head span { font-size: 10px; text-transform: uppercase; font-weight: 900; color: var(--teal); }
    .trace-card dl { display: grid; grid-template-columns: 58px 1fr; gap: 4px 8px; margin: 9px 0 0; font-size: 10px; line-height: 1.35; }
    .trace-card dt { color: var(--muted); }
    .trace-card dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
    .trace-note { padding: 12px; margin-bottom: 12px; color: var(--muted); background: var(--paper); border-radius: 14px; font-size: 11px; line-height: 1.45; }
    .toast { position: fixed; right: 24px; bottom: 24px; z-index: 5; max-width: 360px; padding: 13px 16px; color: white; background: var(--ink); border-radius: 14px; box-shadow: var(--shadow); transform: translateY(18px); opacity: 0; pointer-events: none; transition: .22s ease; }
    .toast.show { transform: translateY(0); opacity: 1; }
    @keyframes rise { from { opacity: 0; transform: translateY(7px); } }
    @media (max-width: 980px) {
      .app { padding: 10px; }
      .workspace { grid-template-columns: 1fr; height: auto; min-height: 0; }
      .chat-shell { min-height: calc(100vh - 104px); }
      .messages { min-height: 48vh; max-height: 58vh; }
      .side-shell { min-height: 620px; }
      .runtime { display: none; }
    }
    @media (max-width: 580px) {
      .topbar { min-height: 58px; padding: 9px 11px; }
      .mark { width: 36px; height: 36px; }
      .brand h1 { font-size: 19px; }
      .brand p { display: none; }
      .chat-head { padding: 17px; }
      .chat-head h2 { font-size: 27px; }
      .phase { display: none; }
      .messages { padding: 16px; }
      .message { max-width: 92%; }
      .composer { padding: 11px; }
      .compose-row { grid-template-columns: auto 1fr; }
      .send { grid-column: 1 / -1; width: 100%; }
      .compose-note span:last-child { display: none; }
      .quote-line { grid-template-columns: 1fr 58px 85px; }
      .requirement-row, .alternative-line { grid-template-columns: 1fr; }
      .alternative-line .wide { grid-column: auto; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <div class="mark">Q</div>
        <div><h1>QuoteOps</h1><p data-i18n="brandSub">Proyectos que avanzan conversando</p></div>
      </div>
      <div class="top-actions">
        <div class="runtime" id="runtimeLabel"></div>
        <div class="lang" aria-label="Language selector">
          <button id="langEs" data-lang="es">ES</button><button id="langEn" data-lang="en">EN</button>
        </div>
      </div>
    </header>

    <main class="workspace">
      <section class="chat-shell">
        <div class="chat-head">
          <div><h2 data-i18n="headline">Cuéntame qué necesitas construir.</h2><p data-i18n="subhead">Convirtamos una conversación, documentos y datos verificados en una cotización lista para aprobar.</p></div>
          <div class="phase"><span data-i18n="currentStage">Etapa actual</span><strong id="phaseLabel">Descubrimiento</strong></div>
        </div>
        <div class="messages" id="messages" aria-live="polite">
          <div class="message assistant"><small>QuoteOps</small><span data-i18n="welcome">Describe el proyecto con todo el detalle que tengas. Iré organizando el expediente y te preguntaré únicamente lo que falte.</span></div>
          <div class="starter" id="starter">
            <strong data-i18n="femarTitle">Empezar con el proyecto FEMAR</strong>
            <p data-i18n="femarDesc">Carga el caso de cambio o rehabilitación del control de acceso y continúa completándolo en conversación.</p>
            <button class="action" id="femarBtn" data-i18n="loadCase">Cargar caso</button>
          </div>
        </div>
        <div class="composer">
          <div class="selected-files" id="selectedFiles"></div>
          <div class="compose-row">
            <input id="fileInput" type="file" multiple hidden />
            <button class="icon-btn" id="attachBtn" aria-label="Attach files" title="Attach files">+</button>
            <textarea id="messageInput" maxlength="30000" data-i18n-placeholder="messagePlaceholder" placeholder="Escribe aquí el proyecto, responde preguntas o pide preparar la cotización..."></textarea>
            <button class="send" id="sendBtn" data-i18n="send">Enviar</button>
          </div>
          <div class="compose-note"><span id="composerHint" data-i18n="attachmentHint">Hasta 30.000 caracteres · 20 archivos · 25 MB por archivo</span><span data-i18n="enterHint">Ctrl/⌘ + Enter para enviar</span></div>
        </div>
      </section>

      <aside class="side-shell">
        <div class="tabs"><button class="active" data-tab="dossier" data-i18n="caseFile">Expediente</button><button data-tab="decision" data-i18n="decision">Decisión</button><button data-tab="traces" data-i18n="connections">Conexiones</button></div>
        <div class="side-content">
          <div class="tab-panel" id="dossierPanel">
            <div class="progress-block"><div class="progress-row"><strong data-i18n="projectProgress">Progreso del proyecto</strong><span id="progressValue">10%</span></div><div class="bar"><i id="progressBar"></i></div></div>
            <div class="identity">
              <h3 data-i18n="verifyCustomer">Validar cliente</h3>
              <p data-i18n="identityHelp">Cédula de 10 dígitos o RUC de 13. Intuito se consulta únicamente para RUC autorizado.</p>
              <div class="identity-row"><input id="identifierInput" inputmode="numeric" maxlength="13" data-i18n-placeholder="identifierPlaceholder" placeholder="Cédula o RUC" /><button class="action" id="lookupBtn" data-i18n="verify">Verificar</button></div>
              <div class="status-text" id="identityStatus"></div>
            </div>
            <div id="dossierSections"></div>
            <div id="quoteEditor"></div>
          </div>
          <div class="tab-panel" id="decisionPanel" hidden><div id="decisionWorkspace"></div></div>
          <div class="tab-panel" id="tracesPanel" hidden>
            <div class="trace-note" data-i18n="traceNote">Cada tarjeta muestra la fuente real, la llamada observada y un resultado saneado. Las credenciales y datos sensibles nunca aparecen aquí.</div>
            <div id="traceList"></div>
          </div>
        </div>
      </aside>
    </main>
  </div>
  <div class="toast" id="toast"></div>
  <script id="bootstrap-data" type="application/json">__BOOTSTRAP_JSON__</script>
  <script>
    const bootstrap = JSON.parse(document.getElementById('bootstrap-data').textContent);
    const I18N = {
      es: {
        brandSub:'Proyectos que avanzan conversando', headline:'Cuéntame qué necesitas construir.', subhead:'Convirtamos una conversación, documentos y datos verificados en una cotización lista para aprobar.', currentStage:'Etapa actual', welcome:'Describe el proyecto con todo el detalle que tengas. Iré organizando el expediente y te preguntaré únicamente lo que falte.', femarTitle:'Empezar con el proyecto FEMAR', femarDesc:'Carga el caso de cambio o rehabilitación del control de acceso y continúa completándolo en conversación.', loadCase:'Cargar caso', messagePlaceholder:'Escribe aquí el proyecto, responde preguntas o pide preparar la cotización...', send:'Enviar', attachmentHint:'Hasta 30.000 caracteres · 20 archivos · 25 MB por archivo', enterHint:'Ctrl/⌘ + Enter para enviar', caseFile:'Expediente', connections:'Conexiones', projectProgress:'Progreso del proyecto', verifyCustomer:'Validar cliente', identityHelp:'Cédula de 10 dígitos o RUC de 13. Intuito se consulta únicamente para RUC autorizado.', identifierPlaceholder:'Cédula o RUC', verify:'Verificar', traceNote:'Cada tarjeta muestra la fuente real, la llamada observada y un resultado saneado. Las credenciales y datos sensibles nunca aparecen aquí.', project:'Proyecto', customer:'Cliente', site:'Sitio', scope:'Alcance confirmado', assumptions:'Supuestos', risks:'Riesgos', questions:'Preguntas pendientes', options:'Paquetes', attachments:'Adjuntos', workItem:'Tarea activa', extractedEvidence:'Evidencia extraída', supplierOffers:'Costos de proveedor', selectPackage:'Cotizar este paquete', supplierCost:'Costo proveedor', evidencePending:'requiere revisión', noData:'Aún sin información', prepareQuote:'Preparar cotización', quote:'Cotización editable', description:'Descripción', qty:'Cant.', price:'Precio', total:'Total', savePrices:'Guardar valores', approve:'Aprobar y crear PDF', deliver:'Registrar entrega', approvedBy:'Aprobado por', openPdf:'Abrir PDF', phase_discovery:'Descubrimiento', phase_identity:'Cliente', phase_scope:'Alcance', phase_quote:'Cotización', phase_approval:'Aprobación', phase_delivery:'Entrega', status_ready:'Listo', status_ok:'Correcto', status_warning:'Atención', status_error:'Error', status_not_configured:'No configurado', status_pending:'Pendiente', status_locally_valid:'Validación local', status_verified:'Verificado', status_needs_review:'Requiere revisión', status_selected:'Seleccionado', status_stored:'Almacenado', status_needs_costs:'Faltan costos', status_needs_pricing:'Falta precio de venta', status_source_unlinked:'Fuente no archivada', status_confirmed:'Confirmado', status_rejected:'Rechazado', invalidIdentifier:'Ingresa una cédula válida de 10 dígitos o un RUC válido de 13.', validating:'Validando y reconciliando fuentes...', locallyValid:'Cédula válida localmente', verifiedRuc:'RUC verificado por Intuito', fileStored:'archivo(s) almacenado(s)', source:'Fuente', call:'Llamada', status:'Estado', latency:'Latencia', time:'Hora', result:'Resultado', error:'No se pudo completar la operación.', missionFirst:'Inicia el expediente con un mensaje antes de validar al cliente.', saving:'Guardando...', noInventedPrices:'Los valores empiezan en cero para no inventar precios.', femarPrompt:'Proyecto FEMAR: necesitamos cambiar o rehabilitar el sistema de control de acceso existente. Debemos evaluar qué equipos pueden conservarse, levantar los accesos y puertas, identificar riesgos de compatibilidad y preparar opciones técnicas antes de cotizar. Tengo documentación para adjuntar y seguiré completando los datos en esta conversación.'
      },
      en: {
        brandSub:'Projects that move forward through conversation', headline:'Tell me what you need to build.', subhead:'Let’s turn a conversation, documents, and verified data into an approval-ready quote.', currentStage:'Current stage', welcome:'Describe the project with all the detail you have. I will organize the case file and ask only for what is missing.', femarTitle:'Start with the FEMAR project', femarDesc:'Load the access-control replacement or rehabilitation case and keep completing it through conversation.', loadCase:'Load case', messagePlaceholder:'Describe the project, answer questions, or ask to prepare the quote...', send:'Send', attachmentHint:'Up to 30,000 characters · 20 files · 25 MB each', enterHint:'Ctrl/⌘ + Enter to send', caseFile:'Case file', connections:'Connections', projectProgress:'Project progress', verifyCustomer:'Validate customer', identityHelp:'10-digit national ID or 13-digit RUC. Intuito is called only for an authorized RUC.', identifierPlaceholder:'National ID or RUC', verify:'Validate', traceNote:'Each card shows the real source, observed call, and a sanitized result. Credentials and sensitive data never appear here.', project:'Project', customer:'Customer', site:'Site', scope:'Confirmed scope', assumptions:'Assumptions', risks:'Risks', questions:'Open questions', options:'Packages', attachments:'Attachments', workItem:'Active task', extractedEvidence:'Extracted evidence', supplierOffers:'Supplier costs', selectPackage:'Quote this package', supplierCost:'Supplier cost', evidencePending:'needs review', noData:'No information yet', prepareQuote:'Prepare quote', quote:'Editable quote', description:'Description', qty:'Qty.', price:'Price', total:'Total', savePrices:'Save values', approve:'Approve and create PDF', deliver:'Register delivery', approvedBy:'Approved by', openPdf:'Open PDF', phase_discovery:'Discovery', phase_identity:'Customer', phase_scope:'Scope', phase_quote:'Quote', phase_approval:'Approval', phase_delivery:'Delivery', status_ready:'Ready', status_ok:'OK', status_warning:'Warning', status_error:'Error', status_not_configured:'Not configured', status_pending:'Pending', status_locally_valid:'Locally valid', status_verified:'Verified', status_needs_review:'Needs review', status_selected:'Selected', status_stored:'Stored', status_needs_costs:'Needs costs', status_needs_pricing:'Needs selling prices', status_source_unlinked:'Source not archived', status_confirmed:'Confirmed', status_rejected:'Rejected', invalidIdentifier:'Enter a valid 10-digit national ID or 13-digit RUC.', validating:'Validating and reconciling sources...', locallyValid:'National ID validated locally', verifiedRuc:'RUC verified by Intuito', fileStored:'file(s) stored', source:'Source', call:'Call', status:'Status', latency:'Latency', time:'Time', result:'Result', error:'The operation could not be completed.', missionFirst:'Start the case file with a message before validating the customer.', saving:'Saving...', noInventedPrices:'Values start at zero so no price is invented.', femarPrompt:'FEMAR project: we need to replace or rehabilitate the existing access-control system. We must assess which equipment can be kept, survey access points and doors, identify compatibility risks, and prepare technical options before quoting. I have documents to attach and will keep completing the information in this conversation.'
      }
    };
    Object.assign(I18N.es, {
      catalogDrafts:'Productos o servicios por aprobar', status_draft:'Borrador pendiente',
      status_approved_staging:'Aprobado en staging', status_reference:'Referencia',
      status_attachment:'Adjunto', status_reference_and_attachment:'Referencia y adjunto',
      decision:'Decisión', decisionIntro:'Construye alternativas con requisitos confirmados, productos del expediente y evidencia real. QuoteOps calcula el costo desde la fuente y exige revisión humana.',
      technicalRequirements:'Requisitos técnicos', addRequirement:'Añadir requisito', saveRequirements:'Guardar requisitos',
      openDecisionQuestions:'Preguntas para decidir', questionsPlaceholder:'Una pregunta pendiente por línea',
      decisionAssistant:'Asistente para decidir', decisionAssistantNote:'Registra la elección del operador; no afirma el modelo que ejecuta QuoteOps.',
      requirementText:'Describe el requisito', configurationAlternatives:'Alternativas de configuración', alternative:'Alternativa',
      alternativeTitle:'Nombre de la alternativa', alternativeObjective:'Objetivo y criterio de diseño', addProduct:'Añadir producto',
      sourceProduct:'Producto con fuente', role:'Función', compatibility:'Compatibilidad', rationale:'Justificación',
      evidence:'Evidencia confirmada', saveAlternative:'Guardar alternativa', approveAlternative:'Aprobar alternativa', rejectAlternative:'Rechazar alternativa',
      reviewedBy:'Revisado por', noSupplierProducts:'Primero registra una oferta real en el expediente.', noConfirmedEvidence:'Sin evidencia confirmada',
      realCostOnly:'Costo resuelto desde ofertas reales', saved:'Cambios guardados',
      status_collecting_requirements:'Reuniendo requisitos', status_drafting_alternatives:'Preparando alternativas',
      status_needs_validation:'Necesita validación', status_ready_for_review:'Lista para revisión', status_approved:'Aprobada',
      status_incompatible:'Incompatible', category_legacy:'Sistema anterior', category_infrastructure:'Infraestructura',
      category_door:'Puerta', category_credential:'Credenciales', category_software:'Software', category_commercial:'Comercial', category_other:'Otro',
      priority_must:'Obligatorio', priority_should:'Recomendado', priority_could:'Opcional',
      requirement_confirmed:'Confirmado', requirement_assumption:'Supuesto', requirement_needs_validation:'Por validar',
      coverage:'Cobertura', gaps:'Brechas', phase_design:'Diseño técnico'
    });
    Object.assign(I18N.en, {
      catalogDrafts:'Products or services awaiting approval', status_draft:'Pending draft',
      status_approved_staging:'Approved in staging', status_reference:'Reference',
      status_attachment:'Attachment', status_reference_and_attachment:'Reference and attachment',
      decision:'Decision', decisionIntro:'Build alternatives from confirmed requirements, case products, and real evidence. QuoteOps resolves source costs and requires human review.',
      technicalRequirements:'Technical requirements', addRequirement:'Add requirement', saveRequirements:'Save requirements',
      openDecisionQuestions:'Decision questions', questionsPlaceholder:'One open question per line',
      decisionAssistant:'Decision assistant', decisionAssistantNote:'Records the operator choice; it does not claim which model runs QuoteOps.',
      requirementText:'Describe the requirement', configurationAlternatives:'Configuration alternatives', alternative:'Alternative',
      alternativeTitle:'Alternative name', alternativeObjective:'Objective and design criteria', addProduct:'Add product',
      sourceProduct:'Sourced product', role:'Role', compatibility:'Compatibility', rationale:'Rationale',
      evidence:'Confirmed evidence', saveAlternative:'Save alternative', approveAlternative:'Approve alternative', rejectAlternative:'Reject alternative',
      reviewedBy:'Reviewed by', noSupplierProducts:'Record a real supplier offer in the case first.', noConfirmedEvidence:'No confirmed evidence',
      realCostOnly:'Cost resolved from real offers', saved:'Changes saved',
      status_collecting_requirements:'Collecting requirements', status_drafting_alternatives:'Drafting alternatives',
      status_needs_validation:'Needs validation', status_ready_for_review:'Ready for review', status_approved:'Approved',
      status_incompatible:'Incompatible', category_legacy:'Legacy system', category_infrastructure:'Infrastructure',
      category_door:'Door', category_credential:'Credentials', category_software:'Software', category_commercial:'Commercial', category_other:'Other',
      priority_must:'Must have', priority_should:'Should have', priority_could:'Could have',
      requirement_confirmed:'Confirmed', requirement_assumption:'Assumption', requirement_needs_validation:'Needs validation',
      coverage:'Coverage', gaps:'Gaps', phase_design:'Technical design'
    });
    const WORK_STATUS = {
      es: {in_progress:'En curso', needs_input:'Faltan datos', ready_for_quote:'Listo para cotizar', awaiting_approval:'Pendiente de aprobación', ready_for_delivery:'Listo para entrega', completed:'Completado'},
      en: {in_progress:'In progress', needs_input:'Needs input', ready_for_quote:'Ready to quote', awaiting_approval:'Awaiting approval', ready_for_delivery:'Ready for delivery', completed:'Completed'}
    };
    let language = localStorage.getItem('quoteops.language') || 'es';
    let missionId = localStorage.getItem('quoteops.mission_id') || '';
    let dossier = null;
    let selectedFiles = [];
    let selectedAlternativeCode = 'A';
    const $ = (id) => document.getElementById(id);
    const t = (key) => I18N[language][key] || key;
    const statusText = (value) => I18N[language][`status_${value}`] || WORK_STATUS[language][value] || value;
    const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

    async function fetchJson(url, options = {}) {
      options.headers = {...(options.headers || {}), 'x-quoteops-language': language};
      const response = await fetch(url, options);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) { const error = new Error(payload?.detail?.message || payload?.detail || payload?.message || t('error')); error.payload = payload; throw error; }
      return payload;
    }
    function escapeHtml(value) { const el = document.createElement('span'); el.textContent = String(value ?? ''); return el.innerHTML; }
    function escapeAttr(value) { return escapeHtml(value).replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
    function showToast(message) { const el = $('toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2600); }
    function appendMessage(role, text) { const el = document.createElement('div'); el.className = `message ${role}`; const label = document.createElement('small'); label.textContent = role === 'assistant' ? 'QuoteOps' : (language === 'es' ? 'Tú' : 'You'); const body = document.createElement('span'); body.textContent = text; el.append(label, body); $('messages').appendChild(el); $('messages').scrollTop = $('messages').scrollHeight; }
    function applyLanguage() {
      document.documentElement.lang = language;
      localStorage.setItem('quoteops.language', language);
      document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
      document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
      document.querySelectorAll('.lang button').forEach((el) => el.classList.toggle('active', el.dataset.lang === language));
      if (dossier) renderDossier(dossier);
      if (missionId) loadMission();
      renderTraces(bootstrap.integration_traces || []);
    }
    function phaseText(phase) { return t(`phase_${phase || 'discovery'}`); }
    function values(section) { return Array.isArray(section) ? section : []; }
    function listSection(title, items) {
      const content = items.length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : `<div class="empty">${t('noData')}</div>`;
      return `<div class="section"><h3>${title}</h3>${content}</div>`;
    }
    function selectOptions(items, current, label) {
      return items.map((item) => `<option value="${escapeAttr(item)}" ${item === current ? 'selected' : ''}>${escapeHtml(label(item))}</option>`).join('');
    }
    function requirementRow(item = {}) {
      const categories = ['legacy','infrastructure','door','credential','software','commercial','other'];
      const priorities = ['must','should','could'];
      const statuses = ['confirmed','assumption','needs_validation'];
      return `<div class="requirement-row" data-requirement-id="${escapeAttr(item.requirement_id || '')}">
        <select class="req-category" aria-label="${t('technicalRequirements')}">${selectOptions(categories, item.category || 'other', (value) => t(`category_${value}`))}</select>
        <select class="req-priority" aria-label="Priority">${selectOptions(priorities, item.priority || 'must', (value) => t(`priority_${value}`))}</select>
        <select class="req-status" aria-label="Status">${selectOptions(statuses, item.status || 'confirmed', (value) => t(`requirement_${value}`))}</select>
        <input class="req-text" value="${escapeAttr(item.text || '')}" placeholder="${escapeAttr(t('requirementText'))}" />
        <button class="row-remove" type="button" aria-label="Remove">×</button>
      </div>`;
    }
    function supplierProducts() {
      return values(dossier?.supplier_offers).flatMap((offer) => values(offer.lines).map((line) => ({offer, line})));
    }
    function confirmedEvidence() { return values(dossier?.extracted_evidence).filter((item) => item.status === 'confirmed'); }
    function alternativeLineRow(item = {}) {
      const products = supplierProducts();
      const productOptions = products.length
        ? products.map(({offer, line}) => `<option value="${escapeAttr(line.line_id)}" ${line.line_id === item.source_offer_line_id ? 'selected' : ''}>${escapeHtml(`${line.sku || line.description} · ${offer.supplier_name} · USD ${Number(line.unit_cost || 0).toFixed(2)}`)}</option>`).join('')
        : `<option value="">${t('noSupplierProducts')}</option>`;
      const evidence = confirmedEvidence();
      const selectedEvidence = values(item.evidence_ids)[0] || '';
      const evidenceOptions = `<option value="">${t('noConfirmedEvidence')}</option>` + evidence.map((entry) => `<option value="${escapeAttr(entry.evidence_id)}" ${entry.evidence_id === selectedEvidence ? 'selected' : ''}>${escapeHtml(entry.source_file_name)} · ${escapeHtml(entry.evidence_id)}</option>`).join('');
      return `<div class="alternative-line">
        <select class="alt-source wide" aria-label="${t('sourceProduct')}">${productOptions}</select>
        <input class="alt-qty" type="number" min="0.01" step="0.01" value="${Number(item.quantity || 1)}" aria-label="${t('qty')}" />
        <input class="alt-role" value="${escapeAttr(item.role || 'equipment')}" placeholder="${escapeAttr(t('role'))}" />
        <select class="alt-compatibility" aria-label="${t('compatibility')}">${selectOptions(['needs_validation','verified','incompatible'], item.compatibility_status || 'needs_validation', statusText)}</select>
        <select class="alt-evidence wide" aria-label="${t('evidence')}">${evidenceOptions}</select>
        <input class="alt-rationale wide" value="${escapeAttr(item.rationale || '')}" placeholder="${escapeAttr(t('rationale'))}" />
        <button class="row-remove" type="button" aria-label="Remove">×</button>
      </div>`;
    }
    function splitLines(value) { return String(value || '').split(/\r?\n/).map((item) => item.trim()).filter(Boolean); }
    function renderDecisionWorkspace(workspace = {}) {
      const requirements = values(workspace.requirements);
      const alternatives = values(workspace.alternatives);
      const alternative = alternatives.find((item) => item.code === selectedAlternativeCode) || {};
      const updatedBy = localStorage.getItem('quoteops.updated_by') || 'Rafael';
      const lineRows = values(alternative.lines).length ? alternative.lines.map(alternativeLineRow).join('') : alternativeLineRow();
      $('decisionWorkspace').innerHTML = `
        <div class="decision-intro">${t('decisionIntro')}<div class="cost-proof"><span>${escapeHtml(statusText(workspace.status || 'collecting_requirements'))}</span><span>${escapeHtml(workspace.last_channel || 'web')}</span></div></div>
        <div class="decision-card"><h3>${t('technicalRequirements')}</h3><div id="decisionRequirementRows">${requirements.map(requirementRow).join('')}</div>
          <div class="decision-actions"><button class="action secondary" id="addRequirementBtn">${t('addRequirement')}</button></div>
          <label class="decision-field full">${t('openDecisionQuestions')}<textarea id="decisionQuestions" rows="3" placeholder="${escapeAttr(t('questionsPlaceholder'))}">${escapeHtml(values(workspace.open_questions).join('\n'))}</textarea></label>
          <label class="decision-field full">${t('decisionAssistant')}<input id="decisionModel" list="decisionModelChoices" value="${escapeAttr(workspace.selected_model || '')}" /></label>
          <datalist id="decisionModelChoices"><option value="ChatGPT / GPT-5.6 Sol operator session"></option><option value="Codex-built / MCP"></option><option value="Manual review"></option></datalist>
          <div class="decision-note">${t('decisionAssistantNote')}</div>
          <div class="decision-actions"><button class="action" id="saveRequirementsBtn">${t('saveRequirements')}</button></div>
        </div>
        <div class="decision-card"><h3>${t('configurationAlternatives')}</h3>
          <div class="decision-grid"><label class="decision-field">${t('alternative')}<select id="decisionAlternativeCode">${selectOptions(['A','B','C'], selectedAlternativeCode, (value) => value)}</select></label><label class="decision-field">${t('status')}<input value="${escapeAttr(statusText(alternative.status || 'draft'))}" disabled /></label>
          <label class="decision-field full">${t('alternativeTitle')}<input id="alternativeTitle" value="${escapeAttr(alternative.title || '')}" /></label>
          <label class="decision-field full">${t('alternativeObjective')}<textarea id="alternativeObjective" rows="2">${escapeHtml(alternative.objective || '')}</textarea></label></div>
          <div id="alternativeLines">${lineRows}</div>
          <div class="decision-actions"><button class="action secondary" id="addAlternativeLineBtn" ${supplierProducts().length ? '' : 'disabled'}>${t('addProduct')}</button></div>
          <div class="decision-grid">
            <label class="decision-field">${t('coverage')}<textarea id="alternativeCoverage" rows="2">${escapeHtml(values(alternative.coverage).join('\n'))}</textarea></label>
            <label class="decision-field">${t('gaps')}<textarea id="alternativeGaps" rows="2">${escapeHtml(values(alternative.gaps).join('\n'))}</textarea></label>
            <label class="decision-field">${t('assumptions')}<textarea id="alternativeAssumptions" rows="2">${escapeHtml(values(alternative.assumptions).join('\n'))}</textarea></label>
            <label class="decision-field">${t('risks')}<textarea id="alternativeRisks" rows="2">${escapeHtml(values(alternative.risks).join('\n'))}</textarea></label>
          </div>
          <div class="cost-proof"><span>${t('realCostOnly')}</span><span>USD ${Number(alternative.supplier_cost_total || 0).toFixed(2)}</span></div>
          <label class="decision-field">${t('reviewedBy')}<input id="decisionReviewedBy" value="${escapeAttr(updatedBy)}" /></label>
          <div class="decision-actions"><button class="action" id="saveAlternativeBtn">${t('saveAlternative')}</button><button class="action secondary" id="approveAlternativeBtn" ${alternative.status !== 'ready_for_review' ? 'disabled' : ''}>${t('approveAlternative')}</button><button class="action secondary" id="rejectAlternativeBtn" ${!alternative.code ? 'disabled' : ''}>${t('rejectAlternative')}</button></div>
        </div>`;
      document.querySelectorAll('#decisionWorkspace .row-remove').forEach((button) => button.addEventListener('click', () => button.parentElement.remove()));
      $('addRequirementBtn').addEventListener('click', () => { $('decisionRequirementRows').insertAdjacentHTML('beforeend', requirementRow()); bindDecisionRemoveButtons(); });
      $('addAlternativeLineBtn').addEventListener('click', () => { $('alternativeLines').insertAdjacentHTML('beforeend', alternativeLineRow()); bindDecisionRemoveButtons(); });
      $('decisionAlternativeCode').addEventListener('change', (event) => { selectedAlternativeCode = event.target.value; renderDecisionWorkspace(workspace); });
      $('saveRequirementsBtn').addEventListener('click', saveDecisionBrief);
      $('saveAlternativeBtn').addEventListener('click', saveConfigurationAlternative);
      $('approveAlternativeBtn').addEventListener('click', () => reviewConfigurationAlternative('approve'));
      $('rejectAlternativeBtn').addEventListener('click', () => reviewConfigurationAlternative('reject'));
    }
    function bindDecisionRemoveButtons() { document.querySelectorAll('#decisionWorkspace .row-remove').forEach((button) => { button.onclick = () => button.parentElement.remove(); }); }
    async function saveDecisionBrief() {
      if (!missionId) { showToast(t('missionFirst')); return; }
      const requirements = [...document.querySelectorAll('.requirement-row')].map((row) => ({requirement_id:row.dataset.requirementId || '', category:row.querySelector('.req-category').value, priority:row.querySelector('.req-priority').value, status:row.querySelector('.req-status').value, text:row.querySelector('.req-text').value.trim()})).filter((item) => item.text);
      const updatedBy = $('decisionReviewedBy')?.value.trim() || localStorage.getItem('quoteops.updated_by') || 'Rafael';
      localStorage.setItem('quoteops.updated_by', updatedBy);
      try {
        const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/decision-brief`, {method:'PUT', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, source_channel:'web', updated_by:updatedBy, requirements, open_questions:splitLines($('decisionQuestions').value), replace_requirements:true, replace_open_questions:true, selected_model:$('decisionModel').value.trim()})});
        renderMission(result); showToast(t('saved'));
      } catch (error) { showToast(error.message); }
    }
    async function saveConfigurationAlternative() {
      if (!missionId) { showToast(t('missionFirst')); return; }
      const lines = [...document.querySelectorAll('.alternative-line')].map((row) => ({offer_line_id:row.querySelector('.alt-source').value, quantity:Number(row.querySelector('.alt-qty').value), role:row.querySelector('.alt-role').value.trim(), compatibility_status:row.querySelector('.alt-compatibility').value, rationale:row.querySelector('.alt-rationale').value.trim(), evidence_ids:row.querySelector('.alt-evidence').value ? [row.querySelector('.alt-evidence').value] : []})).filter((item) => item.offer_line_id);
      if (!lines.length) { showToast(t('noSupplierProducts')); return; }
      const updatedBy = $('decisionReviewedBy').value.trim() || 'Rafael'; localStorage.setItem('quoteops.updated_by', updatedBy);
      const selectedModel = $('decisionModel').value.trim();
      try {
        const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/alternatives/${selectedAlternativeCode}`, {method:'PUT', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, source_channel:'web', code:selectedAlternativeCode, title:$('alternativeTitle').value.trim() || `${t('alternative')} ${selectedAlternativeCode}`, objective:$('alternativeObjective').value.trim(), lines, coverage:splitLines($('alternativeCoverage').value), gaps:splitLines($('alternativeGaps').value), assumptions:splitLines($('alternativeAssumptions').value), risks:splitLines($('alternativeRisks').value), generated_by:'web', selected_model:selectedModel, updated_by:updatedBy})});
        renderMission(result); showToast(t('saved'));
      } catch (error) { showToast(error.message); }
    }
    async function reviewConfigurationAlternative(decision) {
      const reviewedBy = $('decisionReviewedBy').value.trim() || 'Rafael'; localStorage.setItem('quoteops.updated_by', reviewedBy);
      try {
        const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/alternatives/${selectedAlternativeCode}/review`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, decision, reviewed_by:reviewedBy, notes:''})});
        renderMission(result); showToast(t('saved'));
      } catch (error) { showToast(error.message); }
    }
    function renderDossier(data) {
      dossier = data;
      const project = data.project || {};
      const customer = data.customer || {};
      const site = data.site || {};
      $('progressValue').textContent = `${data.progress || 0}%`;
      $('progressBar').style.width = `${data.progress || 0}%`;
      const customerItems = [customer.name, customer.identifier, customer.verification_status && customer.verification_status !== 'pending' ? statusText(customer.verification_status) : '', customer.source].filter(Boolean);
      const siteItems = [site.location, site.access_points ? `${site.access_points} ${language === 'es' ? 'accesos' : 'access points'}` : '', ...(site.operating_constraints || [])].filter(Boolean);
      const attachmentItems = values(data.attachments).map((item) => `${item.name} · ${item.status === 'stored' ? statusText('stored') + ' · SHA-256 ' + item.sha256.slice(0,8) : statusText(item.status)}`);
      const factLabels = language === 'es'
        ? {archive_volume:'Volumen del archivo', current_server:'Servidor actual', delivery_workflow:'Entrega actual', billing_workflow:'Cobros actuales', local_ai_goal:'Objetivo de IA local', budget_and_schedule:'Presupuesto y fecha'}
        : {archive_volume:'Archive volume', current_server:'Current server', delivery_workflow:'Current delivery', billing_workflow:'Current billing', local_ai_goal:'Local AI goal', budget_and_schedule:'Budget and schedule'};
      const projectItems = [project.title, project.summary, ...Object.entries(project.facts || {}).map(([key, value]) => `${factLabels[key] || key}: ${value}`)].filter(Boolean);
      const workItem = data.work_item ? [data.work_item.title, `${data.work_item.task_id} · ${statusText(data.work_item.status)}`, data.work_item.next_action] : [];
      const evidenceItems = values(data.extracted_evidence).map((item) => `${item.source_file_name} · ${item.extraction_type} · ${statusText(item.status)} · ${(item.products || []).length} ${language === 'es' ? 'producto(s)' : 'product(s)'} · ${(item.supplier_prices || []).length} ${language === 'es' ? 'precio(s)' : 'price(s)'}`);
      const supplierItems = values(data.supplier_offers).map((item) => `${item.supplier_name} · ${item.supplier_reference} · USD ${Number(item.total_cost || 0).toFixed(2)} · ${statusText(item.evidence_status)}`);
      const catalogItems = values(data.catalog_drafts).map((item) => `${item.sku ? item.sku + ' · ' : ''}${item.name} · ${statusText(item.status)}${item.canonical_item_id ? ' · ' + item.canonical_item_id : ''}`);
      let html = '';
      html += listSection(t('workItem'), workItem);
      html += listSection(t('project'), projectItems);
      html += listSection(t('customer'), customerItems);
      html += listSection(t('site'), siteItems);
      html += listSection(t('scope'), values(data.confirmed_scope));
      html += listSection(t('assumptions'), values(data.assumptions));
      html += listSection(t('risks'), values(data.risks));
      html += listSection(t('questions'), values(data.questions));
      html += listSection(t('extractedEvidence'), evidenceItems);
      html += listSection(t('supplierOffers'), supplierItems);
      html += listSection(t('catalogDrafts'), catalogItems);
      if (values(data.options).length) html += `<div class="section"><h3>${t('options')}</h3>${data.options.map((item) => `<div class="option"><strong>${escapeHtml(item.code)} · ${escapeHtml(item.title)}</strong><span>${escapeHtml(item.summary)}</span><div class="option-meta"><span>${escapeHtml(statusText(item.status))} · ${t('supplierCost')} USD ${Number(item.supplier_cost_total || 0).toFixed(2)}</span><button data-option-code="${escapeHtml(item.code)}" ${['needs_validation','ready_for_review'].includes(item.status) ? 'disabled' : ''}>${t('selectPackage')}</button></div></div>`).join('')}</div>`;
      html += listSection(t('attachments'), attachmentItems);
      if (!data.quote && values(data.confirmed_scope).length) html += `<button class="action" id="prepareQuoteBtn">${t('prepareQuote')}</button>`;
      $('dossierSections').innerHTML = html;
      document.querySelectorAll('[data-option-code]').forEach((button) => button.addEventListener('click', () => selectPackage(button.dataset.optionCode)));
      $('prepareQuoteBtn')?.addEventListener('click', () => sendMessage(language === 'es' ? 'Preparar cotización editable' : 'Prepare the editable quote'));
      renderDecisionWorkspace(data.decision_workspace || {});
      renderQuote(data.quote);
    }
    function renderQuote(quote) {
      if (!quote) { $('quoteEditor').innerHTML = ''; return; }
      const lines = (quote.lines || []).map((line) => `<div class="quote-line" data-line-id="${escapeHtml(line.line_id)}"><input class="line-desc" value="${escapeHtml(line.description)}" aria-label="${t('description')}" /><input class="line-qty" type="number" min="0.01" step="0.01" value="${line.quantity}" aria-label="${t('qty')}" /><input class="line-price" type="number" min="0" step="0.01" value="${line.unit_price}" aria-label="${t('price')}" />${Number(line.unit_cost || 0) > 0 ? `<span class="quote-source">${t('supplierCost')}: USD ${Number(line.unit_cost).toFixed(2)} · ${escapeHtml(line.sku || line.supplier_offer_id || '')}</span>` : ''}</div>`).join('');
      const approvedBy = localStorage.getItem('quoteops.approved_by') || 'Rafael';
      $('quoteEditor').innerHTML = `<div class="section"><h3>${t('quote')}${quote.selected_option_code ? ` · ${escapeHtml(quote.selected_option_code)}` : ''}</h3><div class="empty">${t('noInventedPrices')}</div>${lines}<div class="quote-totals"><span>${t('total')}</span><span>USD ${Number(quote.total || 0).toFixed(2)}</span></div><input id="approvedByInput" value="${escapeHtml(approvedBy)}" placeholder="${t('approvedBy')}" style="margin-top:10px" /><div class="quote-actions"><button class="action secondary" id="saveQuoteBtn">${t('savePrices')}</button><button class="action" id="approveQuoteBtn" ${quote.status !== 'draft' ? 'disabled' : ''}>${t('approve')}</button><button class="action" id="deliverQuoteBtn" ${quote.status !== 'approved' ? 'disabled' : ''}>${t('deliver')}</button></div>${quote.pdf_url ? `<p><a class="pdf-link" target="_blank" rel="noopener" href="${escapeHtml(quote.pdf_url)}">${t('openPdf')}</a></p>` : ''}</div>`;
      $('saveQuoteBtn').addEventListener('click', saveQuote);
      $('approveQuoteBtn').addEventListener('click', approveQuote);
      $('deliverQuoteBtn').addEventListener('click', deliverQuote);
    }
    async function sendMessage(forcedText = '') {
      const text = forcedText || $('messageInput').value.trim();
      if (!text && !selectedFiles.length) return;
      $('sendBtn').disabled = true;
      if (text) appendMessage('user', text);
      const files = [...selectedFiles];
      try {
        let result = await fetchJson('/api/conversation/messages', { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({ mission_id:missionId, idempotency_key:newKey(), language, message:text, attachments:files.map((file) => ({name:file.name, media_type:file.type || 'application/octet-stream', size_bytes:file.size})) }) });
        missionId = result.mission_id; localStorage.setItem('quoteops.mission_id', missionId); $('starter')?.remove();
        let stored = 0;
        for (const file of files) {
          const form = new FormData(); form.append('file', file); form.append('language', language);
          result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/attachments`, {method:'POST', body:form}); stored += 1;
        }
        if (stored) showToast(`${stored} ${t('fileStored')}`);
        appendMessage('assistant', result.assistant_message); renderMission(result); $('messageInput').value = ''; selectedFiles = []; renderSelectedFiles();
      } catch (error) { showToast(error.message); }
      finally { $('sendBtn').disabled = false; }
    }
    function renderHistory(history) { if (!history?.length) return; $('messages').innerHTML = ''; history.forEach((item) => appendMessage(item.role, item.text)); }
    function renderMission(result) { dossier = result.dossier; $('phaseLabel').textContent = phaseText(result.phase); $('runtimeLabel').textContent = result.runtime_label || bootstrap.runtime_label; renderHistory(result.history); renderDossier(result.dossier); }
    async function loadMission() { try { const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}?language=${language}`); renderMission(result); } catch { localStorage.removeItem('quoteops.mission_id'); missionId = ''; } }
    function renderSelectedFiles() { $('selectedFiles').innerHTML = selectedFiles.map((file) => `<span class="file-chip">${escapeHtml(file.name)} · ${(file.size/1024).toFixed(0)} KB</span>`).join(''); }
    async function lookupCustomer() {
      if (!missionId) { showToast(t('missionFirst')); return; }
      const identifier = $('identifierInput').value.replace(/\D/g,'');
      if (![10,13].includes(identifier.length)) { $('identityStatus').textContent = t('invalidIdentifier'); return; }
      $('identityStatus').textContent = t('validating'); $('lookupBtn').disabled = true;
      try {
        const result = await fetchJson('/api/customer/lookup', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({identifier, mission_id:missionId, language, force_refresh:false})});
        $('identityStatus').textContent = result.provider_called ? t('verifiedRuc') : t('locallyValid'); await loadMission(); await refreshTraces();
      } catch (error) { $('identityStatus').textContent = error.message; }
      finally { $('lookupBtn').disabled = false; }
    }
    function quoteLines() { return [...document.querySelectorAll('.quote-line')].map((row) => ({line_id:row.dataset.lineId, description:row.querySelector('.line-desc').value, quantity:Number(row.querySelector('.line-qty').value), unit_price:Number(row.querySelector('.line-price').value)})); }
    async function selectPackage(optionCode) { try { const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/packages/select`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, option_code:optionCode})}); renderMission(result); } catch(error) { showToast(error.message); } }
    async function saveQuote() { try { const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/quote`, {method:'PUT', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, lines:quoteLines(), tax_rate:0})}); renderMission(result); showToast(t('savePrices')); } catch(error) { showToast(error.message); } }
    async function approveQuote() { const approvedBy = $('approvedByInput').value.trim(); localStorage.setItem('quoteops.approved_by', approvedBy); try { const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/approve`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, approved_by:approvedBy, access_mode:'judge'})}); appendMessage('assistant', result.assistant_message); renderMission(result); await refreshTraces(); } catch(error) { showToast(error.message); } }
    async function deliverQuote() { try { const result = await fetchJson(`/api/conversation/missions/${encodeURIComponent(missionId)}/deliver`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({idempotency_key:newKey(), language, channels:['download'], access_mode:'judge'})}); appendMessage('assistant', result.assistant_message); renderMission(result); } catch(error) { showToast(error.message); } }
    function renderTraces(items) {
      $('traceList').innerHTML = (items || []).map((item) => `<div class="trace-card ${escapeHtml(item.status)}"><div class="trace-head"><strong>${escapeHtml(item.integration)}</strong><span>${escapeHtml(statusText(item.status))}</span></div><dl><dt>${t('source')}</dt><dd>${escapeHtml(item.source)}</dd><dt>${t('call')}</dt><dd>${escapeHtml(item.call)}</dd><dt>${t('latency')}</dt><dd>${Number(item.latency_ms || 0).toFixed(1)} ms</dd><dt>${t('time')}</dt><dd>${escapeHtml(new Date(item.observed_at).toLocaleTimeString(language))}</dd><dt>${t('result')}</dt><dd>${escapeHtml(item.result)}</dd></dl></div>`).join('');
    }
    async function refreshTraces() { try { const data = await fetchJson('/api/integrations/trace'); $('runtimeLabel').textContent = data.runtime_label; renderTraces(data.items); } catch {} }
    document.querySelectorAll('.lang button').forEach((button) => button.addEventListener('click', () => { language = button.dataset.lang; applyLanguage(); }));
    document.querySelectorAll('.tabs button').forEach((button) => button.addEventListener('click', () => { document.querySelectorAll('.tabs button').forEach((item) => item.classList.toggle('active', item === button)); $('dossierPanel').hidden = button.dataset.tab !== 'dossier'; $('decisionPanel').hidden = button.dataset.tab !== 'decision'; $('tracesPanel').hidden = button.dataset.tab !== 'traces'; if (button.dataset.tab === 'traces') refreshTraces(); }));
    $('attachBtn').addEventListener('click', () => $('fileInput').click());
    $('fileInput').addEventListener('change', (event) => { selectedFiles = [...event.target.files].slice(0,20); renderSelectedFiles(); });
    $('sendBtn').addEventListener('click', () => sendMessage());
    $('messageInput').addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') sendMessage(); });
    $('femarBtn').addEventListener('click', () => { $('messageInput').value = t('femarPrompt'); $('messageInput').focus(); });
    $('lookupBtn').addEventListener('click', lookupCustomer);
    $('identifierInput').addEventListener('input', (event) => { event.target.value = event.target.value.replace(/\D/g,'').slice(0,13); });
    $('runtimeLabel').textContent = bootstrap.runtime_label;
    renderTraces(bootstrap.integration_traces || []);
    applyLanguage();
    if (missionId) loadMission();
    setInterval(refreshTraces, 10000);
  </script>
</body>
</html>"""
    return template.replace("__BOOTSTRAP_JSON__", bootstrap_json)
