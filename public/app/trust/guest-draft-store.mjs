// The software viewer and the WebGL studio share the same v2 database and
// verified payload format. Account storage is never opened by this adapter.
import { ACS_TRUST } from './core.js';

const records = ACS_TRUST.persistence;
function request(operation) {
  return new Promise((resolve, reject) => {
    operation.onsuccess = () => resolve(operation.result);
    operation.onerror = () => reject(operation.error);
  });
}

export async function openGuestDraft(scope) {
  if (!scope.startsWith('acs_guest_draft_')) throw new Error('INVALID_GUEST_SCOPE');
  const opening = indexedDB.open(scope, 2);
  opening.onupgradeneeded = () => {
    const db = opening.result;
    for (const name of ['records','design_versions']) {
      if (!db.objectStoreNames.contains(name)) db.createObjectStore(name, {keyPath:'record_id'});
    }
    if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta');
  };
  const db = await request(opening);
  db.onversionchange = () => db.close();
  const recovered = records.chooseRecovery(await request(db.transaction('records').objectStore('records').getAll()));
  if (!recovered.chosen && recovered.code !== 'NO_RECORDS') {
    db.close();
    throw new Error('UNREADABLE_DRAFT');
  }
  const initial = recovered.chosen && records.decode(recovered.chosen);
  if (initial && !initial.ok) { db.close(); throw new Error('UNREADABLE_DRAFT'); }
  let project = initial?.project || {contract:'acs-local-project-payload/1', project_id:'default', current_revision:null, notes:[], generation_in_flight:false};
  let previous = recovered.chosen_id;
  async function save(model) {
    const tx = db.transaction(['records','meta'],'readwrite');
    const done = new Promise((resolve,reject) => {
      tx.oncomplete = resolve;
      tx.onabort = () => reject(tx.error || new Error('DRAFT_WRITE_FAILED'));
      tx.onerror = () => reject(tx.error);
    });
    const store = tx.objectStore('records');
    try {
      const rows = await request(store.getAll());
      const current = records.chooseRecovery(rows);
      if (current.chosen_id !== previous) throw new Error('DRAFT_CHANGED');
      const nextProject = {...project, model, request_text:model.meta?.acs_apartment?.brief || project.request_text || ''};
      const plan = records.planWrite({pointer:previous, records:current.accepted.map(row=>row.record_id)}, nextProject,
        {now:Math.max(Date.now(),(current.chosen?.saved_at_ms || 0)+1),origin:'AUTOSAVE'});
      if (!plan.ok) throw new Error(plan.code);
      const record = plan.plan.new_record;
      await request(store.add(record));
      if (!records.validateRecord(await request(store.get(record.record_id))).usable) throw new Error('DRAFT_VALIDATION_FAILED');
      tx.objectStore('meta').put(record.record_id,'pointer');
      for (const id of plan.plan.prune) store.delete(id);
      await done;
      previous=record.record_id;
      project=nextProject;
    } catch(error) {
      try { tx.abort(); } catch {}
      await done.catch(()=>{});
      throw error;
    }
  }
  return {model:project.model || null, save};
}
