// Paste in the browser console (F12) on https://uabthehack.cat/participants/xaman, signed in, tab "Envia" visible.
// Needs servidor.py running. Loops ROUNDS rounds: asks the server for fresh variants, submits each, logs the score.
(async () => {
  const ROUNDS = 6, SRV = 'http://127.0.0.1:8765/', Q = 'torns';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const main = () => document.querySelector('main').innerText;
  const setSel = (el, v) => { Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('change', { bubbles: true })); };
  const log = o => fetch(SRV + 'log', { method: 'POST', body: JSON.stringify(o) });
  const submit = async dir => {
    setSel(document.querySelectorAll('select')[0], Q); await sleep(1000);
    const ins = document.querySelectorAll('input[type=file]');
    for (const [i, n, nm] of [[0, 'p.csv', 'proposta.csv'], [1, 'r.csv', 'relaxacions.csv']]) {
      const t = await (await fetch(SRV + dir + '/' + n)).text();
      const dt = new DataTransfer(); dt.items.add(new File([t], nm, { type: 'text/csv' }));
      ins[i].files = dt.files; ins[i].dispatchEvent(new Event('change', { bubbles: true }));
    }
    const before = +((main().match(/enviament #(\d+)/) || [0, 0])[1]);
    document.querySelector('button[type=submit]').click();
    for (let k = 0; k < 120; k++) {
      await sleep(1000);
      const t = main();
      if (t.includes('màxim de')) return { limit: true };
      const m = t.match(/enviament #(\d+)([\s\S]{0,1500})/);
      if (m && +m[1] > before) { const s = m[2].match(/(\d+)\/100/); if (s) return { id: +m[1], score: +s[1], text: m[2].slice(0, 700) }; }
    }
    return { timeout: true };
  };
  for (let r = 1; r <= ROUNDS; r++) {
    console.log(`Round ${r}: generating variants (takes a few minutes)...`);
    const { variants } = await (await fetch(SRV + 'next')).json();
    for (const v of variants) {
      let res = await submit(v.dir);
      while (res.limit) { console.log('Hourly limit reached, waiting 5 min'); await sleep(300000); location.reload(); await sleep(5000); res = await submit(v.dir); }
      await log({ dir: v.dir, mode: v.mode, obj: v.obj, ...res });
      console.log(`${v.dir} [${v.mode}] score=${res.score} id=${res.id}`, v.obj);
    }
  }
  console.log('DONE. Results in nivell2/p52_torns/web-lot/resultats.jsonl');
})();
