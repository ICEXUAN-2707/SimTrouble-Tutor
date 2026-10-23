import type { SessionView } from './learning-types';
type Step = 'observe' | 'evidence' | 'hypothesis' | 'diagnosis';
const steps: Step[] = ['observe', 'evidence', 'hypothesis', 'diagnosis'];
let active: Step = 'observe';
const el = (id: string) => document.getElementById(id)!;
export function showStep(step: Step): void {
  active = step;
  document.querySelectorAll<HTMLElement>('[data-panel]').forEach(p => p.hidden = p.dataset.panel !== step);
  document.querySelectorAll<HTMLButtonElement>('[data-step]').forEach(b => {
    b.setAttribute('aria-current', b.dataset.step === step ? 'step' : 'false');
  });
  const index = steps.indexOf(step);
  el('step-back').hidden = index === 0;
  el('step-back').textContent = ['','返回观察','返回取证','返回假设'][index];
  el('step-next').hidden = index === 3;
  el('step-next').textContent = ['开始取证 →','形成假设 →','进入诊断 →',''][index];
  el('hypothesis-submit').hidden = step !== 'hypothesis';
  el('diagnosis-submit').hidden = step !== 'diagnosis';
  // Submission belongs to the form; the next button remains navigation only.
  el('learning-notice').hidden = step === 'observe' || !el('learning-notice').textContent;
}
export function syncWorkspace(view: SessionView | null, busy = false): void {
  el('training-status').textContent = !view ? '正在连接' : ['SUBMITTED','REVIEWED'].includes(view.public_stage) ? '诊断已提交' : '训练进行中';
  el('busy-notice').hidden = !busy;
  document.querySelectorAll<HTMLButtonElement>('[data-step]').forEach(b => {
    const key = b.dataset.step;
    const locked = key === 'diagnosis' && !view?.allowed_actions.includes('submit_diagnosis') && !['SUBMITTED','REVIEWED'].includes(view?.public_stage ?? '');
    b.dataset.locked = String(locked);
    const complete = key === "evidence" ? !!view?.released_evidence.length : key === "hypothesis" ? !!view?.hypotheses.length : key === "diagnosis" ? ["SUBMITTED","REVIEWED"].includes(view?.public_stage ?? "") : false;
    b.dataset.complete = String(complete);
    b.title = locked ? '完成假设修正后可提交诊断' : '查看此步骤';
  });
}
export function showReport(): void {
  const dialog = el('assistant-dialog') as HTMLDialogElement;
  if (dialog.open) dialog.close();
  document.querySelector<HTMLElement>('.workspace')!.hidden = true;
  el('report-panel').hidden = false;
  document.body.classList.add('report-open');
  el('report-back').focus();
}
export function initialiseWorkspace(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-step]').forEach(b => b.addEventListener('click', () => showStep(b.dataset.step as Step)));
  el('step-back').addEventListener('click', () => showStep(steps[Math.max(0, steps.indexOf(active)-1)]));
  el('step-next').addEventListener('click', () => showStep(steps[Math.min(3, steps.indexOf(active)+1)]));
  const dialog = el('assistant-dialog') as HTMLDialogElement;
  el('assistant-open').addEventListener('click', () => dialog.showModal());
  el('assistant-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => el('assistant-open').focus());
  dialog.addEventListener('click', e => { if (e.target === dialog && e.clientX < dialog.getBoundingClientRect().left) dialog.close(); });
  el('report-back').addEventListener('click', () => {
    el('report-panel').hidden = true;
    document.querySelector<HTMLElement>('.workspace')!.hidden = false;
    document.body.classList.remove('report-open');
    showStep('diagnosis');
    document.querySelector<HTMLButtonElement>('[data-step="diagnosis"]')!.focus();
  });
  showStep('observe');
}
