# RalfIA Remote Developer Control Plane

## Objetivo

Permitir que Rafael gestione operaciones y encargue desarrollo desde WhatsApp o un navegador móvil. WhatsApp no es una shell: convierte solicitudes en tareas MCP, aplica scopes y exige confirmación humana antes de que Codex trabaje en un repositorio aislado.

## Estado verificado (2026-07-18)

- PASS: audio sintético OGG → FFmpeg → Whisper local (`~2 s`).
- PASS: imagen sintética → Tesseract + `llava:7b` local (`~34 s`).
- PASS: reintento multimedia idempotente y cero API pagada.
- PASS: `message_id` → `media_id` → `correlation_id` → tarea/runner.
- PASS: servicio demo mínimo en `127.0.0.1:8766`; `/healthz` y panel 200, `/docs` 404, cabeceras defensivas y rate limit 6 sesiones/10 min.
- PASS: 28 pruebas del bridge y 11 pruebas del demo.
- PARTIAL: MCP crea la tarea y el checkpoint funciona, pero Codex no puede iniciar Bubblewrap hasta cargar el perfil AppArmor específico. El fallo se registra como FAIL; nunca como éxito falso.
- PENDIENTE: activar `demo.pcdoctor.ai` solamente después del E2E con pruebas y commit.

## Límites de seguridad

- Escenarios públicos fijos; el texto u OCR del visitante no modifica herramientas ni prompt ejecutable.
- Identidad efímera, token hasheado, expiración de 30 minutos y máximo 3 acciones por sesión.
- Aprobación ligada a la misma sesión.
- Sin sudo, despliegue, DNS, producción, shell arbitraria ni datos privados.
- Codex usa `workspace-write`, entorno mínimo y `shell_environment_policy.inherit=none`.
- Las pruebas no heredan `MCP_API_KEY` ni otras variables del servicio.
- Cambio verificable + pruebas PASS son obligatorios antes de crear commit.
- El timeout termina el grupo completo de procesos.

## AppArmor: corrección mínima

Ubuntu restringe user namespaces aun cuando `kernel.unprivileged_userns_clone=1`. No se desactiva ese control global. Se autoriza `userns` únicamente al binario de Codex, siguiendo el patrón de los perfiles AppArmor de VS Code.

En `.4`:

```bash
sudo install -o root -g root -m 0644 /home/rlopez/apparmor-ralfia-codex-14 /etc/apparmor.d/ralfia-codex-14
sudo apparmor_parser -r /etc/apparmor.d/ralfia-codex-14
```

En `.5`:

```bash
sudo install -o root -g root -m 0644 /home/rlopez/apparmor-ralfia-codex-15 /etc/apparmor.d/ralfia-codex-15
sudo apparmor_parser -r /etc/apparmor.d/ralfia-codex-15
```

Después se repite `scripts/run_remote_dev_e2e.py`. Solo un resultado con tarea MCP, cambio Git, tests PASS y commit habilita el túnel público.

## Servicio aislado

- Release: `/home/rlopez/releases/ralfia-remote-dev-demo/5a11afd`
- Unidad: `~/.config/systemd/user/ralfia-remote-dev-demo.service`
- Bind: `127.0.0.1:8766`
- Workspace sintético: `/home/rlopez/worktrees/ralfia-public-demo`
- Dominio reservado: `demo.pcdoctor.ai` mediante Cloudflare Tunnel; no se abre ningún puerto público.

## Rollback

1. Detener el demo: `systemctl --user disable --now ralfia-remote-dev-demo.service`.
2. Restaurar `/home/rlopez/.cloudflared/opportunityops.yml` desde su backup y reiniciar `opportunityops-cloudflared.service` si el hostname ya fue activado.
3. Retirar los perfiles, si se requiere: `sudo apparmor_parser -R /etc/apparmor.d/ralfia-codex-14` (y `-15` en `.5`), luego eliminar únicamente esos dos archivos.
4. El bridge `.4` tiene backup en `/home/rlopez/backups/raphiia-openai-openai-demo-20260718T2258Z`; restaurar solo los archivos listados y reiniciar `ralfia-mcp`, `ralfia-app` y `whatsapp-automation`.

Nunca borrar worktrees o releases de forma recursiva sin validar primero la ruta absoluta.
