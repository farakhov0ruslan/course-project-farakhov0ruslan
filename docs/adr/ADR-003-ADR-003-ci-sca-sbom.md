# ADR-003 — CI: SCA (pip-audit) + SBOM (CycloneDX) + SLA/Issue-автоматизация

**Status:** Accepted
**Date:** 2025-10-22
**Component:** CI/CD (`.github/workflows/ci.yml`)
**Related NFR:** **NFR-05** (SCA/SBOM с триажем ≤3д и фиксом High/Critical ≤7д)
**Related Risks:** **R-04** (supply-chain)
**DFD/Flows:** **F9: Dev/CI → App (SCA/SBOM отчёты)**
**STRIDE:** подмена зависимостей / отсутствие аудита уязвимостей на F9 (Tampering/Repudiation)

## Context

В проекте требуется контроль цепочки поставки зависимостей (supply-chain) и формирование **SBOM** для прозрачности компонентов. Это зафиксировано в **NFR-05** и в реестре рисков как **R-04** с приоритетом High. Требуется «shift-left» проверка на каждый push/PR с понятными сроками реакции (triage/fix) и доказуемыми артефактами в CI.

## Decision

1. **Отдельный job `sca`** в GitHub Actions, на который завязан `build` (`needs: sca`). Если `sca` падает — PR не проходит. Это встраивает контроль в поток **F9**.
2. **Инструменты:**

   * `pip-audit` — основной SCA; билд **проваливается**, если найдены High/Critical.
   * `safety` — дополнительный отчёт (не блокирующий).
   * `cyclonedx-bom` → генерация **SBOM (CycloneDX JSON)** через `python -m cyclonedx_py requirements -F json`.
3. **Артефакты CI:** `pip-audit.json`, `pip_audit_summary.md`, `safety.json`, `sbom.cdx.json` — загружаются как artifacts к ранe.
4. **SLA-автоматизация:** при High/Critical создаётся **Issue** с дедлайнами **Triage ≤ 3 дня**, **Fix ≤ 7 дней** (из NFR-05); номер Issue становится ссылкой-evidence в PR.
5. **Нефункциональные сценарии (BDD):** соответствуют @NFR-05 — появление отчёта с High/Critical → Issue ≤3д; fix ≤7д попадает в main.

### Фрагмент реализации (суть job `sca`)

```yaml
jobs:
  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: "pip" }

      - name: Install deps
        run: |
          python -m pip install -U pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
          pip install pip-audit safety cyclonedx-bom

      - name: Freeze
        run: pip freeze | sort > requirements.lock.txt

      - name: pip-audit (collect)
        id: pip_audit
        continue-on-error: true
        run: |
          pip-audit -r requirements.lock.txt -f json -o pip-audit.json || true
          python - <<'PY'
            import json, os
            sev={"LOW":1,"MEDIUM":2,"HIGH":3,"CRITICAL":4}; hi=[]
            for pkg in json.load(open("pip-audit.json","r",encoding="utf-8")):
              for v in pkg.get("vulns", []):
                if sev.get((v.get("severity") or "").upper(),0)>=3: hi.append((pkg["name"], v["severity"], v["id"]))
            if hi:
              open("pip_audit_summary.md","w",encoding="utf-8").write("### pip-audit High/Critical findings\n\n"+"\n".join(f"- {n}: {s} — {vid}" for n,s,vid in hi))
              open(os.environ["GITHUB_ENV"],"a").write("PIP_AUDIT_HIGH_OR_CRIT=1\n")
            else:
              open(os.environ["GITHUB_ENV"],"a").write("PIP_AUDIT_HIGH_OR_CRIT=0\n")
            PY

      - name: safety (non-blocking)
        run: safety check --full-report --json > safety.json || true

      - name: SBOM (CycloneDX JSON)
        run: |
          python -m cyclonedx_py requirements -i requirements.lock.txt -o sbom.cdx.json -F json

      - name: Upload SCA artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sca-reports
          path: |
            requirements.lock.txt
            pip-audit.json
            pip_audit_summary.md
            safety.json
            sbom.cdx.json

      - name: Create Issue on High/Critical (triage≤3d, fix≤7d)
        if: env.PIP_AUDIT_HIGH_OR_CRIT == '1'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const summary = fs.existsSync('pip_audit_summary.md') ? fs.readFileSync('pip_audit_summary.md','utf8') : '';
            const triageBy = new Date(Date.now() + 3*24*3600*1000).toISOString().slice(0,10);
            const fixBy    = new Date(Date.now() + 7*24*3600*1000).toISOString().slice(0,10);
            await github.rest.issues.create({
              owner: context.repo.owner, repo: context.repo.repo,
              title: `SCA: High/Critical vulnerabilities (triage ≤ ${triageBy}, fix ≤ ${fixBy})`,
              labels: ['security','sca','NFR-05'],
              body: `**NFR-05 / R-04 (supply-chain)**\n\n${summary}\n\n- Triage: ${triageBy}\n- Fix: ${fixBy}\n\nAttach 'sca-reports'.`
            });

      - name: Fail if High/Critical found
        if: env.PIP_AUDIT_HIGH_OR_CRIT == '1'
        run: exit 2

  build:
    needs: sca
    # ... остальной пайплайн (lint/test/pre-commit)
```

