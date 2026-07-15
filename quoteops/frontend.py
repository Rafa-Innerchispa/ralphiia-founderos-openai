from __future__ import annotations

import html
import json
from typing import Any


def build_cockpit_bootstrap(payload: dict[str, Any]) -> dict[str, Any]:
    reuse = payload.get("reuse", {})
    results = payload.get("reuse_verify", {}).get("results", [])
    return {
        "project": payload.get("meta", {}).get("project", "ralphiia-quoteops"),
        "task_id": payload.get("meta", {}).get("task_id", "ops_202172a3b4c8"),
        "correlation_id": payload.get("meta", {}).get("correlation_id", "openai-build-week-quoteops-20260714"),
        "reuse_count": reuse.get("reuse_count", 0),
        "new_count": reuse.get("new_count", 0),
        "stack_ok": payload.get("reuse_verify", {}).get("ok", False),
        "stack_results": results,
    }


def render_cockpit_page(payload: dict[str, Any]) -> str:
    bootstrap = build_cockpit_bootstrap(payload)
    bootstrap_json = json.dumps(bootstrap, ensure_ascii=False).replace("</", "<\\/")
    meta_json = html.escape(json.dumps(payload.get("meta", {}), ensure_ascii=False))
    template = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QuoteOps Cockpit</title>
  <style>
    :root {
      --bg: #07111f;
      --panel: rgba(10, 20, 35, 0.78);
      --line: rgba(151, 171, 198, 0.18);
      --text: #edf4ff;
      --muted: #98abc4;
      --accent: #f7b955;
      --accent-2: #6ee7b7;
      --danger: #ff8a6b;
      --shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
      --radius: 24px;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background:
      radial-gradient(circle at top left, rgba(247, 185, 85, 0.18), transparent 24%),
      radial-gradient(circle at top right, rgba(110, 231, 183, 0.14), transparent 28%),
      linear-gradient(180deg, #091321 0%, #050b14 100%); color: var(--text); min-height: 100vh; }
    .wrap { max-width: 1440px; margin: 0 auto; padding: 28px; }
    .hero { display: grid; grid-template-columns: 1.3fr 0.9fr; gap: 18px; margin-bottom: 18px; }
    .brand, .panel, .stat { border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
    .brand { padding: 30px; background: linear-gradient(135deg, rgba(16, 34, 56, 0.92), rgba(8, 15, 26, 0.94)); position: relative; overflow: hidden; }
    .brand::after { content: ''; position: absolute; inset: auto -120px -140px auto; width: 320px; height: 320px; background: radial-gradient(circle, rgba(247, 185, 85, 0.25), transparent 60%); pointer-events: none; }
    .eyebrow { display: inline-flex; gap: 10px; align-items: center; padding: 8px 12px; border: 1px solid rgba(247, 185, 85, 0.35); border-radius: 999px; color: var(--accent); background: rgba(247, 185, 85, 0.08); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
    h1 { margin: 16px 0 10px; font-size: clamp(32px, 5vw, 58px); line-height: 0.95; letter-spacing: -0.04em; }
    .lede { max-width: 72ch; color: var(--muted); font-size: 16px; line-height: 1.6; margin: 0; }
    .stats { display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .stat { padding: 18px; background: rgba(7, 17, 31, 0.65); }
    .stat-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em; }
    .stat-value { font-size: 30px; font-weight: 700; margin-top: 10px; }
    .grid { display: grid; grid-template-columns: 1.15fr 0.95fr 0.9fr; gap: 18px; align-items: start; }
    .panel { background: var(--panel); backdrop-filter: blur(16px); padding: 22px; }
    .panel h2 { margin: 0 0 8px; font-size: 20px; letter-spacing: -0.02em; }
    .panel p.sub { margin: 0 0 16px; color: var(--muted); line-height: 1.6; }
    .field { display: grid; gap: 8px; margin-bottom: 12px; }
    .field label { color: #d8e5f7; font-size: 13px; }
    input, select, textarea { width: 100%; border: 1px solid rgba(151, 171, 198, 0.24); border-radius: 16px; padding: 14px; background: rgba(3, 8, 16, 0.72); color: var(--text); outline: none; font: inherit; }
    textarea { min-height: 132px; resize: vertical; }
    input:focus, select:focus, textarea:focus { border-color: rgba(247, 185, 85, 0.65); box-shadow: 0 0 0 3px rgba(247, 185, 85, 0.12); }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .btn-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 14px; }
    button { border: 0; border-radius: 999px; padding: 13px 18px; font-weight: 700; cursor: pointer; transition: transform .15s ease, opacity .15s ease; }
    button:hover { transform: translateY(-1px); }
    .primary { background: linear-gradient(135deg, var(--accent), #ffcf76); color: #1c1205; }
    .secondary { background: rgba(110, 231, 183, 0.14); color: var(--accent-2); border: 1px solid rgba(110, 231, 183, 0.28); }
    .ghost { background: transparent; color: var(--text); border: 1px solid rgba(151, 171, 198, 0.22); }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; }
    .chip { padding: 7px 10px; border-radius: 999px; background: rgba(255,255,255,0.06); color: #e7eef9; font-size: 12px; border: 1px solid rgba(255,255,255,0.08); }
    .list { display: grid; gap: 12px; }
    .card { padding: 16px; border-radius: 18px; background: rgba(3, 8, 16, 0.52); border: 1px solid rgba(151, 171, 198, 0.16); }
    .card h3 { margin: 0 0 6px; font-size: 16px; }
    .small { color: var(--muted); font-size: 13px; line-height: 1.5; }
    pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; line-height: 1.5; }
    .timeline { display: grid; gap: 10px; }
    .step { display: flex; justify-content: space-between; gap: 16px; align-items: center; padding: 12px 14px; border-radius: 16px; background: rgba(3, 8, 16, 0.54); border: 1px solid rgba(151, 171, 198, 0.14); }
    .step.active { border-color: rgba(247, 185, 85, 0.42); background: rgba(247, 185, 85, 0.08); }
    .step.done { border-color: rgba(110, 231, 183, 0.32); }
    .badge { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    .status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--danger); box-shadow: 0 0 0 4px rgba(255, 138, 107, 0.12); }
    .status-dot.ok { background: var(--accent-2); box-shadow: 0 0 0 4px rgba(110, 231, 183, 0.12); }
    .status-dot.wait { background: var(--accent); box-shadow: 0 0 0 4px rgba(247, 185, 85, 0.12); }
    .foot { margin-top: 18px; color: var(--muted); font-size: 12px; display: flex; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
    .jsonbox { max-height: 280px; overflow: auto; }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }
    .ruc-grid { display: grid; grid-template-columns: .75fr 1.25fr; gap: 18px; margin-top: 18px; }
    .signal { display: grid; gap: 5px; padding: 13px; border: 1px solid var(--line); border-radius: 16px; background: rgba(3, 8, 16, .5); }
    .signal strong { font-size: 15px; }
    .signal span { color: var(--muted); font-size: 12px; }
    .verified { color: var(--accent-2); }
    .accent-line { width: 66px; height: 4px; border-radius: 999px; background: linear-gradient(90deg, var(--accent), var(--accent-2)); margin: 18px 0; }
    @media (max-width: 1180px) { .hero, .grid, .grid2, .ruc-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="brand">
        <span class="eyebrow">QuoteOps Cockpit</span>
        <h1>Del mensaje bruto a la cotización verificable.</h1>
        <div class="accent-line"></div>
        <p class="lede">Una experiencia operativa creada para mostrar reutilización real del stack RalphiIA, análisis estructurado con GPT-5.6 cuando esté habilitado, y trazabilidad de todo el flujo desde intake hasta delivery.</p>
        <div class="chips" style="margin-top:18px;">
          <span class="chip">repo nuevo</span>
          <span class="chip">structured outputs</span>
          <span class="chip">reuse-first</span>
          <span class="chip">sandbox safe</span>
          <span class="chip">verificable</span>
        </div>
      </div>
      <div class="stats">
        <div class="stat"><div class="stat-label">Reuse count</div><div class="stat-value" id="reuseCount">__REUSE_COUNT__</div></div>
        <div class="stat"><div class="stat-label">New components</div><div class="stat-value" id="newCount">__NEW_COUNT__</div></div>
        <div class="stat"><div class="stat-label">Stack status</div><div class="stat-value" id="stackStatus">__STACK_STATUS__</div></div>
        <div class="stat"><div class="stat-label">Task ID</div><div class="stat-value" style="font-size:18px;">__TASK_ID__</div></div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Intake Composer</h2>
        <p class="sub">Captura un request, valida lo mínimo y manda el análisis al motor estructurado.</p>
        <div class="row">
          <div class="field"><label for="source_channel">Source channel</label><select id="source_channel"><option value="sandbox">sandbox</option><option value="whatsapp">whatsapp</option><option value="web">web</option></select></div>
          <div class="field"><label for="customer_name">Customer name</label><input id="customer_name" value="Ana" placeholder="Cliente" /></div>
        </div>
        <div class="row">
          <div class="field"><label for="contact">Contact</label><input id="contact" value="ana@example.com" placeholder="Email o teléfono" /></div>
          <div class="field"><label for="attachments">Attachments</label><input id="attachments" value="brief.pdf,chat.png" placeholder="archivos separados por coma" /></div>
        </div>
        <div class="field"><label for="original_text">Original text</label><textarea id="original_text">Necesito una cotización para automatizar WhatsApp, PDFs y seguimiento de entrega.</textarea></div>
        <div class="btn-row">
          <button class="primary" id="analyzeBtn">Analyze intake</button>
          <button class="secondary" id="previewBtn">Preview fallback</button>
          <button class="ghost" id="verifyBtn">Verify stack</button>
        </div>
        <div class="foot"><span id="analysisHint">Ready for structured analysis.</span><span>H2 live</span></div>
      </div>

      <div class="panel">
        <h2>Analysis Output</h2>
        <p class="sub">Structured data returned by the backend, shown as the judge will see it.</p>
        <div class="chips" id="analysisChips"></div>
        <div class="card" style="margin-top:14px;">
          <h3>Result</h3>
          <div class="jsonbox"><pre id="analysisJson">Waiting for analysis...</pre></div>
        </div>
      </div>

      <div class="panel">
        <h2>Delivery Timeline</h2>
        <p class="sub">A compact state machine that makes the flow understandable at a glance.</p>
        <div class="timeline" id="timeline"></div>
      </div>
    </section>

    <section class="ruc-grid">
      <div class="panel">
        <span class="eyebrow">Trust anchor · Owner mode</span>
        <h2 style="margin-top:16px;">Verificar empresa por RUC</h2>
        <p class="sub">Intuito confirma la identidad; RalphiIA y Contífico aportan contexto. Nada se modifica sin aprobación.</p>
        <div class="field"><label for="rucInput">RUC ecuatoriano</label><input id="rucInput" value="0992364866001" inputmode="numeric" maxlength="13" /></div>
        <div class="btn-row">
          <button class="primary" id="rucLookupBtn">Consultar y comparar</button>
          <button class="ghost" id="rucNewBtn">Probar RUC nuevo</button>
          <button class="secondary" id="rucRefreshBtn">Refrescar fuente</button>
        </div>
        <div class="card" style="margin-top:16px;">
          <div class="field"><label for="approvedBy">Aprobado por</label><input id="approvedBy" value="Rafael" /></div>
          <button class="secondary" id="rucConfirmBtn" disabled>Confirmar creación / actualización</button>
          <div class="small" id="rucConfirmHint" style="margin-top:10px;">Primero consulta y revisa la evidencia.</div>
        </div>
      </div>
      <div class="panel">
        <h2>Identity Reconciliation</h2>
        <p class="sub">Datos oficiales, coincidencias internas, conflictos y borrador propuesto en una sola vista.</p>
        <div class="chips" id="rucChips"><span class="chip">waiting for verification</span></div>
        <div class="list" id="rucSignals" style="margin-top:14px;"></div>
        <div class="card" style="margin-top:14px;"><pre id="rucJson">Introduce un RUC para iniciar.</pre></div>
      </div>
    </section>

    <section class="grid2">
      <div class="panel">
        <h2>Reuse Map</h2>
        <p class="sub">What we reuse from the RalphiIA platform and what is genuinely new in QuoteOps.</p>
        <div class="list" id="reuseList"></div>
      </div>
      <div class="panel">
        <h2>Trace Panel</h2>
        <p class="sub">Observed health, verification results, and the control-plane facts the build week cares about.</p>
        <div class="list" id="traceList"></div>
      </div>
    </section>

    <div class="foot">
      <span>Project: __PROJECT__</span>
      <span>Correlation: __CORRELATION_ID__</span>
      <span>Meta: __META_JSON__</span>
    </div>
  </div>

  <script id="bootstrap-data" type="application/json">__BOOTSTRAP_JSON__</script>
  <script>
    const bootstrap = JSON.parse(document.getElementById('bootstrap-data').textContent);
    const reuseList = document.getElementById('reuseList');
    const traceList = document.getElementById('traceList');
    const analysisJson = document.getElementById('analysisJson');
    const analysisChips = document.getElementById('analysisChips');
    const analysisHint = document.getElementById('analysisHint');
    const timeline = document.getElementById('timeline');
    const rucJson = document.getElementById('rucJson');
    const rucSignals = document.getElementById('rucSignals');
    const rucChips = document.getElementById('rucChips');
    const rucConfirmBtn = document.getElementById('rucConfirmBtn');
    const rucConfirmHint = document.getElementById('rucConfirmHint');
    let currentVerification = null;

    const phases = ['intake', 'analysis', 'draft', 'review', 'delivery', 'done'];
    const phaseLabels = { intake: 'Intake', analysis: 'Analysis', draft: 'Draft', review: 'Review', delivery: 'Delivery', done: 'Done' };

    function renderTimeline(active = 'analysis') {
      timeline.innerHTML = '';
      phases.forEach((phase) => {
        const el = document.createElement('div');
        el.className = 'step' + (phase === active ? ' active' : '') + (phases.indexOf(phase) < phases.indexOf(active) ? ' done' : '');
        el.innerHTML = `<div><div style="font-weight:700;">${phaseLabels[phase]}</div><div class="small">${phase === 'analysis' ? 'Structured output and risk review' : 'Operational state'}</div></div><div class="status-dot ${phase === active ? 'wait' : (phases.indexOf(phase) < phases.indexOf(active) ? 'ok' : '')}"></div>`;
        timeline.appendChild(el);
      });
    }

    function renderReuse(data) {
      reuseList.innerHTML = '';
      const reuse = data.catalog?.reuse_first || [];
      const fresh = data.catalog?.new_for_quoteops || [];
      [[reuse, 'Reused stack'], [fresh, 'New in QuoteOps']].forEach(([items, title]) => {
        const group = document.createElement('div');
        group.className = 'card';
        group.innerHTML = `<h3>${title}</h3><div class="small">${items.length} items</div>`;
        const list = document.createElement('div');
        list.className = 'list';
        items.forEach((item) => {
          const row = document.createElement('div');
          row.className = 'card';
          row.innerHTML = `<h3>${item.name}</h3><div class="small">${item.description}</div><div class="small" style="margin-top:8px;">${item.source}</div>`;
          list.appendChild(row);
        });
        group.appendChild(list);
        reuseList.appendChild(group);
      });
    }

    function renderTrace(results) {
      traceList.innerHTML = '';
      const cards = [
        { label: 'Task', value: bootstrap.task_id },
        { label: 'Correlation', value: bootstrap.correlation_id },
        { label: 'Reuse count', value: bootstrap.reuse_count },
        { label: 'New count', value: bootstrap.new_count },
      ];
      cards.forEach(({ label, value }) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<div class="badge">${label}</div><div style="font-size:20px;font-weight:700;margin-top:6px;">${value}</div>`;
        traceList.appendChild(card);
      });
      (results || []).forEach((result) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<h3>${result.name}</h3><div class="small">${result.url}</div><div class="small" style="margin-top:8px;">HTTP ${result.status_code} · ${result.ok ? 'reachable' : 'check'}</div>`;
        traceList.appendChild(card);
      });
    }

    function setAnalysis(data, label) {
      analysisJson.textContent = JSON.stringify(data, null, 2);
      analysisHint.textContent = label;
      analysisChips.innerHTML = '';
      const chips = [
        data.analysis_source ? `source: ${data.analysis_source}` : 'source: unknown',
        data.model_used ? `model: ${data.model_used}` : null,
        data.review?.status ? `review: ${data.review.status}` : null,
        data.next_action ? `next: ${data.next_action}` : null,
      ].filter(Boolean);
      chips.forEach((text) => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = text;
        analysisChips.appendChild(chip);
      });
      renderTimeline(data.mission?.status || 'analysis');
    }

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const data = await response.json();
      if (!response.ok) {
        const error = new Error(data.detail?.message || 'Request failed');
        error.payload = data;
        throw error;
      }
      return data;
    }

    function renderRucResult(data) {
      currentVerification = data.verification;
      rucJson.textContent = JSON.stringify(data, null, 2);
      rucConfirmBtn.disabled = false;
      rucConfirmHint.textContent = `Acción propuesta: ${data.customer_draft.recommended_action}. Persistencia: ${data.persistence_target}.`;
      rucChips.innerHTML = '';
      [
        `source: ${data.verification.source}`,
        `status: ${data.verification.upstream_status}`,
        `matches: ${data.comparison.matches.length}`,
        `conflicts: ${data.comparison.conflicts.length}`,
        `checksum: ${data.verification.checksum_valid ? 'valid' : 'provider-confirmed / local warning'}`,
      ].forEach((label) => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = label;
        rucChips.appendChild(chip);
      });
      const verification = data.verification;
      const firstSite = verification.establishments[0];
      const signals = [
        ['Verified legal name', verification.legal_name || 'Not returned'],
        ['Commercial name', verification.commercial_name || 'Not returned'],
        ['Economic activity', verification.activity || 'Not returned'],
        ['Primary establishment', firstSite?.full_address || 'Not returned'],
        ['RalphiIA / Contífico', data.comparison.matches.map((item) => item.source).join(', ') || 'No existing match'],
        ['Human gate', 'Required before create or update'],
      ];
      rucSignals.innerHTML = '';
      signals.forEach(([label, value], index) => {
        const card = document.createElement('div');
        card.className = 'signal';
        const strong = document.createElement('strong');
        strong.className = index === 0 ? 'verified' : '';
        strong.textContent = value;
        const span = document.createElement('span');
        span.textContent = label;
        card.append(strong, span);
        rucSignals.appendChild(card);
      });
    }

    async function lookupRuc(forceRefresh = false) {
      rucConfirmBtn.disabled = true;
      rucJson.textContent = 'Consultando Intuito y reconciliando fuentes...';
      try {
        const data = await fetchJson('/api/ruc/lookup', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ ruc: document.getElementById('rucInput').value, force_refresh: forceRefresh, mode: 'owner' }),
        });
        renderRucResult(data);
      } catch (error) {
        currentVerification = null;
        rucJson.textContent = JSON.stringify(error.payload || { error: error.message }, null, 2);
        rucConfirmHint.textContent = 'Consulta bloqueada; revisa el error y el trace ID.';
      }
    }

    async function confirmRuc() {
      if (!currentVerification) return;
      rucConfirmBtn.disabled = true;
      try {
        const result = await fetchJson('/api/ruc/confirm', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            ruc: currentVerification.ruc,
            approved_by: document.getElementById('approvedBy').value,
            expected_verification_id: currentVerification.verification_id,
          }),
        });
        rucConfirmHint.textContent = `${result.action.toUpperCase()} · party ${result.party_id} · client ${result.client_id} · duplicates ${result.duplicate_count}`;
        await lookupRuc(false);
      } catch (error) {
        rucConfirmHint.textContent = error.payload?.detail?.message || error.message;
        rucConfirmBtn.disabled = false;
      }
    }

    async function refreshReuse() {
      const reuse = await fetchJson('/api/reuse');
      const verify = await fetchJson('/api/reuse/verify');
      renderReuse(reuse);
      renderTrace(verify.results || []);
      document.getElementById('reuseCount').textContent = reuse.reuse_count;
      document.getElementById('newCount').textContent = reuse.new_count;
      document.getElementById('stackStatus').textContent = verify.ok ? 'OK' : 'Check';
    }

    async function analyze(endpoint) {
      const payload = {
        source_channel: document.getElementById('source_channel').value,
        customer_name: document.getElementById('customer_name').value,
        contact: document.getElementById('contact').value,
        original_text: document.getElementById('original_text').value,
        attachments: document.getElementById('attachments').value.split(',').map((item) => item.trim()).filter(Boolean),
      };
      const data = await fetchJson(endpoint, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setAnalysis(data, endpoint.includes('analyze') ? 'GPT-5.6-backed analysis or fallback executed.' : 'Deterministic fallback preview generated.');
    }

    document.getElementById('analyzeBtn').addEventListener('click', () => analyze('/api/intake/analyze'));
    document.getElementById('previewBtn').addEventListener('click', () => analyze('/api/intake/preview'));
    document.getElementById('verifyBtn').addEventListener('click', refreshReuse);
    document.getElementById('rucLookupBtn').addEventListener('click', () => lookupRuc(false));
    document.getElementById('rucRefreshBtn').addEventListener('click', () => lookupRuc(true));
    document.getElementById('rucNewBtn').addEventListener('click', () => {
      document.getElementById('rucInput').value = '0993402875001';
      lookupRuc(true);
    });
    rucConfirmBtn.addEventListener('click', confirmRuc);

    renderTimeline('analysis');
    refreshReuse();
    fetchJson('/api/intake/preview', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        source_channel: 'sandbox',
        customer_name: 'Ana',
        contact: 'ana@example.com',
        original_text: 'Necesito una cotización para automatizar WhatsApp, PDFs y seguimiento de entrega.',
        attachments: ['brief.pdf']
      })
    }).then((data) => setAnalysis(data, 'Bootstrapped with fallback preview.'));
  </script>
</body>
</html>"""
    return (
        template
        .replace("__BOOTSTRAP_JSON__", bootstrap_json)
        .replace("__META_JSON__", meta_json)
        .replace("__PROJECT__", html.escape(bootstrap["project"]))
        .replace("__CORRELATION_ID__", html.escape(bootstrap["correlation_id"]))
        .replace("__TASK_ID__", html.escape(bootstrap["task_id"]))
        .replace("__REUSE_COUNT__", str(bootstrap["reuse_count"]))
        .replace("__NEW_COUNT__", str(bootstrap["new_count"]))
        .replace("__STACK_STATUS__", 'OK' if bootstrap["stack_ok"] else 'Check')
    )