## Consequences

**Плюсы**

* Принудительная «воронка безопасности» в PR: без чистого SCA билд не проходит — снижаем **R-04**.
* Автоматическая трассировка и **evidence**: отчёты артефактами, Issues с SLA — закрывают требования **NFR-05** и сценарии из **NFR_BDD**.
* Непрерывная видимость зависимостей через **SBOM (CycloneDX)**.

**Минусы/риски**

* Возможны «ложные блокировки» при конфликтах CVE и несовместимых апгрейдах; требуется triage.
* Увеличение времени CI (≈1–2 минуты).

## Security Impact

* STRIDE/Tampering на F9: снижение риска подмены зависимостей за счёт регулярного анализа и контроля порогов.
* Repudiation: наличие отчётов и Issues обеспечивает аудит и прослеживаемость решений (кто/когда отреагировал).

## Implementation / Links

* Файл: `.github/workflows/ci.yml` — добавлен job `sca` и `needs: sca` в `build`.
* Артефакты CI: `sca-reports` (pip-audit/safety/SBOM).
* Привязка к документации: **DFD F9**, **STRIDE (F9)**, **RISKS R-04**, **NFR-05**, **NFR_BDD @NFR-05**.

## Testing / Evidence

* На PR с намеренно уязвимой зависимостью:
  * `sca` генерирует отчёты (артефакты присутствуют),
  * создаётся **Issue** с дедлайнами triage/fix,
  * job `sca` → **fail**, `build` не запускается.
* На PR с фиксами:

  * `sca` зелёный,
  * Issue закрывается ссылкой на PR, SLA уложены (≤3/≤7 дней).
    Это соответствует критериям **NFR_BDD @NFR-05**.

## Rollout / Ops

* Включено для всех веток PR/Push.
* При «шумных» уязвимостях допускается временная метка `known-issue` в Issue и пин приоритета, но **блокирующее правило** для High/Critical сохраняется (исключения — через отдельный ADR/временный флаг).

## Alternatives

* **Dependabot-только:** уведомления без блокировки CI — не гарантия соблюдения SLA/порогов (отвергнуто).
* **Только pip-audit, без SBOM:** хуже видимость состава (отвергнуто).
* **Syft (Anchore) для SBOM:** допустимая альтернатива; можно заменить шаг генерации SBOM на `anchore/sbom-action@v0` (не меняет смысл ADR).
* **Отдельный nightly-скан:** медленнее обратная связь, не «shift-left» (отвергнуто).

## Traceability

* **NFR:** NFR-05.
* **DFD/Flows:** F9.
* **STRIDE:** строки по F9.
* **RISKS:** R-04.

## Acceptance Criteria

* ✅ На каждый push/PR выполняется job `sca`; при High/Critical — создаётся Issue (triage ≤3д) и job падает.
* ✅ `build` имеет `needs: sca` и не стартует при провале `sca`.
* ✅ В артефактах ранa присутствуют `pip-audit.json`, `pip_audit_summary.md`, `safety.json`, `sbom.cdx.json`.
* ✅ В репозитории есть закрытые Issues/PR, подтверждающие фиксы ≤7д после triage (evidence для **NFR-05**).
